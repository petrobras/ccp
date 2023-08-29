"""Module for performance evaluation based on historical data."""
import multiprocessing
from .data_io import filter_data
from .state import State
from .point import Point
from .impeller import Impeller
from . import Q_


class Evaluation:
    """Class for performance evaluation based on historical data."""

    def __init__(
        self,
        data,
        operation_fluid=None,
        window=3,
        data_units=None,
        temperature_fluctuation=0.5,
        pressure_fluctuation=2,
        speed_fluctuation=0.5,
        impellers=None,
    ):
        """Initialize the evaluation class.

        Parameters
        ----------
        data : pandas.DataFrame
            Historical data of the following parameters below. Notice that if the units
            are not provided in the data_units dictionary, the units will be assumed as
            SI units:
            - flow: should be 'flow_v' (m³/s) or 'flow_m' (kg/s) in the DataFrame;
            - Suction pressure: should be 'ps' (Pa) in the DataFrame;
            - Discharge pressure: should be 'pd' (Pa) in the DataFrame;
            - Suction temperature: should be 'Ts' (degK) in the DataFrame;
            - Discharge temperature: should be 'Td' (degK) in the DataFrame;
            - Speed: should be 'speed' (rad/s) in the DataFrame.
        window : int, optional
            Window size for rolling calculation, meaning how many rolls will be used
            to calculate the fluctuation.
            The default is 3.
        data_units : dict
            Dictionary with data units for each column.
        temperature_fluctuation : float, optional
            Maximum fluctuation for temperature data.
            The default is 0.5.
        pressure_fluctuation : float, optional
            Maximum fluctuation for pressure data.
            The default is 2.
        speed_fluctuation : float, optional
            Maximum fluctuation for speed data.
            The default is 0.5.
        impellers : list
            List of impellers with design curves.

        Returns
        -------
        None.
        """
        self.data = data
        self.operation_fluid = operation_fluid
        self.window = window
        self.data_type = {
            "ps": "pressure",
            "Ts": "temperature",
            "pd": "pressure",
            "Td": "temperature",
            "speed": "speed",
        }
        self.data_units = data_units
        self.temperature_fluctuation = temperature_fluctuation
        self.pressure_fluctuation = pressure_fluctuation
        self.speed_fluctuation = speed_fluctuation
        self.impellers = impellers

        df = self.data.copy()
        df = filter_data(
            df,
            data_type=self.data_type,
            window=window,
            temperature_fluctuation=temperature_fluctuation,
            pressure_fluctuation=pressure_fluctuation,
            speed_fluctuation=speed_fluctuation,
        )

        # create density column
        df["v_s"] = 0
        for i, row in df.iterrows():
            # create state
            state = State(
                p=Q_(row.ps, data_units["ps"]),
                T=Q_(row.Ts, data_units["Ts"]),
                fluid=operation_fluid,
            )
            df.loc[i, "v_s"] = state.v().m

        # check if flow_v or flow_m is in the DataFrame
        if "flow_v" in df.columns:
            # create flow_m column
            df["flow_m"] = (
                Q_(df["flow_v"].array, self.data_units["flow_v"])
                * Q_(df["v_s"].array, "m³/kg")
            ).m
        elif "flow_m" in df.columns:
            # create flow_v column
            df["flow_v"] = (
                Q_(df["flow_m"].array, self.data_units["flow_m"])
                / Q_(df["v_s"].array, "m³/kg")
            ).m
        else:
            raise ValueError("Flow rate not found in the DataFrame.")

        # convert impeller considering mean data
        # for now use only one impeller
        # TODO create clusters based on mach and vs/vd and select best impeller for each cluster
        # TODO convert impeller for each cluster
        imp = self.impellers[0]
        mean = df.mean()
        suc_new = State(
            p=Q_(mean.ps, data_units["ps"]),
            T=Q_(mean.Ts, data_units["Ts"]),
            fluid=operation_fluid,
        )
        imp_new = Impeller.convert_from(imp, suc=suc_new, speed="same")
        self.impellers_new = [imp_new]

        # create args list for parallel processing
        # loop
        points = []
        expected_points = []

        args_list = []
        for i, row in df.iterrows():
            # calculate point
            arg_dict = {
                "flow_m": row.flow_m,
                "speed": Q_(row.speed, self.data_units["speed"]),
                "suc": State(
                    p=Q_(row.ps, self.data_units["ps"]),
                    T=Q_(row.Ts, self.data_units["Ts"]),
                    fluid=operation_fluid,
                ),
                "disch": State(
                    p=Q_(row.pd, self.data_units["pd"]),
                    T=Q_(row.Td, self.data_units["Td"]),
                    fluid=operation_fluid,
                ),
                "imp_new": imp_new,
            }

            args_list.append(arg_dict)

        with multiprocessing.Pool() as pool:
            points += pool.map(create_points_parallel, args_list)
            expected_points += pool.map(get_interpolated_point, args_list)

        # loop
        df["eff"] = 0
        df["head"] = 0
        df["power"] = 0
        df["p_disch"] = 0
        df["expected_eff"] = 0
        df["expected_head"] = 0
        df["expected_power"] = 0
        df["expected_p_disch"] = 0
        df["delta_eff"] = 0
        df["delta_head"] = 0
        df["delta_power"] = 0
        df["delta_p_disch"] = 0

        for i, point_op, point_expected in zip(df.index, points, expected_points):
            df.loc[i, "eff"] = point_op.eff.m
            df.loc[i, "head"] = point_op.head.m
            df.loc[i, "power"] = point_op.power.m
            df.loc[i, "p_disch"] = point_op.disch.p("bar").m
            df.loc[i, "expected_eff"] = point_expected.eff.m
            df.loc[i, "expected_head"] = point_expected.head.m
            df.loc[i, "expected_power"] = point_expected.power.m
            df.loc[i, "expected_p_disch"] = point_expected.disch.p("bar").m
            df.loc[i, "delta_eff"] = (point_op.eff - point_expected.eff).m
            df.loc[i, "delta_head"] = (point_op.head - point_expected.head).m
            df.loc[i, "delta_power"] = (point_op.power - point_expected.power).m
            df.loc[i, "delta_p_disch"] = (
                point_op.disch.p("bar") - point_expected.disch.p("bar")
            ).m

        # plot eff in plot with colormap showing the time

        # define the time delta and use that as a scale from 0 to 100
        total_time = df.index[-1] - df.index[0]

        # create column for timescale
        df["timescale"] = 0

        for i, row in df.iterrows():
            # calculate seconds from i sample to start. Remember that i here is the index which is datetime
            sample_time = i - df.index[0]
            df.loc[i, "timescale"] = sample_time.seconds / total_time.seconds

        self.df = df


def create_points_parallel(x):
    del x["imp_new"]
    return Point(**x)


def get_interpolated_point(x):
    imp_new = x["imp_new"]
    expected_point = imp_new.point(flow_m=x["flow_m"], speed=x["speed"])
    return expected_point