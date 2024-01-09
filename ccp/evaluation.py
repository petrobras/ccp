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
        verbose=False,
        **kwargs,
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
        verbose : bool, optional
            If True, shows progress bar.

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

        # check if we are loading from a zip file where the impellers are available
        if kwargs.get("impellers_new") is None:
            print("running")
            self._run()
        else:
            self.impellers_new = kwargs.get("impellers_new")
            self.df = kwargs.get("df")

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

        # create density column
        df["v_s"] = 0
        df["speed_sound"] = 0
        for i, row in df.iterrows():
            # create state
            state = State(
                p=Q_(row.ps, self.data_units["ps"]),
                T=Q_(row.Ts, self.data_units["Ts"]),
                fluid=self.operation_fluid,
            )
            df.loc[i, "v_s"] = state.v().m
            df.loc[i, "speed_sound"] = state.speed_sound().m

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

        # create clusters based on speed_sound, ps and Ts
        data = df[["speed_sound", "ps", "Ts"]]
        # normalize
        data_mean = data.mean()
        data_std = data.std()
        data_norm = (data - data_mean) / data_std

        # Using sklearn
        kmeans = KMeans(n_clusters=5, n_init="auto")
        kmeans.fit(data_norm)

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
            suc_new = State(
                p=Q_(cluster_series.ps_center, self.data_units["ps"]),
                T=Q_(cluster_series.Ts_center, self.data_units["Ts"]),
                fluid=self.operation_fluid,
            )
            imp_new = Impeller.convert_from(self.impellers, suc=suc_new, speed="same")
            self.impellers_new.append(imp_new)

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
                    fluid=self.operation_fluid,
                ),
                "disch": State(
                    p=Q_(row.pd, self.data_units["pd"]),
                    T=Q_(row.Td, self.data_units["Td"]),
                    fluid=self.operation_fluid,
                ),
                "imp_new": self.impellers_new[int(row.cluster)],
            }

            args_list.append(arg_dict)

        with multiprocessing.Pool() as pool:
            print("Calculating points...")
            points += tqdm(pool.imap(create_points_parallel, args_list))
            print("Calculating expected points...")
            expected_points += tqdm(pool.imap(get_interpolated_point, args_list))

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
    del x["imp_new"]
    try:
        p = Point(**x)
    except:
        print("Error for point with args:", x)
    return p


def get_interpolated_point(x):
    try:
        imp_new = x["imp_new"]
        expected_point = imp_new.point(flow_m=x["flow_m"], speed=x["speed"])
    except:
        print("Error for expected point with args:", x)
    return expected_point
