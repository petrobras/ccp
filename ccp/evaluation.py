"""Module for performance evaluation based on historical data."""

import multiprocessing
import zipfile
import toml
import pandas as pd
import io
import pickle
from .data_io import filter_data
from .state import State
from .point import Point
from .fo import FlowOrifice
from .impeller import Impeller
from . import Q_
from sklearn.cluster import KMeans
from tqdm.auto import tqdm


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
        D=None,
        d=None,
        tappings=None,
        verbose=False,
        n_clusters=5,
        calculate_points=True,
        **kwargs,
    ):
        """Initialize the evaluation class.

        Parameters
        ----------
        data : pandas.DataFrame
            Historical data of the following parameters below. Notice that if the units
            are not provided in the data_units dictionary, the units will be assumed as
            SI units:
            - Flow: should be 'flow_v' (m³/s) or 'flow_m' (kg/s) in the DataFrame;
            - Delta p: should be 'delta_p' (Pa) in the DataFrame;
            - Suction pressure: should be 'ps' (Pa) in the DataFrame;
            - Discharge pressure: should be 'pd' (Pa) in the DataFrame;
            - Suction temperature: should be 'Ts' (degK) in the DataFrame;
            - Discharge temperature: should be 'Td' (degK) in the DataFrame;
            - Speed: should be 'speed' (rad/s) in the DataFrame.
            Optionally, the gas composition for each row can be provided by adding
            columns whose names start with ``fluid_`` (e.g. ``fluid_methane``). Each
            of these columns must contain the mole fraction of the constituent in that
            row. When these columns are present ``operation_fluid`` can be omitted.
        operation_fluid : dict, optional
            Dictionary defining the working fluid composition for all rows. If
            not provided, the composition will be read from the ``fluid_*``
            columns of ``data``.
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
        D : float, pint.Quantity
            Pipe diameter (m).
        d : float, pint.Quantity
            Orifice diameter (m).
        tappings : str, optional
            Tappings of the orifice.
            Options are "flange", "corner" or "D D/2".
            Default is "flange".
        n_clusters : int, optional
            Number of clusters to be used in the K-means algorithm.
            The default is 5.
        calculate_points : bool, optional
            If True, calculates the performance points for the given data.
            The default is True.
        verbose : bool, optional
            If True, shows progress bar.

        Returns
        -------
        None.
        """
        self.data = data
        self.operation_fluid = operation_fluid
        self.fluid_columns = [c for c in self.data.columns if c.startswith("fluid_")]
        self.window = window
        self.data_type = {
            "ps": "pressure",
            "Ts": "temperature",
            "pd": "pressure",
            "Td": "temperature",
            "speed": "speed",
            "delta_p": "delta_p",
        }
        self.data_units = data_units
        self.temperature_fluctuation = temperature_fluctuation
        self.pressure_fluctuation = pressure_fluctuation
        self.speed_fluctuation = speed_fluctuation
        self.impellers = impellers
        self.D = D
        self.d = d
        self.tappings = tappings
        self.n_clusters = n_clusters

        # check if we are loading from a zip file where the impellers are available
        if kwargs.get("impellers_new") is None:
            self._run()
            if calculate_points:
                self.df = self.calculate_points()
        else:
            self.impellers_new = kwargs.get("impellers_new")
            self.df = kwargs.get("df")

    def _get_fluid_composition(self, row_or_series):
        """Extract and convert fluid composition from a row or series.

        Parameters
        ----------
        row_or_series : pandas.Series
            Row or series containing fluid_* columns.

        Returns
        -------
        dict
            Dictionary with component names and mole fractions.
        """
        fluid = {}
        for col in self.fluid_columns:
            comp_name = col[len("fluid_") :]
            value = row_or_series[col]

            # Check if unit is specified as ppm
            if self.data_units and col in self.data_units:
                if self.data_units[col] == "ppm":
                    # Convert ppm to mole fraction
                    value = value / 1e6

            fluid[comp_name] = value

        return fluid

    def _run(self):
        df = self.data.copy()
        df = filter_data(
            df,
            data_type=self.data_type,
            window=self.window,
            temperature_fluctuation=self.temperature_fluctuation,
            pressure_fluctuation=self.pressure_fluctuation,
            speed_fluctuation=self.speed_fluctuation,
        )

        # Check if dataframe is empty after filtering
        if df.empty:
            raise ValueError(
                "DataFrame is empty after filtering. "
                "All rows were removed due to fluctuation criteria. "
                "Please check your data or adjust the filtering parameters "
                "(temperature_fluctuation, pressure_fluctuation, speed_fluctuation)."
            )

        df = self.calculate_flow(df)

        # create clusters based on speed_sound, ps and Ts
        data = df[["speed_sound", "ps", "Ts"]]
        # normalize
        data_mean = data.mean()
        data_std = data.std()
        # Replace 0 std with 1 to avoid division by zero (constant features will become 0)
        data_std = data_std.replace(0, 1)
        data_norm = (data - data_mean) / data_std
        self.data_mean = data_mean
        self.data_std = data_std

        # Using sklearn
        kmeans = KMeans(n_clusters=self.n_clusters, n_init="auto")
        kmeans.fit(data_norm)
        self.kmeans = kmeans

        # Format results as a DataFrame
        df["cluster"] = kmeans.labels_
        for i in range(kmeans.n_clusters):
            df.loc[df["cluster"] == i, "speed_sound_center"] = (
                kmeans.cluster_centers_[i][0] * data_std["speed_sound"]
            ) + data_mean["speed_sound"]
            df.loc[df["cluster"] == i, "ps_center"] = (
                kmeans.cluster_centers_[i][1] * data_std["ps"]
            ) + data_mean["ps"]
            df.loc[df["cluster"] == i, "Ts_center"] = (
                kmeans.cluster_centers_[i][0] * data_std["Ts"]
            ) + data_mean["Ts"]

        self.impellers_new = []

        print("Converting curves")
        for i in tqdm(range(kmeans.n_clusters)):
            cluster_series = df[df["cluster"] == 0].iloc[0]
            if self.operation_fluid is not None:
                fluid = self.operation_fluid
            else:
                fluid = self._get_fluid_composition(cluster_series)
            suc_new = State(
                p=Q_(cluster_series.ps_center, self.data_units["ps"]),
                T=Q_(cluster_series.Ts_center, self.data_units["Ts"]),
                fluid=fluid,
            )
            imp_new = Impeller.convert_from(self.impellers, suc=suc_new, speed="same")
            self.impellers_new.append(imp_new)

        self.df = df

    def calculate_flow(self, data=None):
        df = data
        calculate_flow = False
        if not ("flow_v" in df.columns or "flow_m" in df.columns):
            calculate_flow = True

        # create density column
        df["v_s"] = 0.0
        df["speed_sound"] = 0.0

        for i, row in df.iterrows():
            if self.operation_fluid is not None:
                fluid = self.operation_fluid
            else:
                fluid = self._get_fluid_composition(row)

            if calculate_flow:
                if "p_downstream" in df.columns:
                    state_upstream = False
                    state = State(
                        p=Q_(row.p_downstream, self.data_units["p_downstream"]),
                        T=Q_(row.Ts, self.data_units["Ts"]),
                        fluid=fluid,
                    )
                elif "p_upstream" in df.columns:
                    state_upstream = True
                    state = State(
                        p=Q_(row.p_upstream, self.data_units["p_upstream"]),
                        T=Q_(row.Ts, self.data_units["Ts"]),
                        fluid=fluid,
                    )
                else:
                    raise ValueError(
                        "Pressure upstream/downstream fo not found in the DataFrame."
                    )

                delta_p = Q_(row.delta_p, self.data_units["delta_p"])
                fo = FlowOrifice(
                    state,
                    delta_p,
                    self.D,
                    self.d,
                    tappings=self.tappings,
                    state_upstream=state_upstream,
                )
                df.loc[i, "flow_m"] = fo.qm.m
                df.loc[i, "flow_v"] = (fo.qm * state.v()).m
            else:
                state = State(
                    p=Q_(row.ps, self.data_units["ps"]),
                    T=Q_(row.Ts, self.data_units["Ts"]),
                    fluid=fluid,
                )

            df.loc[i, "v_s"] = state.v().m
            df.loc[i, "speed_sound"] = state.speed_sound().m

        # check if flow_v or flow_m is in the DataFrame
        if (not calculate_flow) and (
            not ("flow_v" in df.columns or "flow_m" in df.columns)
        ):
            if "flow_v" in df.columns:
                # create flow_m column
                df["flow_m"] = (
                    Q_(df["flow_v"].array, self.data_units["flow_v"])
                    / Q_(df["v_s"].array, "m³/kg")
                ).m
            elif "flow_m" in df.columns:
                # create flow_v column
                df["flow_v"] = (
                    Q_(df["flow_m"].array, self.data_units["flow_m"])
                    * Q_(df["v_s"].array, "m³/kg")
                ).m
            else:
                raise ValueError("Flow rate not found in the DataFrame.")

        return df

    def calculate_points(self, data=None, drop_invalid_values=True):
        """Calculate the performance points for the given data.

        Parameters
        ----------
        data : pandas.DataFrame, optional
            Data to be used for the calculation. If not provided, the data
            used in the initialization will be used.
            The default is None.
        drop_invalid_values : bool, optional
            Drop invalid values from the dataframe.
            If false, a column 'valid' will be added to the dataframe with True for valid.
            The default is True.

        Returns
        -------
        df : pandas.DataFrame
            DataFrame with the calculated points.
        """
        if data is None:
            df = self.df
        else:
            df = data.copy()
            df = filter_data(
                df,
                data_type=self.data_type,
                window=self.window,
                temperature_fluctuation=self.temperature_fluctuation,
                pressure_fluctuation=self.pressure_fluctuation,
                speed_fluctuation=self.speed_fluctuation,
                drop_invalid_values=drop_invalid_values,
            )

            # Check if dataframe is empty after filtering
            if df.empty:
                raise ValueError(
                    "DataFrame is empty after filtering. "
                    "All rows were removed due to fluctuation criteria. "
                    "Please check your data or adjust the filtering parameters "
                    "(temperature_fluctuation, pressure_fluctuation, speed_fluctuation)."
                )

        df = self.calculate_flow(df)

        # assign to a cluster
        df["cluster"] = 0

        for i, row in df.iterrows():
            new_data = pd.DataFrame(
                [row[["speed_sound", "ps", "Ts"]].values],
                columns=["speed_sound", "ps", "Ts"],
            )
            new_data = (new_data - self.data_mean.values) / self.data_std.values
            df.loc[i, "cluster"] = self.kmeans.predict(new_data)[0]

        points = []
        expected_points = []

        args_list = []
        for i, row in df.iterrows():
            if self.operation_fluid is not None:
                fluid = self.operation_fluid
            else:
                fluid = self._get_fluid_composition(row)

            arg_dict = {
                "flow_v": row.flow_v,
                "speed": Q_(row.speed, self.data_units["speed"]),
                "suc": State(
                    p=Q_(row.ps, self.data_units["ps"]),
                    T=Q_(row.Ts, self.data_units["Ts"]),
                    fluid=fluid,
                ),
                "disch": State(
                    p=Q_(row.pd, self.data_units["pd"]),
                    T=Q_(row.Td, self.data_units["Td"]),
                    fluid=fluid,
                ),
                "imp_new": self.impellers_new[int(row.cluster)],
                "valid": row.valid,
            }

            args_list.append(arg_dict)

        with multiprocessing.Pool() as pool:
            print("Calculating points...")
            points += tqdm(pool.imap(create_points_parallel, args_list))
            print("Calculating expected points...")
            expected_points += tqdm(pool.imap(get_interpolated_point, args_list))

        # start column with -1.0, if this value remains, it means that the point was not calculated due to invalid data
        df["eff"] = -1.0
        df["head"] = -1.0
        df["power"] = -1.0
        df["p_disch"] = -1.0
        df["expected_eff"] = -1.0
        df["expected_head"] = -1.0
        df["expected_power"] = -1.0
        df["expected_p_disch"] = -1.0
        df["delta_eff"] = -1.0
        df["delta_head"] = -1.0
        df["delta_power"] = -1.0
        df["delta_p_disch"] = -1.0

        for i, point_op, point_expected in zip(df.index, points, expected_points):
            # if point_op is None, it means that the point was not calculated due to invalid data
            if point_op is not None:
                df.loc[i, "eff"] = point_op.eff.m
                df.loc[i, "head"] = point_op.head.m
                df.loc[i, "power"] = point_op.power.m
                df.loc[i, "p_disch"] = point_op.disch.p("bar").m
                df.loc[i, "expected_eff"] = point_expected.eff.m
                df.loc[i, "expected_head"] = point_expected.head.m
                df.loc[i, "expected_power"] = point_expected.power.m
                df.loc[i, "expected_p_disch"] = point_expected.disch.p("bar").m
                df.loc[i, "delta_eff"] = (point_op.eff - point_expected.eff).m * 100
                df.loc[i, "delta_head"] = (
                    (point_op.head - point_expected.head) / point_expected.head
                ).m * 100
                df.loc[i, "delta_power"] = (
                    (point_op.power - point_expected.power) / point_expected.power
                ).m * 100
                df.loc[i, "delta_p_disch"] = (
                    (point_op.disch.p("bar") - point_expected.disch.p("bar"))
                    / point_expected.disch.p("bar")
                ).m * 100

        # plot eff in plot with colormap showing the time

        # define the time delta and use that as a scale from 0 to 100
        total_time = df.index[-1] - df.index[0]

        # create column for timescale
        df["timescale"] = 0.0

        if len(df) > 1:
            for i, row in df.iterrows():
                # calculate seconds from i sample to start. Remember that i here is the index which is datetime
                sample_time = i - df.index[0]
                df.loc[i, "timescale"] = sample_time.seconds / total_time.seconds

        return df

    def save(self, path):
        # create zip file and save dataframe as parquet and impellers
        with zipfile.ZipFile(path, "w") as zip_file:
            zip_file.writestr("data.parquet", self.data.to_parquet())
            zip_file.writestr("df.parquet", self.df.to_parquet())
            for i, imp in enumerate(self.impellers):
                # write pickle file to zip
                with zip_file.open(f"imp_{i}.pickle", "w") as pickle_file:
                    pickle.dump(imp, pickle_file)
            for i, imp in enumerate(self.impellers_new):
                with zip_file.open(f"imp_new_{i}.pickle", "w") as pickle_file:
                    pickle.dump(imp, pickle_file)
            # create dict with arguments and save to toml
            args_dict = {
                "operation_fluid": self.operation_fluid,
                "data_units": self.data_units,
                "window": self.window,
                "temperature_fluctuation": self.temperature_fluctuation,
                "pressure_fluctuation": self.pressure_fluctuation,
                "speed_fluctuation": self.speed_fluctuation,
            }
            zip_file.writestr("args.toml", toml.dumps(args_dict))

    @classmethod
    def load(cls, path):
        with zipfile.ZipFile(path, "r") as zip_file:
            # load args
            # create file object to read the toml file
            args_dict = toml.loads(zip_file.read("args.toml").decode("utf-8"))
            # load initial data
            data = pd.read_parquet(zip_file.open("data.parquet"))
            # load dataframe
            df = pd.read_parquet(zip_file.open("df.parquet"))
            # load impellers
            impellers = []
            for i in range(len(zip_file.filelist)):
                if (
                    zip_file.filelist[i].filename.startswith("imp_")
                    and "new" not in zip_file.filelist[i].filename
                ):
                    with zip_file.open(
                        zip_file.filelist[i].filename, "r"
                    ) as pickle_file:
                        impellers.append(pickle.load(pickle_file))
            # load impellers_new
            impellers_new = []
            for i in range(len(zip_file.filelist)):
                if zip_file.filelist[i].filename.startswith("imp_new_"):
                    with zip_file.open(
                        zip_file.filelist[i].filename, "r"
                    ) as pickle_file:
                        impellers_new.append(pickle.load(pickle_file))
            evaluation = cls(
                data=data,
                impellers=impellers,
                operation_fluid=args_dict["operation_fluid"],
                data_units=args_dict["data_units"],
                window=args_dict["window"],
                temperature_fluctuation=args_dict["temperature_fluctuation"],
                pressure_fluctuation=args_dict["pressure_fluctuation"],
                speed_fluctuation=args_dict["speed_fluctuation"],
                impellers_new=impellers_new,
                df=df,
            )
            evaluation.impellers_new = impellers_new

            return evaluation


def create_points_parallel(x):
    if not x["valid"]:
        return None
    # delete arguments not used for point calculation
    del x["imp_new"]
    del x["valid"]
    try:
        p = Point(**x)
    except:
        print("Error for point with args:", x)
        return None
    return p


def get_interpolated_point(x):
    if not x["valid"]:
        return None
    try:
        imp_new = x["imp_new"]
        expected_point = imp_new.point(flow_v=x["flow_v"], speed=x["speed"])
    except:
        print("Error for expected point with args:", x)
    return expected_point
