"""Module for performance evaluation based on historical data."""

import zipfile
import toml
import numpy as np
import pandas as pd
import pickle
from .data_io import filter_data
from .state import State, _IdealGasState
from .point import Point, PhaseWarning, _check_one_gas_model
from .fo import FlowOrifice
from .fc import FlowCone, FlowMeterWarning, _cone_geometry, _discharge_coefficient
from .impeller import Impeller
from .parallel import create_pool
from . import Q_, config
from .config.units import _ambient_pascal, gauge_reference_unit, gauge_to_absolute
from sklearn.cluster import KMeans
from tqdm.auto import tqdm
import warnings

# columns of the data that hold pressures, the only ones read in gauge units
_PRESSURE_COLUMNS = ("ps", "pd", "p_upstream", "p_downstream")


def _allow_wet_cluster_suction(suc, cluster):
    """Warn, naming the cluster, when a cluster centre suction is not single phase.

    Plant data with heavy components can put a cluster centre at or just inside
    the dew line. The evaluation converts the curves with the unconstrained
    state; marking it keeps ``Point`` from repeating the warning without the
    cluster.
    """
    if suc.phase:
        return
    try:
        quality = suc.Q()
    except ValueError:
        return
    if 0.0 <= quality <= 1.0:
        warnings.warn(
            f"Cluster {cluster} suction lies at or inside the phase envelope "
            f"(vapour quality {quality:.4g}, p={suc.p('bar'):.3~P}, "
            f"T={suc.T('degC'):.2f~P}); the curves are converted with this "
            "two-phase suction. Check the fluid composition and the operating "
            "data of this cluster.",
            PhaseWarning,
            stacklevel=3,
        )
        suc._allow_two_phase_suction = True


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
        tappings="flange",
        verbose=False,
        n_clusters=5,
        calculate_points=True,
        parallel=True,
        flow_meter="orifice",
        dc=None,
        C=None,
        ambient_pressure=None,
        driver=None,
        transmission_efficiency=1.0,
        cluster_on_composition=False,
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
            - Delta p: should be 'delta_p' (Pa) in the DataFrame, with the
              pressure at the flow meter, 'p_upstream' or 'p_downstream' (Pa),
              when the flow is calculated from a flow meter (see ``flow_meter``);
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
            Dictionary with data units for each column. Gauge units (e.g. "barg")
            can be used for the pressures ('ps', 'pd', 'p_upstream' and
            'p_downstream') but not for 'delta_p'.
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
            Pipe internal diameter at the flow meter (m).
        d : float, pint.Quantity
            Orifice bore diameter (m). For a cone meter, the equivalent
            diameter d = beta * D (m); ``dc`` can be given instead.
        tappings : str, optional
            Tappings of the orifice.
            Options are "flange", "corner" or "D D/2".
            Default is "flange".
        flow_meter : str, optional
            Flow meter used to calculate the flow from 'delta_p' when the data
            has no flow column: "orifice" (orifice plate, ISO 5167-2, see
            ccp.FlowOrifice) or "cone" (cone meter, ISO 5167-5, see
            ccp.FlowCone).
            Default is "orifice".
        dc : float, pint.Quantity, optional
            Cone diameter of a cone meter (m), as an alternative to ``d``.
        C : float, callable or array_like, optional
            Discharge coefficient of a cone meter: None for the ISO 5167-5
            value of an uncalibrated meter, a calibrated value, a callable
            C(Re) or a calibration table (Re, C). See ccp.FlowCone.
            Readings outside the limits of ISO 5167-5 are reported with one
            ccp.fc.FlowMeterWarning per limit, giving the number of rows.
        ambient_pressure : float, pint.Quantity, optional
            Ambient pressure (Pa) of the data in gauge units, kept with the
            evaluation.
            The default is the value of ccp.config.AMBIENT_PRESSURE when the
            evaluation is created.
        n_clusters : int, optional
            Number of clusters to be used in the K-means algorithm.
            The default is 5.
        calculate_points : bool, optional
            If True, calculates the performance points for the given data.
            The default is True.
        parallel : bool, optional
            If True, uses multiprocessing for point calculation.
            Set to False for debugging to get detailed error messages.
            Ignored (runs serially) when parallel execution is globally
            disabled with ccp.config.PARALLEL = False or CCP_PARALLEL=0.
            The default is True.
        verbose : bool, optional
            If True, shows progress bar.
        driver : ccp.Driver, optional
            Driver used to estimate the shaft power it delivers from the
            ``driver_*`` columns of ``data`` (e.g. ``driver_input_power``,
            ``driver_current`` for an ``InductionMotor``; the suffix is the
            argument of ``driver.estimate``). Not needed when ``data`` has a
            ``power_driver`` column (driver shaft power, W unless set in
            ``data_units``). With either, the results get
            ``power_coupling`` (driver power times
            ``transmission_efficiency``, W) and ``delta_power_balance``
            (``power_coupling`` minus the compressor shaft power, % of the
            compressor shaft power).
        transmission_efficiency : float, optional
            Coupling and gearbox efficiency between the driver and the
            compressor, applied to the driver power. The default is 1.0.
        cluster_on_composition : bool, optional
            If True, the molar mass of the gas is a clustering feature, so
            rows with different compositions get different converted curves.
            Only used with ``fluid_*`` columns. The default is False.

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
        self.ambient_pressure = Q_(
            _ambient_pascal(
                config.AMBIENT_PRESSURE
                if ambient_pressure is None
                else ambient_pressure
            ),
            "pascal",
        )
        if self._gauge_reference("delta_p") is not None:
            raise ValueError(
                "'delta_p' is a pressure difference and cannot be in the gauge "
                f"unit {data_units['delta_p']!r}."
            )
        self.temperature_fluctuation = temperature_fluctuation
        self.pressure_fluctuation = pressure_fluctuation
        self.speed_fluctuation = speed_fluctuation
        self.impellers = impellers
        if impellers:
            _check_one_gas_model([imp.points[0] for imp in impellers])
        self.D = D
        self.d = d
        self.tappings = tappings
        self.flow_meter = flow_meter
        self.dc = dc
        self.C = C
        self._check_flow_meter()
        self.n_clusters = n_clusters
        self.parallel = parallel
        self.driver = driver
        self.transmission_efficiency = transmission_efficiency
        self.cluster_on_composition = cluster_on_composition

        # check if we are loading from a zip file where the impellers are available
        if kwargs.get("impellers_new") is None:
            self._run()
            if calculate_points:
                self.df = self.calculate_points()
        else:
            self.impellers_new = kwargs.get("impellers_new")
            self.df = kwargs.get("df")

    def _check_flow_meter(self):
        """Check the flow meter definition once, not on every row.

        The flow calculation marks rows that raise ValueError as invalid, so an
        invalid meter definition would otherwise invalidate every row quietly.
        """
        if self.flow_meter not in ("orifice", "cone"):
            raise ValueError(
                f'flow_meter must be "orifice" or "cone", got {self.flow_meter!r}.'
            )
        if self.D is None:
            return
        if self.flow_meter == "cone":
            _cone_geometry(self.D, self.d, self.dc)
            _discharge_coefficient(self.C)
        elif self.tappings not in ("flange", "corner", "D D/2"):
            raise ValueError(
                'tappings must be "flange", "corner" or "D D/2", '
                f"got {self.tappings!r}."
            )

    def _flow_meter(self, state, delta_p, state_upstream):
        """Flow meter of the data (FlowOrifice or FlowCone) for one row."""
        if self.flow_meter == "cone":
            return FlowCone(
                state,
                delta_p,
                self.D,
                self.d,
                dc=self.dc,
                C=self.C,
                state_upstream=state_upstream,
            )
        return FlowOrifice(
            state,
            delta_p,
            self.D,
            self.d,
            tappings=self.tappings,
            state_upstream=state_upstream,
        )

    def _gauge_reference(self, column):
        """Absolute unit of a column in a gauge unit, None for the other columns."""
        unit = (self.data_units or {}).get(column)
        # other columns can have units that pint does not know (ppm)
        if not unit or column not in (*_PRESSURE_COLUMNS, "delta_p"):
            return None
        try:
            return gauge_reference_unit(unit)
        except (AttributeError, ValueError, TypeError):
            # not a unit: raises where the column is used, if it is
            return None

    def _pressure(self, value, column):
        """Pressure of a column, absolute if the column is in a gauge unit."""
        reference = self._gauge_reference(column)
        if reference is None:
            return Q_(value, self.data_units[column])
        return gauge_to_absolute(Q_(value, reference), self.ambient_pressure).to(
            "pascal"
        )

    def _filter_dataframe(self, data, drop_invalid_values=True):
        """Apply fluctuation filtering with current instance parameters.

        The fluctuation and the check for negative values are those of the
        absolute pressures. Driver columns are averaged over the same window
        but do not take part in the filter: a missing driver reading must not
        drop the row.
        """
        offsets = {
            column: self.ambient_pressure.to(reference).m
            for column in data.columns
            if (reference := self._gauge_reference(column)) is not None
        }
        if offsets:
            data = data.copy()
            for column, offset in offsets.items():
                data[column] = pd.to_numeric(data[column]) + offset
        df = self._filter_absolute(data, drop_invalid_values)
        for column, offset in offsets.items():
            df[column] = df[column] - offset
        return df

    def _filter_absolute(self, data, drop_invalid_values):
        optional = [c for c in data.columns if _is_driver_column(c)]
        filtered = filter_data(
            data.drop(columns=optional),
            data_type=self.data_type,
            window=self.window,
            temperature_fluctuation=self.temperature_fluctuation,
            pressure_fluctuation=self.pressure_fluctuation,
            speed_fluctuation=self.speed_fluctuation,
            drop_invalid_values=drop_invalid_values,
        )
        if optional:
            means = (
                data[optional]
                .apply(pd.to_numeric)
                .rolling(window=self.window, min_periods=1)
                .mean()
            )
            filtered = filtered.join(means.loc[filtered.index])
        return filtered

    @property
    def cluster_features(self):
        """Columns used by the k-means clustering of the operating data."""
        features = ["speed_sound", "ps", "Ts"]
        if getattr(self, "cluster_on_composition", False) and self.fluid_columns:
            features.append("molar_mass")
        return features

    @staticmethod
    def _align_timestamp_to_reference(ts, reference_ts):
        """Align timestamp timezone to match the reference timestamp."""
        ts = pd.Timestamp(ts)
        reference_ts = pd.Timestamp(reference_ts)

        if reference_ts.tz is None and ts.tz is not None:
            return ts.tz_localize(None)
        if reference_ts.tz is not None and ts.tz is None:
            return ts.tz_localize(reference_ts.tz)
        if reference_ts.tz is not None and ts.tz is not None:
            return ts.tz_convert(reference_ts.tz)
        return ts

    def _ensure_incremental_artifacts(self):
        """Ensure model artifacts needed by incremental mode are available."""
        missing = []
        for attr in ("kmeans", "data_mean", "data_std", "impellers_new"):
            if getattr(self, attr, None) is None:
                missing.append(attr)
        if missing:
            raise RuntimeError(
                "Incremental update artifacts are missing: "
                f"{missing}. Run a Full Rebuild first."
            )

    def _assign_clusters(self, df):
        """Assign cluster id to each row using fitted model and scaling."""
        df = df.copy()
        features = df[list(self.data_mean.index)]
        features_norm = (features - self.data_mean) / self.data_std
        # rows with NaN features (invalid rows kept in the dataframe) get a
        # placeholder cluster; they are skipped in the point calculation
        complete = features_norm.notna().all(axis=1)
        df["cluster"] = 0
        if complete.any():
            df.loc[complete, "cluster"] = self.kmeans.predict(features_norm[complete])
        return df

    def _calculate_points_from_prepared_df(self, df, parallel=None):
        """Calculate points from a dataframe with flow and cluster columns."""
        if parallel is None:
            parallel = self.parallel

        # One task per row carrying scalars only: the states are built in the
        # worker (their flash is the row's main cost and runs in parallel) and
        # the converted impellers are shipped once per worker through the pool
        # initializer instead of being unpickled by every task.
        args_list = []
        for i, row in df.iterrows():
            if self.operation_fluid is not None:
                fluid = self.operation_fluid
            else:
                fluid = self._get_fluid_composition(row)

            # Get 'valid' value safely (default to True if not present)
            is_valid = row.valid if "valid" in row.index else True
            if not is_valid:
                # skip state construction: invalid rows can hold NaN inputs
                args_list.append({"valid": False})
                continue

            args_list.append(
                {
                    "flow_v": row.flow_v,
                    "speed": Q_(row.speed, self.data_units["speed"]),
                    "ps": self._pressure(row.ps, "ps"),
                    "Ts": Q_(row.Ts, self.data_units["Ts"]),
                    "pd": self._pressure(row.pd, "pd"),
                    "Td": Q_(row.Td, self.data_units["Td"]),
                    "fluid": fluid,
                    "EOS": self._EOS,
                    "cluster": int(row.cluster),
                    "valid": True,
                }
            )

        # parallel=False (a debugging switch) and a global disable both
        # yield the serial stand-in, keeping a single pipeline.
        with create_pool(
            parallel=parallel,
            initializer=_init_worker_impellers,
            initargs=(self.impellers_new,),
            tasks=len(args_list),
        ) as pool:
            print("Calculating points and expected points...")
            chunksize = max(1, len(args_list) // 64)
            results = list(
                tqdm(
                    pool.imap(calculate_evaluation_point, args_list, chunksize),
                    total=len(args_list),
                )
            )

        n = len(df)
        # -1.0 marks rows where points were not computed (typically invalid rows).
        value_columns = [
            "eff",
            "head",
            "power",
            "p_disch",
            "expected_eff",
            "expected_head",
            "expected_power",
            "expected_p_disch",
            "delta_eff",
            "delta_head",
            "delta_power",
            "delta_p_disch",
        ]
        values = {name: np.full(n, -1.0) for name in value_columns}
        # analytics columns: NaN where not computed
        kpi_values = {name: np.full(n, np.nan) for name in KPI_COLUMNS}
        # Error tracking columns
        error_columns = ["error", "error_type", "expected_error", "expected_error_type"]
        errors = {name: [None] * n for name in error_columns}
        invalid_rows = []

        for k, (i, result) in enumerate(zip(df.index, results)):
            if result["invalid_state"]:
                invalid_rows.append(i)
                continue
            point_op = result["point"]
            error_info = result["error"]
            point_expected = result["expected"]
            expected_error = result["expected_error"]

            # Store error info if calculation failed
            if error_info is not None:
                errors["error"][k] = error_info["exception"]
                errors["error_type"][k] = error_info["type"]
                if not parallel:
                    # In sequential mode, print full traceback for debugging
                    print(f"Error at index {i}: {error_info['traceback']}")

            if expected_error is not None:
                errors["expected_error"][k] = expected_error["exception"]
                errors["expected_error_type"][k] = expected_error["type"]
                if not parallel:
                    print(
                        f"Expected point error at index {i}: {expected_error['traceback']}"
                    )

            # point_op/point_expected are None when row is invalid or failed.
            if point_op is not None and point_expected is not None:
                eff_op = point_op.eff.m
                head_op = point_op.head.m
                power_op = point_op.power.m
                p_disch_op = point_op.disch.p("bar").m
                eff_exp = point_expected.eff.m
                head_exp = point_expected.head.m
                power_exp = point_expected.power.m
                p_disch_exp = point_expected.disch.p("bar").m
                values["eff"][k] = eff_op
                values["head"][k] = head_op
                values["power"][k] = power_op
                values["p_disch"][k] = p_disch_op
                values["expected_eff"][k] = eff_exp
                values["expected_head"][k] = head_exp
                values["expected_power"][k] = power_exp
                values["expected_p_disch"][k] = p_disch_exp
                values["delta_eff"][k] = (eff_op - eff_exp) * 100
                values["delta_head"][k] = (head_op - head_exp) / head_exp * 100
                values["delta_power"][k] = (power_op - power_exp) / power_exp * 100
                values["delta_p_disch"][k] = (
                    (p_disch_op - p_disch_exp) / p_disch_exp * 100
                )
                for name, value in result["kpis"].items():
                    kpi_values[name][k] = value

        for name in value_columns:
            df[name] = values[name]
        for name in KPI_COLUMNS:
            df[name] = kpi_values[name]
        power_coupling = self._driver_power(df)
        if power_coupling is not None:
            df["power_coupling"] = power_coupling
            df["delta_power_balance"] = (
                (power_coupling - df["power_shaft"]) / df["power_shaft"] * 100
            )
        for name in error_columns:
            df[name] = errors[name]
        if invalid_rows and "valid" in df.columns:
            df.loc[invalid_rows, "valid"] = False

        if len(df) > 1 and pd.api.types.is_datetime64_any_dtype(df.index):
            # Use elapsed fraction in [0, 1] for coloring over time.
            total_seconds = (df.index[-1] - df.index[0]).total_seconds()
            if total_seconds == 0:
                df["timescale"] = 0.0
            else:
                df["timescale"] = (
                    df.index - df.index[0]
                ).total_seconds() / total_seconds
        elif "timescale" not in df.columns:
            df["timescale"] = 0.0

        return df

    def append_new_data(
        self,
        new_data,
        drop_invalid_values=True,
        parallel=None,
        use_filter_history=True,
    ):
        """Append only new data rows and calculate points incrementally.

        Parameters
        ----------
        new_data : pandas.DataFrame
            Dataframe containing only new timestamps to evaluate.
        drop_invalid_values : bool, optional
            Drop invalid values from the dataframe.
            If False, a column 'valid' is added with True for valid rows.
            The default is True.
        parallel : bool, optional
            If True, uses multiprocessing for point calculation.
            If None, uses the value from the instance.
            Ignored (runs serially) when parallel execution is globally
            disabled with ccp.config.PARALLEL = False or CCP_PARALLEL=0.
        use_filter_history : bool, optional
            If True, prepends last window-1 rows from existing data to preserve
            fluctuation filtering continuity at the batch boundary.

        Returns
        -------
        pandas.DataFrame
            Only the newly calculated rows (same schema as self.df).
        """
        if new_data is None or new_data.empty:
            return pd.DataFrame()

        self._ensure_incremental_artifacts()

        if parallel is None:
            parallel = self.parallel

        required_cols = ["ps", "Ts", "pd", "Td", "speed"]
        missing_cols = [c for c in required_cols if c not in new_data.columns]
        if missing_cols:
            raise ValueError(
                "New data is missing required columns for incremental "
                f"evaluation: {missing_cols}"
            )

        new_df = new_data.copy().sort_index()

        if isinstance(new_df.index, pd.DatetimeIndex) and isinstance(
            self.data.index, pd.DatetimeIndex
        ):
            if self.data.index.tz is None and new_df.index.tz is not None:
                new_df.index = new_df.index.tz_localize(None)
            elif self.data.index.tz is not None and new_df.index.tz is None:
                new_df.index = new_df.index.tz_localize(self.data.index.tz)
            elif (
                self.data.index.tz is not None
                and new_df.index.tz is not None
                and new_df.index.tz != self.data.index.tz
            ):
                new_df.index = new_df.index.tz_convert(self.data.index.tz)

        # Keep only strictly new rows based on current evaluation data.
        if self.data is not None and not self.data.empty:
            last_index = self.data.index.max()
            new_df = new_df[new_df.index > last_index]

        if new_df.empty:
            return pd.DataFrame()

        filter_input = new_df
        context_len = max(self.window - 1, 0)
        if (
            use_filter_history
            and context_len > 0
            and self.data is not None
            and not self.data.empty
        ):
            history_context = self.data.tail(context_len)
            filter_input = pd.concat([history_context, new_df]).sort_index()

        filtered = self._filter_dataframe(
            filter_input, drop_invalid_values=drop_invalid_values
        )
        filtered = filtered[filtered.index.isin(new_df.index)]

        if filtered.empty:
            return pd.DataFrame()

        filtered = self.calculate_flow(filtered)
        filtered = filtered.dropna(subset=["speed_sound", "v_s"])

        if filtered.empty:
            return pd.DataFrame()

        if "valid" not in filtered.columns:
            filtered["valid"] = True

        prepared = self._assign_clusters(filtered)
        df_new_points = self._calculate_points_from_prepared_df(
            prepared, parallel=parallel
        )

        # Append raw and calculated datasets, preserving the newest value in duplicates.
        self.data = pd.concat([self.data, new_df])
        self.data = self.data[~self.data.index.duplicated(keep="last")].sort_index()

        self.df = pd.concat([self.df, df_new_points])
        self.df = self.df[~self.df.index.duplicated(keep="last")].sort_index()

        return df_new_points

    def _driver_power(self, df):
        """Driver power delivered at the compressor coupling (W) for each row.

        From a ``power_driver`` column, or from ``self.driver`` and the
        ``driver_*`` measurement columns. None when neither is available.
        """
        units = self.data_units or {}
        efficiency = getattr(self, "transmission_efficiency", 1.0)
        if "power_driver" in df.columns:
            power = Q_(
                df["power_driver"].to_numpy(dtype=float),
                units.get("power_driver", "W"),
            )
            return power.to("W").m * efficiency
        driver = getattr(self, "driver", None)
        if driver is None:
            return None
        columns = [c for c in df.columns if c.startswith("driver_")]
        power = np.full(len(df), np.nan)
        for k, (_, row) in enumerate(df[columns].iterrows()):
            measurements = {
                c[len("driver_") :]: Q_(row[c], units[c]) if c in units else row[c]
                for c in columns
                if pd.notna(row[c])
            }
            try:
                power[k] = driver.power_output(**measurements).to("W").m
            except (ValueError, TypeError, ZeroDivisionError):
                continue
        return power * efficiency

    def trends(self, kpis=None, **kwargs):
        """Trends, change points and time to threshold of the KPI columns.

        See :func:`ccp.analytics.trends.analyse_trends` for the parameters.

        Returns
        -------
        report : ccp.analytics.TrendReport
        """
        from .analytics.trends import analyse_trends

        return analyse_trends(self.df, kpis=kpis, **kwargs)

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
        df = self._filter_dataframe(self.data.copy())

        # Check if dataframe is empty after filtering
        if df.empty:
            raise ValueError(
                "DataFrame is empty after filtering. "
                "All rows were removed due to fluctuation criteria. "
                "This can happen when sensors have frozen values (e.g., stuck at zero). "
                "Please check your data or adjust the filtering parameters "
                "(temperature_fluctuation, pressure_fluctuation, speed_fluctuation)."
            )

        df = self.calculate_flow(df)

        # Remove rows with NaN values (can occur in two-phase region)
        df = df.dropna(subset=["speed_sound", "v_s"])

        # create clusters based on speed_sound, ps and Ts (and molar mass)
        data = df[self.cluster_features]
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
                kmeans.cluster_centers_[i][2] * data_std["Ts"]
            ) + data_mean["Ts"]

        self.impellers_new = []

        print("Converting curves")
        for i in tqdm(range(kmeans.n_clusters)):
            cluster_rows = df[df["cluster"] == i]
            cluster_series = cluster_rows.iloc[0]
            if self.operation_fluid is not None:
                fluid = self.operation_fluid
            else:
                # mean composition of the cluster, not the composition of
                # whichever row comes first
                fluid = self._get_fluid_composition(
                    cluster_rows[self.fluid_columns].mean()
                )
            suc_new = State(
                p=self._pressure(cluster_series.ps_center, "ps"),
                T=Q_(cluster_series.Ts_center, self.data_units["Ts"]),
                fluid=fluid,
                EOS=self._EOS,
            )
            _allow_wet_cluster_suction(suc_new, i)
            imp_new = Impeller.convert_from(self.impellers, suc=suc_new, speed="same")
            self.impellers_new.append(imp_new)

        self.df = df

    @property
    def _EOS(self):
        """Model of the operating data: ideal if the impellers are, else the default."""
        suc = (self.impellers or self.impellers_new)[0].points[0].suc
        return suc.EOS if isinstance(suc, _IdealGasState) else config.EOS

    def calculate_flow(self, data=None):
        """Add the flow, 'v_s' and 'speed_sound' columns to the data.

        When the data has no 'flow_v' or 'flow_m' column, the flow is
        calculated from 'delta_p' with the flow meter of the evaluation.
        """
        # a cone meter warns about the ISO 5167-5 limits on each row: report
        # each limit once, with the number of rows, instead of once per row
        outside_limits = {}
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", FlowMeterWarning)
            df, n_meter_rows = self._calculate_flow(data, outside_limits)
        for count, message in outside_limits.values():
            warnings.warn(
                f"{message} Found in {count} of {n_meter_rows} rows; the values "
                "shown are those of the first one.",
                FlowMeterWarning,
                stacklevel=2,
            )
        return df

    def _calculate_flow(self, data, outside_limits):
        df = data
        n_meter_rows = 0
        calculate_flow = False
        if not ("flow_v" in df.columns or "flow_m" in df.columns):
            calculate_flow = True
            if self.D is None:
                raise ValueError(
                    "The data has no 'flow_v' or 'flow_m' column: give the flow "
                    "meter geometry (D, and d or dc) to calculate the flow from "
                    "'delta_p'."
                )

        # create density column
        df["v_s"] = 0.0
        df["speed_sound"] = 0.0

        for i, row in df.iterrows():
            # rows marked invalid can carry NaN inputs that CoolProp rejects
            if "valid" in df.columns and not row.valid:
                continue

            if self.operation_fluid is not None:
                fluid = self.operation_fluid
            else:
                fluid = self._get_fluid_composition(row)

            try:
                if calculate_flow:
                    if "p_downstream" in df.columns:
                        state_upstream = False
                        state = State(
                            p=self._pressure(row.p_downstream, "p_downstream"),
                            T=Q_(row.Ts, self.data_units["Ts"]),
                            fluid=fluid,
                            EOS=self._EOS,
                        )
                    elif "p_upstream" in df.columns:
                        state_upstream = True
                        state = State(
                            p=self._pressure(row.p_upstream, "p_upstream"),
                            T=Q_(row.Ts, self.data_units["Ts"]),
                            fluid=fluid,
                            EOS=self._EOS,
                        )
                    else:
                        raise ValueError(
                            "Pressure upstream/downstream fo not found in the DataFrame."
                        )

                    delta_p = Q_(row.delta_p, self.data_units["delta_p"])
                    meter = self._flow_meter(state, delta_p, state_upstream)
                    # upstream state of the meter (p + delta_p for a downstream
                    # state); v_s and flow_v are taken at it
                    state = meter.state
                    n_meter_rows += 1
                    for limit, message in getattr(meter, "outside_limits", {}).items():
                        outside_limits.setdefault(limit, [0, message])[0] += 1
                    df.loc[i, "flow_m"] = meter.flow_m.m
                    df.loc[i, "flow_v"] = meter.flow_v.m
                else:
                    state = State(
                        p=self._pressure(row.ps, "ps"),
                        T=Q_(row.Ts, self.data_units["Ts"]),
                        fluid=fluid,
                        EOS=self._EOS,
                    )
            except ValueError:
                # NaN or out-of-range inputs (e.g. sensor dropouts): mark the row
                # invalid when invalid rows are being kept, otherwise fail loudly
                if "valid" in df.columns:
                    df.loc[i, "valid"] = False
                    continue
                raise

            df.loc[i, "v_s"] = state.v().m
            df.loc[i, "speed_sound"] = state.speed_sound().m
            if self.fluid_columns:
                df.loc[i, "molar_mass"] = state.molar_mass().m

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

        return df, n_meter_rows

    def calculate_points(self, data=None, drop_invalid_values=True, parallel=None):
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
        parallel : bool, optional
            If True, uses multiprocessing for point calculation.
            Set to False for debugging to get detailed error messages.
            If None, uses the value from the instance.
            Ignored (runs serially) when parallel execution is globally
            disabled with ccp.config.PARALLEL = False or CCP_PARALLEL=0.
            The default is None.

        Returns
        -------
        df : pandas.DataFrame
            DataFrame with the calculated points.
        """
        if parallel is None:
            parallel = self.parallel

        if data is None:
            df = self.df.copy()
            if "valid" not in df.columns:
                df["valid"] = True
            if "cluster" not in df.columns:
                df = self._assign_clusters(df)
            return self._calculate_points_from_prepared_df(df, parallel=parallel)

        df = data.copy()
        df = self._filter_dataframe(df, drop_invalid_values=drop_invalid_values)

        # Check if dataframe is empty after filtering
        if df.empty:
            raise ValueError(
                "DataFrame is empty after filtering. "
                "All rows were removed due to fluctuation criteria. "
                "Please check your data or adjust the filtering parameters "
                "(temperature_fluctuation, pressure_fluctuation, speed_fluctuation)."
            )

        if "valid" not in df.columns:
            df["valid"] = True

        df = self.calculate_flow(df)
        df = self._assign_clusters(df)
        return self._calculate_points_from_prepared_df(df, parallel=parallel)

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
            with zip_file.open("kmeans.pickle", "w") as pickle_file:
                pickle.dump(self.kmeans, pickle_file)
            zip_file.writestr(
                "data_mean.parquet", self.data_mean.to_frame().to_parquet()
            )
            zip_file.writestr("data_std.parquet", self.data_std.to_frame().to_parquet())
            # create dict with arguments and save to toml
            args_dict = {
                "operation_fluid": self.operation_fluid,
                "data_units": self.data_units,
                "window": self.window,
                "temperature_fluctuation": self.temperature_fluctuation,
                "pressure_fluctuation": self.pressure_fluctuation,
                "speed_fluctuation": self.speed_fluctuation,
                "ambient_pressure": self.ambient_pressure.m,
                "transmission_efficiency": self.transmission_efficiency,
                "cluster_on_composition": self.cluster_on_composition,
            }
            if self.driver is not None:
                args_dict["driver"] = self.driver.to_dict()
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
            kmeans = None
            data_mean = None
            data_std = None
            if "kmeans.pickle" in zip_file.namelist():
                with zip_file.open("kmeans.pickle", "r") as pickle_file:
                    kmeans = pickle.load(pickle_file)
            if "data_mean.parquet" in zip_file.namelist():
                data_mean = pd.read_parquet(zip_file.open("data_mean.parquet")).iloc[
                    :, 0
                ]
            if "data_std.parquet" in zip_file.namelist():
                data_std = pd.read_parquet(zip_file.open("data_std.parquet")).iloc[:, 0]
            evaluation = cls(
                data=data,
                impellers=impellers,
                operation_fluid=args_dict.get("operation_fluid"),
                data_units=args_dict["data_units"],
                window=args_dict["window"],
                temperature_fluctuation=args_dict["temperature_fluctuation"],
                pressure_fluctuation=args_dict["pressure_fluctuation"],
                speed_fluctuation=args_dict["speed_fluctuation"],
                ambient_pressure=args_dict.get("ambient_pressure"),
                transmission_efficiency=args_dict.get("transmission_efficiency", 1.0),
                cluster_on_composition=args_dict.get("cluster_on_composition", False),
                driver=_load_driver(args_dict.get("driver")),
                impellers_new=impellers_new,
                df=df,
            )
            evaluation.impellers_new = impellers_new
            evaluation.kmeans = kmeans
            evaluation.data_mean = data_mean
            evaluation.data_std = data_std

            return evaluation


# per-row analytics columns computed with the expected point (see _row_kpis)
KPI_COLUMNS = [
    "flow_dev",
    "delta_Td",
    "health_index",
    "head_slope",
    "eff_slope",
    "power_shaft",
]


def _is_driver_column(column):
    return column == "power_driver" or column.startswith("driver_")


def _load_driver(data):
    if not data:
        return None
    from .drivers import InductionMotor

    return InductionMotor.from_dict(data)


def _curve_slopes(curve, flow_v, head):
    """Log-slopes of an expected curve at ``flow_v``.

    Returns ``d ln(head) / d ln(flow)`` and ``d eff / d ln(flow)``, where
    ``head`` is the expected head at ``flow_v``. The flow derivatives are
    those of the linear interpolation used by ``Impeller.point`` (the segment
    containing ``flow_v``, the first segment below the lowest flow). Above
    the highest flow ``Impeller.point`` uses a choke formula that is not a
    performance curve, so the slopes are NaN.
    """
    flow = curve["flow_v"]
    if flow_v > flow[-1]:
        return np.nan, np.nan
    i = int(np.clip(np.searchsorted(flow, flow_v) - 1, 0, len(flow) - 2))
    dflow = flow[i + 1] - flow[i]
    dhead = (curve["head"][i + 1] - curve["head"][i]) / dflow
    deff = (curve["eff"][i + 1] - curve["eff"][i]) / dflow
    return float(flow_v * dhead / head), float(flow_v * deff)


def _flow_at_head(curve, head, max_extrapolation=0.5):
    """Flow of the expected curve's stable branch with the given head.

    The stable branch runs from the highest head to the highest flow. Heads
    below the curve end are extrapolated with the last segment up to
    ``max_extrapolation`` times the branch flow range; heads above the peak
    have no solution (NaN).
    """
    flow = curve["flow_v"]
    heads = curve["head"]
    peak = int(np.argmax(heads))
    flow, heads = flow[peak:], heads[peak:]
    if len(flow) < 2 or head > heads[0]:
        return np.nan
    if head >= heads[-1]:
        return float(np.interp(head, heads[::-1], flow[::-1]))
    slope = (flow[-1] - flow[-2]) / (heads[-1] - heads[-2])
    value = flow[-1] + (head - heads[-1]) * slope
    if value - flow[-1] > max_extrapolation * (flow[-1] - flow[0]):
        return np.nan
    return float(value)


def _row_kpis(imp_new, point_op, point_expected):
    """Analytics values of one row (see KPI_COLUMNS)."""
    curve = imp_new._curve_data(point_expected.speed)
    flow_v = point_op.flow_v.m
    head_slope, eff_slope = _curve_slopes(curve, flow_v, point_expected.head.m)
    flow_exp = _flow_at_head(curve, point_op.head.m)
    return {
        "flow_dev": (flow_v - flow_exp) / flow_exp * 100,
        "delta_Td": point_op.disch.T().m - point_expected.disch.T().m,
        "health_index": point_op.eff.m / point_expected.eff.m,
        "head_slope": head_slope,
        "eff_slope": eff_slope,
        "power_shaft": point_op.power.m + point_expected.power_losses.m,
    }


# converted impellers of the Evaluation being calculated, set once per worker
# by the pool initializer (see create_pool) and indexed by cluster
_worker_impellers = None


def _init_worker_impellers(impellers):
    global _worker_impellers
    _worker_impellers = impellers


def _error_info(exc):
    import traceback

    return {
        "exception": str(exc),
        "type": type(exc).__name__,
        "traceback": traceback.format_exc(),
    }


def calculate_evaluation_point(x):
    """Operating point and expected point of one evaluation row.

    ``x`` holds scalars only (``ps``, ``Ts``, ``pd``, ``Td``, ``fluid``,
    ``flow_v``, ``speed``, ``cluster``, ``valid``); the states are built here
    and the expected point comes from the converted impeller of the row's
    cluster, shipped to the worker by the pool initializer.

    Returns
    -------
    dict
        ``point`` and ``expected`` (Point or None), ``error`` and
        ``expected_error`` (error info dicts with 'exception', 'type' and
        'traceback', or None) and ``invalid_state`` (True when the suction or
        discharge state could not be defined, which marks the row invalid).
        Rows with ``valid=False`` return all None: that is data that exceeded
        the fluctuation thresholds, not an error.
    """
    result = {
        "point": None,
        "error": None,
        "expected": None,
        "expected_error": None,
        "invalid_state": False,
        "kpis": {},
    }
    if not x.get("valid", True):
        return result
    try:
        suc = State(p=x["ps"], T=x["Ts"], fluid=x["fluid"], EOS=x["EOS"])
        disch = State(p=x["pd"], T=x["Td"], fluid=x["fluid"], EOS=x["EOS"])
    except ValueError:
        result["invalid_state"] = True
        return result
    try:
        result["point"] = Point(
            suc=suc, disch=disch, flow_v=x["flow_v"], speed=x["speed"]
        )
    except Exception as e:
        result["error"] = _error_info(e)
    try:
        imp_new = _worker_impellers[x["cluster"]]
        result["expected"] = imp_new.point(flow_v=x["flow_v"], speed=x["speed"])
    except Exception as e:
        result["expected_error"] = _error_info(e)
    if result["point"] is not None and result["expected"] is not None:
        try:
            result["kpis"] = _row_kpis(imp_new, result["point"], result["expected"])
        except Exception:
            # analytics are optional: keep the row with NaN KPIs
            pass
    return result


def create_points_parallel(x):
    """Create a Point from the given arguments.

    Returns
    -------
    tuple
        (Point or None, error_info or None)
        error_info is a dict with 'exception', 'type', and 'traceback' keys.
        For invalid data points (valid=False), returns (None, None) since this
        is expected behavior, not an error.
    """
    if not x.get("valid", True):
        # Not an error - just data that exceeded fluctuation thresholds
        return (None, None)
    # Create a copy and remove arguments not used for point calculation
    point_args = {k: v for k, v in x.items() if k not in ("imp_new", "valid")}
    try:
        p = Point(**point_args)
        return (p, None)
    except Exception as e:
        import traceback

        error_info = {
            "exception": str(e),
            "type": type(e).__name__,
            "traceback": traceback.format_exc(),
        }
        return (None, error_info)


def get_interpolated_point(x):
    """Get the expected point from the impeller curve.

    Returns
    -------
    tuple
        (Point or None, error_info or None)
        error_info is a dict with 'exception', 'type', and 'traceback' keys.
        For invalid data points (valid=False), returns (None, None) since this
        is expected behavior, not an error.
    """
    if not x.get("valid", True):
        # Not an error - just data that exceeded fluctuation thresholds
        return (None, None)
    try:
        imp_new = x["imp_new"]
        expected_point = imp_new.point(flow_v=x["flow_v"], speed=x["speed"])
        return (expected_point, None)
    except Exception as e:
        import traceback

        error_info = {
            "exception": str(e),
            "type": type(e).__name__,
            "traceback": traceback.format_exc(),
        }
        return (None, error_info)
