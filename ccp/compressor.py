"""Module to define compressors with 1 or 2 sections."""

from copy import copy

import ccp
import toml
from ccp.impeller import Impeller
from ccp.point import Point, flow_from_phi
from ccp.state import State
from ccp.config.units import check_units
from ccp import Q_
import numpy as np
from scipy.optimize import newton


class Point1Sec(Point):
    """Point class for a compressor with 1 section.

    Parameters
    ----------
    balance_line_flow_m : float, pint.Quantity
        Balance line mass flow (kg/s).
    seal_gas_flow_m : float, pint.Quantity
        Seal gas mass flow (kg/s).
    seal_gas_temperature : float, pint.Quantity
        Seal gas injection temperature (degK).
    oil_flow_journal_bearing_de : float, pint.Quantity
        Oil flow journal bearing drive end side (m³/s).
    oil_flow_journal_bearing_nde : float, pint.Quantity
        Oil flow journal bearing non-drive end side (m³/s).
    oil_flow_thrust_bearing_nde : float, pint.Quantity
         Oil flow journal bearing thrust bearing (m³/s).
    oil_inlet_temperature : float, pint.Quantity
        Oil inlet temperature (degK).
    oil_outlet_temperature_de : float, pint.Quantity
        Oil outlet temperature journal bearing drive end side (degK).
    oil_outlet_temperature_nde : float, pint.Quantity
        Oil outlet temperature bearing non-drive end side (degK).
    oil_specific_heat_de : float, pint.Quantity
        Oil specific heat bearing drive end side (J/kg/degK).
    oil_specific_heat_nde : float, pint.Quantity
        Oil specific heat bearing non-drive end side (J/kg/degK).
    oil_density_de : float, pint.Quantity
        Oil Density bearing drive end side (kg/m³).
    oil_density_nde : float, pint.Quantity
        Oil density bearing non-drive end side (kg/m³).

    Returns
    -------
    point1sec : ccp.Point1Sec
        A point for a straight through compressor (inherited from ccp.Point).

    Examples
    --------
    >>> import ccp
    >>> p = Point1Sec(
    ...     flow_m=Q_(7.737, "kg/s"),
    ...     speed=Q_(7894, "RPM"),
    ...     b=Q_(28.5, "mm"),
    ...     D=Q_(365, "mm"),
    ...     suc=State(
    ...         p=Q_(1.826, "bar"),
    ...         T=Q_(296.7, "degK"),
    ...         fluid={
    ...             "carbon dioxide": 0.80218,
    ...             "R134a": 0.18842,
    ...             "nitrogen": 0.0091,
    ...             "oxygen": 0.0003,
    ...         },
    ...     ),
    ...     disch=State(
    ...         p=Q_(6.142, "bar"),
    ...         T=Q_(392.1, "degK"),
    ...         fluid={
    ...             "carbon dioxide": 0.80218,
    ...             "R134a": 0.18842,
    ...             "nitrogen": 0.0091,
    ...             "oxygen": 0.0003,
    ...         },
    ...     ),
    ...     balance_line_flow_m=Q_(0.1076, "kg/s"),
    ...     seal_gas_flow_m=Q_(0.04982, "kg/s"),
    ...     seal_gas_temperature=Q_(297.7, "degK"),
    ...     oil_flow_journal_bearing_de=Q_(27.084, "l/min"),
    ...     oil_flow_journal_bearing_nde=Q_(47.984, "l/min"),
    ...     oil_flow_thrust_bearing_nde=Q_(33.52, "l/min"),
    ...     oil_inlet_temperature=Q_(42.184, "degC"),
    ...     oil_outlet_temperature_de=Q_(48.111, "degC"),
    ...     oil_outlet_temperature_nde=Q_(46.879, "degC"),
    ...     oil_specific_heat_de=Q_(2.02, "kJ/kg/degK"),
    ...     oil_specific_heat_nde=Q_(2.02, "kJ/kg/degK"),
    ...     oil_density_de=Q_(846.9, "kg/m³"),
    ...     oil_density_nde=Q_(846.9, "kg/m³"),
    ...     casing_area=7.5,
    ...     casing_temperature=Q_(31.309, "degC"),
    ...     ambient_temperature=Q_(0, "degC"),
    ...     )

    """

    @check_units
    def __init__(
        self,
        *args,
        balance_line_flow_m=None,
        seal_gas_flow_m=None,
        seal_gas_temperature=None,
        oil_flow_journal_bearing_de=None,
        oil_flow_journal_bearing_nde=None,
        oil_flow_thrust_bearing_nde=None,
        oil_inlet_temperature=None,
        oil_outlet_temperature_de=None,
        oil_outlet_temperature_nde=None,
        oil_specific_heat_de=None,
        oil_specific_heat_nde=None,
        oil_density_de=None,
        oil_density_nde=None,
        leakages=True,
        bearing_mechanical_losses=True,
        **kwargs,
    ):
        super().__init__(
            *args,
            **kwargs,
        )
        self.balance_line_flow_m = balance_line_flow_m
        self.seal_gas_flow_m = seal_gas_flow_m
        self.seal_gas_temperature = seal_gas_temperature
        self.oil_flow_journal_bearing_de = oil_flow_journal_bearing_de
        self.oil_flow_journal_bearing_nde = oil_flow_journal_bearing_nde
        self.oil_flow_thrust_bearing_nde = oil_flow_thrust_bearing_nde
        self.oil_inlet_temperature = oil_inlet_temperature
        self.oil_outlet_temperature_de = oil_outlet_temperature_de
        self.oil_outlet_temperature_nde = oil_outlet_temperature_nde
        self.oil_specific_heat_de = oil_specific_heat_de
        self.oil_specific_heat_nde = oil_specific_heat_nde
        self.oil_density_de = oil_density_de
        self.oil_density_nde = oil_density_nde
        self.leakages = leakages
        self.bearing_mechanical_losses = bearing_mechanical_losses

        if not self.leakages:
            self.balance_line_flow_m = Q_(0, "kg/s")
            self.seal_gas_flow_m = Q_(0, "kg/s")
            self.seal_gas_temperature = self.suc.T()

        if not self.bearing_mechanical_losses:
            self.oil_flow_journal_bearing_de = Q_(0, "m³/s")
            self.oil_flow_journal_bearing_nde = Q_(0, "m³/s")
            self.oil_flow_thrust_bearing_nde = Q_(0, "m³/s")
            self.oil_inlet_temperature = self.suc.T()
            self.oil_outlet_temperature_de = self.suc.T()
            self.oil_outlet_temperature_nde = self.suc.T()
            oil_specific_heat_de = (Q_(2.02, "kJ/kg/degK"),)
            oil_specific_heat_nde = (Q_(2.02, "kJ/kg/degK"),)
            oil_density_de = (Q_(846.9, "kg/m³"),)
            oil_density_nde = (Q_(846.9, "kg/m³"),)

    def _dict_to_save(self):
        """Returns a dict that will be saved to a toml file."""
        dict_to_save = super()._dict_to_save()
        for param in [
            "balance_line_flow_m",
            "seal_gas_flow_m",
            "seal_gas_temperature",
            "oil_flow_journal_bearing_de",
            "oil_flow_journal_bearing_nde",
            "oil_flow_thrust_bearing_nde",
            "oil_inlet_temperature",
            "oil_outlet_temperature_de",
            "oil_outlet_temperature_nde",
            "oil_specific_heat_de",
            "oil_specific_heat_nde",
            "oil_density_de",
            "oil_density_nde",
        ]:
            if getattr(self, param):
                dict_to_save[param] = str(getattr(self, param))

        return dict_to_save


class StraightThrough(Impeller):
    """Straight Through compressor"""

    @check_units
    def __init__(
        self,
        guarantee_point,
        test_points,
        speed_operational=None,
        reynolds_correction=False,
        bearing_mechanical_losses=False,
    ):
        self.guarantee_point = guarantee_point
        self.test_points = test_points
        if speed_operational is None:
            speed_operational = guarantee_point.speed
        self.speed_operational = speed_operational
        self.reynolds_correction = reynolds_correction
        self.bearing_mechanical_losses = bearing_mechanical_losses

        # points for test flange conditions
        self.points_flange_t = test_points

        # calculate rotor condition
        test_points_rotor = []
        self.k_end_seal = []  # list with seal constants
        for point in test_points:
            ms1f = point.flow_m
            mbal = point.balance_line_flow_m
            mseal = point.seal_gas_flow_m
            if mbal == None:
                mbal = Q_(0, "kg/s")
            if mseal == None:
                mseal = Q_(0, "kg/s")

            mend = mbal - (0.95 * mseal) / 2
            ms1r = ms1f + mend

            Ts1f = point.suc.T()
            # dummy state to calculate Tend
            dummy_state = copy(point.disch)
            dummy_state.update(p=point.suc.p(), h=dummy_state.h())
            Tend = dummy_state.T()
            Tseal = point.seal_gas_temperature
            if Tseal == None:
                Tseal = Q_(0, "kelvin")
            Ts1r = (ms1f * Ts1f + mend * Tend + 0.95 * mseal * Tseal) / (
                ms1f + mend + 0.95 * mseal
            )
            point.Ts1r = Ts1r
            k_end = k_seal(flow_m=mend, state_up=point.disch, state_down=point.suc)
            self.k_end_seal.append(k_end)
            suc_rotor = State(p=point.suc.p(), T=point.Ts1r, fluid=point.suc.fluid)

            # calculate power losses
            if bearing_mechanical_losses:
                power_losses = (
                    point.oil_density_de
                    * point.oil_flow_journal_bearing_de
                    * point.oil_specific_heat_de
                    * (point.oil_outlet_temperature_de - point.oil_inlet_temperature)
                    + point.oil_density_nde
                    * point.oil_flow_journal_bearing_nde
                    * point.oil_specific_heat_nde
                    * (point.oil_outlet_temperature_nde - point.oil_inlet_temperature)
                    + point.oil_density_nde
                    * point.oil_flow_thrust_bearing_nde
                    * point.oil_specific_heat_nde
                    * (point.oil_outlet_temperature_nde - point.oil_inlet_temperature)
                )
            else:
                power_losses = 0

            test_points_rotor.append(
                Point(
                    suc=suc_rotor,
                    disch=point.disch,
                    flow_m=ms1r,
                    speed=point.speed,
                    b=point.b,
                    D=point.D,
                    power_losses=power_losses,
                    surface_roughness=point.surface_roughness,
                    casing_area=point.casing_area,
                    casing_temperature=point.casing_temperature,
                    ambient_temperature=point.ambient_temperature,
                    convection_constant=point.convection_constant,
                )
            )

        self.points_rotor_t = test_points_rotor

        # convert points_rotor_t to points_rotor_sp
        self.points_rotor_sp = []
        self.points_flange_sp = []
        # calculate ms1r for the guarantee point
        for point, k in zip(self.points_rotor_t, self.k_end_seal):
            error = 1
            # initial estimate of Ts1r_sp with Ts1f_sp
            Ts1r_sp = guarantee_point.suc.T()
            initial_suc = copy(guarantee_point.suc)
            i = 0
            while error > 1e-5 and i < 5:
                initial_suc.update(p=initial_suc.p(), T=Ts1r_sp)
                initial_point_rotor_sp = Point.convert_from(
                    original_point=point,
                    suc=initial_suc,
                    speed=self.speed_operational,
                    find="volume_ratio",
                    reynolds_correction=self.reynolds_correction,
                )
                ms1r_sp = initial_point_rotor_sp.flow_m
                mend_sp = flow_m_seal(
                    k,
                    state_up=initial_point_rotor_sp.disch,
                    state_down=initial_point_rotor_sp.suc,
                )
                ms1f_sp = ms1r_sp - mend_sp
                Ts1f_sp = guarantee_point.suc.T()
                # dummy state to calculate Tend
                dummy_state = copy(initial_point_rotor_sp.disch)
                dummy_state.update(p=initial_point_rotor_sp.suc.p(), h=dummy_state.h())
                Tend_sp = dummy_state.T()
                Ts1r_sp_new = (ms1f_sp * Ts1f_sp + mend_sp * Tend_sp) / (
                    ms1f_sp + mend_sp
                )
                i += 1
                error = abs(Ts1r_sp_new.m - Ts1r_sp.m)
                Ts1r_sp = Ts1r_sp_new
            self.points_rotor_sp.append(initial_point_rotor_sp)
            self.points_flange_sp.append(
                Point(
                    suc=guarantee_point.suc,
                    disch=initial_point_rotor_sp.disch,
                    flow_m=ms1f_sp,
                    speed=speed_operational,
                    b=guarantee_point.b,
                    D=guarantee_point.D,
                    power_losses=initial_point_rotor_sp.power_losses,
                    surface_roughness=guarantee_point.surface_roughness,
                    casing_area=guarantee_point.casing_area,
                    casing_temperature=guarantee_point.casing_temperature,
                    ambient_temperature=guarantee_point.ambient_temperature,
                    convection_constant=guarantee_point.convection_constant,
                )
            )

        super().__init__(self.points_flange_sp)

    def _dict_to_save(self):
        dict_to_save = {
            "reynolds_correction": self.reynolds_correction,
            "speed_operational": str(self.speed_operational),
        }
        # add points to file
        dict_to_save["guarantee_point"] = self.guarantee_point._dict_to_save()

        dict_to_save["test_points"] = {
            f"Point{i}": point._dict_to_save()
            for i, point in enumerate(self.test_points)
        }
        return dict_to_save

    def save(self, file):
        """Save compressor as .toml file.

        Parameters
        ----------
        file : str
            File name.
        """
        with open(file, mode="w") as f:
            toml.dump(self._dict_to_save(), f)

    @classmethod
    def load(cls, file):
        """Load compressor from .toml file.

        Parameters
        ----------
        file : str
            File name.
        """
        parameters = toml.load(file)
        kwargs = {"speed_operational": Q_(parameters.pop("speed_operational", None))}
        # guarantee_point, test_points, speed=None, reynolds_correction=False

        for k, v in parameters.items():
            if "guarantee_point" in k:
                kwargs[k] = Point(**Point._dict_from_load(v))
            elif "test_points" in k:
                kwargs[k] = [Point1Sec(**Point._dict_from_load(v)) for v in v.values()]
            else:
                kwargs[k] = v

        return cls(**kwargs)

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            if (
                self.reynolds_correction == other.reynolds_correction
                and self.speed_operational == other.speed_operational
                and self.guarantee_point == other.guarantee_point
            ):
                test_points_other = sorted(other.test_points, key=lambda x: x.flow_v)
                test_points_self = sorted(self.test_points, key=lambda x: x.flow_v)
                if len(test_points_self) == len(test_points_other):
                    if test_points_self == test_points_other:
                        return True

    def calculate_speed_to_match_discharge_pressure(self):
        """Calculate the speed to match the discharge pressure of the guarantee point."""

        def calculate_disch_pressure_delta(x):
            compressor = StraightThrough(
                guarantee_point=self.guarantee_point,
                test_points=self.test_points,
                speed_operational=x,
                reynolds_correction=self.reynolds_correction,
                bearing_mechanical_losses=self.bearing_mechanical_losses,
            )

            point = compressor.point(flow_m=self.guarantee_point.flow_m, speed=x)
            # add 1 pascal to guarantee that discharge pressure is higher
            return point.disch.p().m - (self.guarantee_point.disch.p().m + 1)

        new_speed = newton(calculate_disch_pressure_delta, self.speed_operational.m)
        return self.__class__(
            guarantee_point=self.guarantee_point,
            test_points=self.test_points,
            speed_operational=new_speed,
            reynolds_correction=self.reynolds_correction,
            bearing_mechanical_losses=self.bearing_mechanical_losses,
        )


class PointFirstSection(Point):
    """Point class for a compressor with 2 sections in a back-to-back configuration.

    Parameters
    ----------
    balance_line_flow_m : float, pint.Quantity
        Balance line mass flow (kg/s).
    seal_gas_flow_m : float, pint.Quantity
        Seal gas mass flow (kg/s).
    seal_gas_temperature : float, pint.Quantity
        Seal gas injection temperature (degK).
    first_section_discharge_flow_m : float, pint.Quantity
        First section discharge mass flow (kg/s).
    div_wall_flow_m : float, pint.Quantity
        Division wall mass flow (kg/s).
    end_seal_upstream_temperature : float, pint.Quantity
        Temperature upstream the end seal (degK).
    end_seal_upstream_pressure : float, pint.Quantity
        Pressure upstream the end seal (Pa).
    div_wall_upstream_temperature : float, pint.Quantity
        Temperature upstream the division wall (degK).
    div_wall_upstream_pressure : float, pint.Quantity
         Pressure upstream the division wall (Pa).
    oil_flow_journal_bearing_de : float, pint.Quantity
        Oil flow journal bearing drive end side (m³/s).
    oil_flow_journal_bearing_nde : float, pint.Quantity
        Oil flow journal bearing non-drive end side (m³/s).
    oil_flow_thrust_bearing_nde : float, pint.Quantity
         Oil flow journal bearing thrust bearing (m³/s).
    oil_inlet_temperature : float, pint.Quantity
        Oil inlet temperature (degK).
    oil_outlet_temperature_de : float, pint.Quantity
        Oil outlet temperature journal bearing drive end side (degK).
    oil_outlet_temperature_nde : float, pint.Quantity
        Oil outlet temperature bearing non-drive end side (degK).
    oil_specific_heat_de : float, pint.Quantity
        Oil specific heat bearing drive end side (J/kg/degK).
    oil_specific_heat_nde : float, pint.Quantity
        Oil specific heat bearing non-drive end side (J/kg/degK).
    oil_density_de : float, pint.Quantity
        Oil Density bearing drive end side (kg/m³).
    oil_density_nde : float, pint.Quantity
        Oil density bearing non-drive end side (kg/m³).

    Returns
    -------
    point1sec : ccp.Point2Sec
        A point for a back to back compressor (inherited from ccp.Point).

    Examples
    --------
    >>> import ccp
    >>> p = PointFirstSection(
    ...     flow_m=Q_(4.325, "kg/s"),
    ...     speed=Q_(9096, "RPM"),
    ...     b=Q_(10.5, "mm"),
    ...     D=Q_(365, "mm"),
    ...     suc=State(
    ...         p=Q_(5.182, "bar"),
    ...         T=Q_(299.5, "degK"),
    ...         fluid={
    ...             "carbon dioxide": 1,
    ...         },
    ...     ),
    ...     disch=State(
    ...         p=Q_(14.95, "bar"),
    ...         T=Q_(397.6, "degK"),
    ...         fluid={
    ...             "carbon dioxide": 1,
    ...         },
    ...     ),
    ...     balance_line_flow_m=Q_(0.1625, "kg/s"),
    ...     seal_gas_flow_m=Q_(0.0616, "kg/s"),
    ...     seal_gas_temperature=299.7,
    ...     first_section_discharge_flow_m=4.8059,
    ...     div_wall_flow_m=None,
    ...     end_seal_upstream_temperature=304.3,
    ...     end_seal_upstream_pressure=14.59,
    ...     div_wall_upstream_temperature=362.5,
    ...     div_wall_upstream_pressure=26.15,
    ...     oil_flow_journal_bearing_de=Q_(31.515, "l/min"),
    ...     oil_flow_journal_bearing_nde=Q_(22.67, "l/min"),
    ...     oil_flow_thrust_bearing_nde=Q_(126.729, "l/min"),
    ...     oil_inlet_temperature=Q_(41.544, "degC"),
    ...     oil_outlet_temperature_de=Q_(49.727, "degC"),
    ...     oil_outlet_temperature_nde=Q_(50.621, "degC"),
    ...     oil_specific_heat_de=Q_(2.02, "kJ/kg/degK"),
    ...     oil_specific_heat_nde=Q_(2.02, "kJ/kg/degK"),
    ...     oil_density_de=Q_(846.9, "kg/m³"),
    ...     oil_density_nde=Q_(846.9, "kg/m³"),
    ...     casing_area=5.5,
    ...     casing_temperature=Q_(23.895, "degC"),
    ...     ambient_temperature=Q_(0, "degC"),
    ... )
    """

    @check_units
    def __init__(
        self,
        *args,
        balance_line_flow_m=None,
        seal_gas_flow_m=None,
        seal_gas_temperature=None,
        first_section_discharge_flow_m=None,
        div_wall_flow_m=None,
        end_seal_upstream_temperature=None,
        end_seal_upstream_pressure=None,
        div_wall_upstream_temperature=None,
        div_wall_upstream_pressure=None,
        oil_flow_journal_bearing_de=None,
        oil_flow_journal_bearing_nde=None,
        oil_flow_thrust_bearing_nde=None,
        oil_inlet_temperature=None,
        oil_outlet_temperature_de=None,
        oil_outlet_temperature_nde=None,
        oil_specific_heat_de=None,
        oil_specific_heat_nde=None,
        oil_density_de=None,
        oil_density_nde=None,
        leakages=True,
        bearing_mechanical_losses=True,
        **kwargs,
    ):
        super().__init__(
            *args,
            **kwargs,
        )
        self._args = args
        self._kwargs = kwargs
        self.seal_gas_flow_m = seal_gas_flow_m
        self.seal_gas_temperature = seal_gas_temperature

        # keep the following original values used in instantiation
        self._balance_line_flow_m = balance_line_flow_m
        self._div_wall_flow_m = div_wall_flow_m
        self._first_section_discharge_flow_m = first_section_discharge_flow_m

        self.balance_line_flow_m = balance_line_flow_m
        self.first_section_discharge_flow_m = first_section_discharge_flow_m
        self.div_wall_flow_m = div_wall_flow_m
        self.end_seal_upstream_temperature = end_seal_upstream_temperature
        self.end_seal_upstream_pressure = end_seal_upstream_pressure
        self.div_wall_upstream_temperature = div_wall_upstream_temperature
        self.div_wall_upstream_pressure = div_wall_upstream_pressure
        self.oil_flow_journal_bearing_de = oil_flow_journal_bearing_de
        self.oil_flow_journal_bearing_nde = oil_flow_journal_bearing_nde
        self.oil_flow_thrust_bearing_nde = oil_flow_thrust_bearing_nde
        self.oil_inlet_temperature = oil_inlet_temperature
        self.oil_outlet_temperature_de = oil_outlet_temperature_de
        self.oil_outlet_temperature_nde = oil_outlet_temperature_nde
        self.oil_specific_heat_de = oil_specific_heat_de
        self.oil_specific_heat_nde = oil_specific_heat_nde
        self.oil_density_de = oil_density_de
        self.oil_density_nde = oil_density_nde
        self.leakages = leakages
        self.bearing_mechanical_losses = bearing_mechanical_losses

        # check case for no leakage. If no leakage, div_wall_flow_m and first_section_discharge_flow_m are zero
        # and we equate the seal/div wall states to avoid errors
        if not self.leakages:
            self.div_wall_flow_m = Q_(0, "kg/s")
            self.balance_line_flow_m = Q_(0, "kg/s")
            self.seal_gas_flow_m = Q_(0, "kg/s")
            self.seal_gas_temperature = self.suc.T()
            self.end_seal_upstream_temperature = self.suc.T()
            self.end_seal_upstream_pressure = self.suc.p()
            self.div_wall_upstream_temperature = self.disch.T()
            self.div_wall_upstream_pressure = self.disch.p()

        if not self.bearing_mechanical_losses:
            self.oil_flow_journal_bearing_de = Q_(0, "m³/s")
            self.oil_flow_journal_bearing_nde = Q_(0, "m³/s")
            self.oil_flow_thrust_bearing_nde = Q_(0, "m³/s")
            self.oil_inlet_temperature = self.suc.T()
            self.oil_outlet_temperature_de = self.suc.T()
            self.oil_outlet_temperature_nde = self.suc.T()
            oil_specific_heat_de = (Q_(2.02, "kJ/kg/degK"),)
            oil_specific_heat_nde = (Q_(2.02, "kJ/kg/degK"),)
            oil_density_de = (Q_(846.9, "kg/m³"),)
            oil_density_nde = (Q_(846.9, "kg/m³"),)

        self.end_seal_upstream_state = State(
            p=self.end_seal_upstream_pressure,
            T=self.end_seal_upstream_temperature,
            fluid=self.suc.fluid,
        )
        self.end_seal_downstream_state = copy(self.suc)
        self.end_seal_downstream_state.update(
            p=self.end_seal_downstream_state.p(), h=self.end_seal_upstream_state.h()
        )

        self.div_wall_upstream_state = State(
            p=self.div_wall_upstream_pressure,
            T=self.div_wall_upstream_temperature,
            fluid=self.suc.fluid,
        )
        self.div_wall_downstream_state = copy(self.disch)
        self.div_wall_downstream_state.update(
            p=self.div_wall_downstream_state.p(), h=self.div_wall_upstream_state.h()
        )

    def _dict_to_save(self):
        """Returns a dict that will be saved to a toml file."""
        dict_to_save = super()._dict_to_save()
        parameters = [
            "balance_line_flow_m",
            "first_section_discharge_flow_m",
            "div_wall_flow_m",
        ]
        for parameter in parameters:
            if getattr(self, "_" + parameter) is not None:
                dict_to_save[parameter] = str(getattr(self, "_" + parameter))

        parameters = [
            "seal_gas_flow_m",
            "seal_gas_temperature",
            "end_seal_upstream_temperature",
            "end_seal_upstream_pressure",
            "div_wall_upstream_temperature",
            "div_wall_upstream_pressure",
            "oil_flow_journal_bearing_de",
            "oil_flow_journal_bearing_nde",
            "oil_flow_thrust_bearing_nde",
            "oil_inlet_temperature",
            "oil_outlet_temperature_de",
            "oil_outlet_temperature_nde",
            "oil_specific_heat_de",
            "oil_specific_heat_nde",
            "oil_density_de",
            "oil_density_nde",
        ]
        for parameter in parameters:
            if getattr(self, parameter) is not None:
                dict_to_save[parameter] = str(getattr(self, parameter))

        return dict_to_save


class PointSecondSection(Point1Sec):
    """Point for second section"""

    pass


class BackToBack(Impeller):
    """Back to Back compressor"""

    @check_units
    def __init__(
        self,
        guarantee_point_sec1,
        test_points_sec1,
        guarantee_point_sec2,
        test_points_sec2,
        reynolds_correction=False,
        bearing_mechanical_losses=False,
        speed_operational=None,
    ):
        self.guarantee_point_sec1 = guarantee_point_sec1
        self.guarantee_point_sec2 = guarantee_point_sec2
        self.test_points_sec1 = test_points_sec1
        self.test_points_sec2 = test_points_sec2
        if speed_operational is None:
            speed_operational = guarantee_point_sec1.speed
        self.speed_operational = speed_operational
        self.reynolds_correction = reynolds_correction
        self.bearing_mechanical_losses = bearing_mechanical_losses

        # points for test flange conditions
        self.points_flange_t_sec1 = test_points_sec1
        self.points_flange_t_sec2 = test_points_sec2

        # calculate rotor condition for sec1
        test_points_sec1_rotor = np.full(len(test_points_sec1), np.nan, dtype=object)
        self.k_end_seal = np.zeros(
            len(test_points_sec1), dtype=object
        )  # array with seal constants
        self.k_div_wall = np.zeros(
            len(test_points_sec1), dtype=object
        )  # array with div wall seal constants

        for point in test_points_sec1:
            if point.div_wall_flow_m:
                point.first_section_discharge_flow_m = (
                    point.flow_m
                    + point.div_wall_flow_m
                    + point.balance_line_flow_m
                    + 0.95 * point.seal_gas_flow_m / 2
                )
        for i, point in enumerate(test_points_sec1):
            # calculate power losses
            if bearing_mechanical_losses:
                power_losses = (
                    point.oil_density_de
                    * point.oil_flow_journal_bearing_de
                    * point.oil_specific_heat_de
                    * (point.oil_outlet_temperature_de - point.oil_inlet_temperature)
                    + point.oil_density_nde
                    * point.oil_flow_journal_bearing_nde
                    * point.oil_specific_heat_nde
                    * (point.oil_outlet_temperature_nde - point.oil_inlet_temperature)
                    + point.oil_density_nde
                    * point.oil_flow_thrust_bearing_nde
                    * point.oil_specific_heat_nde
                    * (point.oil_outlet_temperature_nde - point.oil_inlet_temperature)
                )
            else:
                power_losses = 0
            # Here we check for _first_section_discharge_flow_m because we want to use the
            # value given in the test point, not the calculated value.
            # This way we can guarantee that everytime we create the compressor, the same
            # values are used, and we also get the same results.
            if point._first_section_discharge_flow_m:
                md1f_t = point._first_section_discharge_flow_m
                ms1f_t = point.flow_m
                mbal_t = point._balance_line_flow_m
                mseal_t = point.seal_gas_flow_m
                mend_t = mbal_t - (0.95 * mseal_t) / 2
                point.end_seal_flow_m = mend_t
                mdiv_t = md1f_t - ms1f_t - mend_t - 0.95 * mseal_t
                point.div_wall_flow_m = mdiv_t
                ms1r_t = ms1f_t + mend_t + 0.95 * mseal_t

                ps1f_t = point.suc.p()
                Ts1f_t = point.suc.T()

                pd1f_t = point.disch.p()
                Td1f_t = point.disch.T()
                pd2f_t = point.div_wall_upstream_pressure
                Td2f_t = point.div_wall_upstream_temperature
                Tseal_t = point.seal_gas_temperature

                Tend_t = point.end_seal_downstream_state.T()

                k_end = k_seal(
                    flow_m=mend_t,
                    state_up=point.end_seal_upstream_state,
                    state_down=point.end_seal_downstream_state,
                )
                self.k_end_seal[i] = k_end

                k_div_wall = k_seal(
                    flow_m=mdiv_t,
                    state_up=point.div_wall_upstream_state,
                    state_down=point.div_wall_downstream_state,
                )
                self.k_div_wall[i] = k_div_wall
                Tdiv_t = point.div_wall_downstream_state.T()
                Ts1r_t = (
                    ms1f_t * Ts1f_t + mend_t * Tend_t + 0.95 * mseal_t * Tseal_t
                ) / (ms1f_t + mend_t + 0.95 * mseal_t)
                Td1r_t = (md1f_t * Td1f_t - mdiv_t * Tdiv_t) / (md1f_t - mdiv_t)
                suc_sec1_rotor_t = State(p=ps1f_t, T=Ts1r_t, fluid=point.suc.fluid)
                disch_sec1_rotor_t = State(p=pd1f_t, T=Td1r_t, fluid=point.suc.fluid)

                test_points_sec1_rotor[i] = Point(
                    suc=suc_sec1_rotor_t,
                    disch=disch_sec1_rotor_t,
                    flow_m=ms1r_t,
                    speed=point.speed,
                    b=point.b,
                    D=point.D,
                    power_losses=power_losses,
                    casing_area=point.casing_area,
                    casing_temperature=point.casing_temperature,
                    ambient_temperature=point.ambient_temperature,
                    surface_roughness=point.surface_roughness,
                    convection_constant=point.convection_constant,
                )

            # use calculated k_end_seal and k_div_wall to calculate seal mass flow
            # use manual mean, since np.mean removes the units
            if (self.k_end_seal == 0).all():
                k_end_seal_mean = Q_(
                    0, "kelvin**0.5 kilogram**0.5 mole**0.5/(pascal second)"
                )
            else:
                k_end_seal_mean = sum(self.k_end_seal[self.k_end_seal != 0]) / len(
                    self.k_end_seal[self.k_end_seal != 0]
                )
            if (self.k_div_wall == 0).all():
                k_div_wall_mean = Q_(
                    0, "kelvin**0.5 kilogram**0.5 mole**0.5/(pascal second)"
                )
            else:
                k_div_wall_mean = sum(self.k_div_wall[self.k_div_wall != 0]) / len(
                    self.k_div_wall[self.k_div_wall != 0]
                )

        for i, point in enumerate(test_points_sec1):
            # calculate power losses
            if bearing_mechanical_losses:
                power_losses = (
                    point.oil_density_de
                    * point.oil_flow_journal_bearing_de
                    * point.oil_specific_heat_de
                    * (point.oil_outlet_temperature_de - point.oil_inlet_temperature)
                    + point.oil_density_nde
                    * point.oil_flow_journal_bearing_nde
                    * point.oil_specific_heat_nde
                    * (point.oil_outlet_temperature_nde - point.oil_inlet_temperature)
                    + point.oil_density_nde
                    * point.oil_flow_thrust_bearing_nde
                    * point.oil_specific_heat_nde
                    * (point.oil_outlet_temperature_nde - point.oil_inlet_temperature)
                )
            else:
                power_losses = 0
            if not point._first_section_discharge_flow_m:
                self.k_end_seal[i] = k_end_seal_mean
                end_seal_flow_m = flow_m_seal(
                    k_seal=k_end_seal_mean,
                    state_up=point.end_seal_upstream_state,
                    state_down=point.end_seal_downstream_state,
                )

                self.k_div_wall[i] = k_div_wall_mean
                div_wall_flow_m = flow_m_seal(
                    k_seal=k_div_wall_mean,
                    state_up=point.div_wall_upstream_state,
                    state_down=point.div_wall_downstream_state,
                )

                # calculate balance line and rotor suction flow
                if point.seal_gas_flow_m == None:  ##################
                    point.seal_gas_flow_m = 0
                mseal_t = point.seal_gas_flow_m
                mend_t = end_seal_flow_m
                point.end_seal_flow_m = mend_t

                mbal_t = mend_t + (0.95 * mseal_t) / 2
                point.balance_line_flow_m = mbal_t

                ms1f_t = point.flow_m
                ms1r_t = ms1f_t + mend_t + 0.95 * mseal_t

                # calculate discharge flow
                mdiv_t = div_wall_flow_m
                point.div_wall_flow_m = mdiv_t
                md1f_t = mdiv_t + ms1f_t + mend_t + 0.95 * mseal_t
                point.first_section_discharge_flow_m = md1f_t

                Ts1f_t = point.suc.T()
                Tend_t = point.end_seal_downstream_state.T()
                Tdiv_t = point.div_wall_downstream_state.T()
                Tseal_t = point.seal_gas_temperature
                Td1f_t = point.disch.T()
                ps1f_t = point.suc.p()
                pd1f_t = point.disch.p()

                Ts1r_t = (
                    ms1f_t * Ts1f_t + mend_t * Tend_t + 0.95 * mseal_t * Tseal_t
                ) / (ms1f_t + mend_t + 0.95 * mseal_t)
                Td1r_t = (md1f_t * Td1f_t - mdiv_t * Tdiv_t) / (md1f_t - mdiv_t)

                suc_sec1_rotor_t = State(p=ps1f_t, T=Ts1r_t, fluid=point.suc.fluid)
                disch_sec1_rotor_t = State(p=pd1f_t, T=Td1r_t, fluid=point.suc.fluid)

                test_points_sec1_rotor[i] = Point(
                    suc=suc_sec1_rotor_t,
                    disch=disch_sec1_rotor_t,
                    flow_m=ms1r_t,
                    speed=point.speed,
                    b=point.b,
                    D=point.D,
                    power_losses=power_losses,
                    casing_area=point.casing_area,
                    casing_temperature=point.casing_temperature,
                    ambient_temperature=point.ambient_temperature,
                    surface_roughness=point.surface_roughness,
                    convection_constant=point.convection_constant,
                )

        self.k_end_seal_mean = k_end_seal_mean
        self.k_div_wall_mean = k_div_wall_mean
        self.points_rotor_t_sec1 = test_points_sec1_rotor

        # calculate rotor condition for sec2
        test_points_sec2_rotor = np.full(len(test_points_sec1), np.nan, dtype=object)
        for i, point_f in enumerate(test_points_sec2):
            # calculate power losses
            if bearing_mechanical_losses:
                power_losses = (
                    point.oil_density_de
                    * point.oil_flow_journal_bearing_de
                    * point.oil_specific_heat_de
                    * (point.oil_outlet_temperature_de - point.oil_inlet_temperature)
                    + point.oil_density_nde
                    * point.oil_flow_journal_bearing_nde
                    * point.oil_specific_heat_nde
                    * (point.oil_outlet_temperature_nde - point.oil_inlet_temperature)
                    + point.oil_density_nde
                    * point.oil_flow_thrust_bearing_nde
                    * point.oil_specific_heat_nde
                    * (point.oil_outlet_temperature_nde - point.oil_inlet_temperature)
                )
            else:
                power_losses = 0

            ms2f_t = point_f.flow_m
            mbal_t = point_f.balance_line_flow_m
            if point_f.seal_gas_flow_m == None:  ##################
                point_f.seal_gas_flow_m = 0
            mseal_t = point_f.seal_gas_flow_m
            mend_t = mbal_t - 0.95 * mseal_t / 2
            ms2r_t = ms2f_t - mend_t
            point_r = Point(
                suc=point_f.suc,
                disch=point_f.disch,
                flow_m=ms2r_t,
                speed=point_f.speed,
                b=point_f.b,
                D=point_f.D,
                power_losses=power_losses,
                casing_area=point_f.casing_area,
                casing_temperature=point_f.casing_temperature,
                ambient_temperature=point_f.ambient_temperature,
                surface_roughness=point_f.surface_roughness,
                convection_constant=point_f.convection_constant,
            )
            test_points_sec2_rotor[i] = point_r

        self.points_rotor_t_sec2 = test_points_sec2_rotor

        # convert sec2 points_rotor_sp to points_flange_sp
        self.points_rotor_sp_sec2 = []
        self.points_flange_sp_sec2 = []

        # calculate rotor specified conditions for sec1
        self.points_rotor_sp_sec1 = []
        ms1f_sp_array = np.zeros(len(self.points_rotor_t_sec1), dtype=object)
        for i, point, k_end_seal, k_div_wall in zip(
            range(len(ms1f_sp_array)),
            self.points_rotor_t_sec1,
            self.k_end_seal,
            self.k_div_wall,
        ):
            initial_point = Point.convert_from(
                original_point=point,
                suc=guarantee_point_sec1.suc,
                speed=self.speed_operational,
                find="volume_ratio",
                reynolds_correction=self.reynolds_correction,
            )
            # determine rotor specified suction state
            end_seal_state_upstream_sp = State(
                p=initial_point.disch.p(),
                T=guarantee_point_sec2.suc.T(),
                fluid=initial_point.suc.fluid,
            )
            end_seal_state_downstream_sp = copy(initial_point.disch)
            end_seal_state_downstream_sp.update(
                p=guarantee_point_sec1.suc.p(), h=end_seal_state_upstream_sp.h()
            )
            Tend_sp = end_seal_state_downstream_sp.T()

            mend_sp = flow_m_seal(
                k_seal=k_end_seal,
                state_up=end_seal_state_upstream_sp,
                state_down=end_seal_state_downstream_sp,
            )

            Ts1f_sp = guarantee_point_sec1.suc.T()
            qs1r_sp = flow_from_phi(
                D=point.D, phi=point.phi, speed=self.speed_operational
            )
            ps1r_sp = guarantee_point_sec1.suc.p()
            vs1f_sp = guarantee_point_sec1.suc.v()
            dummy_suc = copy(guarantee_point_sec1.suc)

            error = 1
            dm = Q_(1, "kg/s")
            ms1f_sp = qs1r_sp / vs1f_sp  # initial guess
            while error > 0.00001:
                ms1r_sp = ms1f_sp + mend_sp
                Ts1r_sp = (mend_sp * Tend_sp + ms1f_sp * Ts1f_sp) / ms1r_sp
                dummy_suc.update(p=ps1r_sp, T=Ts1r_sp)
                vs1r_sp = dummy_suc.v()
                qs1r_sp_1 = ms1r_sp * vs1r_sp

                fx = -qs1r_sp + qs1r_sp_1
                ms1f_sp_new = ms1f_sp + dm
                ms1r_sp_new = ms1f_sp_new + mend_sp
                Ts1r_sp_new = (ms1f_sp_new * Ts1f_sp + mend_sp * Tend_sp) / ms1r_sp_new
                dummy_suc.update(p=ps1r_sp, T=Ts1r_sp_new)
                vs1r_sp_new = dummy_suc.v()
                qs1r_sp_1_new = ms1r_sp_new * vs1r_sp_new
                dfx = (qs1r_sp_1_new - qs1r_sp_1) / dm
                ms1f_sp = ms1f_sp - (fx / dfx)
                error = ((fx**2) ** 0.5).m

            ms1f_sp_array[i] = ms1f_sp

            rotor_sp_sec1_suc = ccp.State(
                p=guarantee_point_sec1.suc.p(),
                T=Ts1r_sp,
                fluid=guarantee_point_sec1.suc.fluid,
            )
            point_r_sp = Point.convert_from(
                original_point=point,
                suc=rotor_sp_sec1_suc,
                speed=self.speed_operational,
                find="volume_ratio",
                reynolds_correction=self.reynolds_correction,
            )
            self.points_rotor_sp_sec1.append(point_r_sp)
        self.imp_rotor_sp_sec1 = Impeller(self.points_rotor_sp_sec1)

        # estimate rotor guarantee flow using datasheet conditions
        end_seal_flow_m_sp = flow_m_seal(
            k_seal=k_end_seal,
            state_up=guarantee_point_sec2.suc,
            state_down=guarantee_point_sec1.suc,
        )
        # calculate suction pressure for sec2
        ms1r_sp = guarantee_point_sec1.flow_m + end_seal_flow_m_sp

        disch_r_sp = self.imp_rotor_sp_sec1.point(
            flow_m=ms1r_sp, speed=self.speed_operational
        ).disch
        ps2f_sp = disch_r_sp.p() - (
            guarantee_point_sec1.disch.p() - guarantee_point_sec2.suc.p()
        )
        suc2f_sp = State(
            p=ps2f_sp,
            T=guarantee_point_sec2.suc.T(),
            fluid=guarantee_point_sec2.suc.fluid,
        )
        for point_r_t in self.points_rotor_t_sec2:
            point_r_sp = Point.convert_from(
                original_point=point_r_t,
                suc=suc2f_sp,
                speed=self.speed_operational,
                find="volume_ratio",
                reynolds_correction=self.reynolds_correction,
            )
            self.points_rotor_sp_sec2.append(point_r_sp)
            mend_sp = flow_m_seal(
                k_seal=k_end_seal,
                state_up=guarantee_point_sec2.suc,
                state_down=guarantee_point_sec1.suc,
            )
            ms2r_sp = point_r_sp.flow_m
            ms2f_sp = ms2r_sp + mend_sp
            point_sp = Point(
                suc=point_r_sp.suc,
                disch=point_r_sp.disch,
                flow_m=ms2f_sp,
                speed=point_r_sp.speed,
                power_losses=point_r_sp.power_losses,
                b=point_r_sp.b,
                D=point_r_sp.D,
            )
            self.points_flange_sp_sec2.append(point_sp)
        # change points_flange power to real power calculated in rotor point
        for p_flange, p_rotor in zip(
            self.points_flange_sp_sec2, self.points_rotor_sp_sec2
        ):
            p_flange.power = p_rotor.power

        self.imp_flange_sp_sec2 = Impeller(self.points_flange_sp_sec2)

        # convert sec1 points_rotor_t to points_rotor_sp
        self.points_flange_sp_sec1 = []
        for point_r_sp, ms1f_sp, k_end_seal, k_div_wall in zip(
            self.points_rotor_sp_sec1, ms1f_sp_array, self.k_end_seal, self.k_div_wall
        ):
            # calculate div wall flow
            suc_sec2 = ccp.State(
                p=point_r_sp.disch.p(),
                T=guarantee_point_sec2.suc.T(),
                fluid=guarantee_point_sec2.suc.fluid,
            )
            imp_sec2_conv = self.imp_flange_sp_sec2
            imp_sec2_flow_m = point_r_sp.flow_m
            if imp_sec2_flow_m > imp_sec2_conv.flow_m.max():
                imp_sec2_flow_m = imp_sec2_conv.flow_m.max()
            sec2_point = imp_sec2_conv.point(
                flow_m=imp_sec2_flow_m, speed=self.speed_operational
            )
            sec2_disch = ccp.point.disch_from_suc_head_eff(
                suc=suc_sec2, head=sec2_point.head, eff=sec2_point.eff
            )
            mdiv_sp = flow_m_seal(
                k_seal=k_div_wall,
                state_up=sec2_disch,
                state_down=point_r_sp.disch,
            )
            div_wall_downstream_state = copy(sec2_disch)
            div_wall_downstream_state.update(
                p=point_r_sp.disch.p(), h=div_wall_downstream_state.h()
            )
            Tdiv_sp = div_wall_downstream_state.T()

            # calculate flange disch
            Td1r_sp = point_r_sp.disch.T()
            Td1f_sp = (ms1r_sp * Td1r_sp + mdiv_sp * Tdiv_sp) / (ms1r_sp + mdiv_sp)
            disch_f = ccp.State(
                p=point_r_sp.disch.p(), T=Td1f_sp, fluid=guarantee_point_sec1.suc.fluid
            )
            point_flange = Point(
                suc=guarantee_point_sec1.suc,
                disch=disch_f,
                flow_m=ms1f_sp,
                speed=self.speed_operational,
                b=guarantee_point_sec1.b,
                D=guarantee_point_sec1.D,
            )
            self.points_flange_sp_sec1.append(point_flange)
            self.points_flange_sp_sec1[-1].div_wall_flow_m = mdiv_sp
            self.points_flange_sp_sec1[-1].first_section_discharge_flow_m = (
                mdiv_sp + ms1r_sp
            )
            # change points_flange power to real power calculated in rotor point
            for p_flange, p_rotor in zip(
                self.points_flange_sp_sec1, self.points_rotor_sp_sec1
            ):
                p_flange.power = p_rotor.power
                p_flange.power_losses = p_rotor.power_losses
        self.imp_flange_sp_sec1 = Impeller(self.points_flange_sp_sec1)

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            if (
                self.reynolds_correction == other.reynolds_correction
                and self.speed_operational == other.speed_operational
                and self.guarantee_point_sec1 == other.guarantee_point_sec1
                and self.guarantee_point_sec2 == other.guarantee_point_sec2
            ):
                test_points_sec1_other = sorted(
                    other.test_points_sec1, key=lambda x: x.flow_v
                )
                test_points_sec1_self = sorted(
                    self.test_points_sec1, key=lambda x: x.flow_v
                )
                test_points_sec2_other = sorted(
                    other.test_points_sec2, key=lambda x: x.flow_v
                )
                test_points_sec2_self = sorted(
                    self.test_points_sec2, key=lambda x: x.flow_v
                )
                if len(test_points_sec1_self) == len(test_points_sec1_other) and len(
                    test_points_sec2_self
                ) == len(test_points_sec2_other):
                    if (
                        test_points_sec1_self == test_points_sec1_other
                        and test_points_sec2_self == test_points_sec2_other
                    ):
                        return True

    def _dict_to_save(self):
        dict_to_save = {
            "reynolds_correction": self.reynolds_correction,
            "speed_operational": str(self.speed_operational),
        }
        # add points to file
        dict_to_save["guarantee_point_sec1"] = self.guarantee_point_sec1._dict_to_save()
        dict_to_save["guarantee_point_sec2"] = self.guarantee_point_sec2._dict_to_save()
        dict_to_save["test_points_sec1"] = {
            f"Point{i}": point._dict_to_save()
            for i, point in enumerate(self.test_points_sec1)
        }
        dict_to_save["test_points_sec2"] = {
            f"Point{i}": point._dict_to_save()
            for i, point in enumerate(self.test_points_sec2)
        }
        return dict_to_save

    def save(self, file):
        """Save compressor as .toml file.

        Parameters
        ----------
        file : str
            File name.
        """
        with open(file, mode="w") as f:
            toml.dump(self._dict_to_save(), f)

    @classmethod
    def load(cls, file):
        """Load compressor from .toml file.

        Parameters
        ----------
        file : str
            File name.
        """
        parameters = toml.load(file)
        kwargs = {"speed_operational": Q_(parameters.pop("speed_operational", None))}

        for k, v in parameters.items():
            if "guarantee_point" in k:
                kwargs[k] = Point(**Point._dict_from_load(v))
            elif "test_points_sec1" in k:
                kwargs[k] = [
                    PointFirstSection(**Point._dict_from_load(v)) for v in v.values()
                ]
            elif "test_points_sec2" in k:
                kwargs[k] = [
                    PointSecondSection(**Point._dict_from_load(v)) for v in v.values()
                ]
            else:
                kwargs[k] = v

        return cls(**kwargs)

    def point_sec1(self, *args, **kwargs):
        # calculate flange point from impeller object
        p_sec1 = self.imp_flange_sp_sec1.point(*args, **kwargs)

        # calculate rotor flow
        ps2f_sp = p_sec1.disch.p() - (
            self.guarantee_point_sec1.disch.p() - self.guarantee_point_sec2.suc.p()
        )
        suc2f_sp = State(
            p=ps2f_sp,
            T=self.guarantee_point_sec2.suc.T(),
            fluid=self.guarantee_point_sec2.suc.fluid,
        )
        end_seal_flow_m_sp = flow_m_seal(
            k_seal=self.k_end_seal_mean,
            state_up=suc2f_sp,
            state_down=p_sec1.suc,
        )
        ms1r_sp = p_sec1.flow_m + end_seal_flow_m_sp

        # calculate 'real' power from rotor conditions
        p_sec1_rotor = self.imp_rotor_sp_sec1.point(flow_m=ms1r_sp, speed=p_sec1.speed)
        p_sec1.power = p_sec1_rotor.power
        p_sec1.power_losses = p_sec1_rotor.power_losses
        p_sec1.power_shaft = p_sec1_rotor.power_shaft

        # set mach number and mach_diff
        mach_interpolation = parameter_interpolation(
            p_sec1.phi,
            [p.phi for p in self.points_flange_t_sec1],
            [p.mach for p in self.points_flange_t_sec1],
        )
        p_sec1.mach = mach_interpolation
        p_sec1.mach_diff = mach_interpolation - self.guarantee_point_sec1.mach

        # set reynolds number and reynolds_ratio
        reynolds_interpolation = parameter_interpolation(
            p_sec1.phi,
            [p.phi for p in self.points_flange_t_sec1],
            [p.reynolds for p in self.points_flange_t_sec1],
        )
        p_sec1.reynolds = reynolds_interpolation
        p_sec1.reynolds_ratio = (
            reynolds_interpolation / self.guarantee_point_sec1.reynolds
        )

        # set new volume ratio ratio
        p_sec1.volume_ratio_ratio = (
            p_sec1.volume_ratio / self.guarantee_point_sec1.volume_ratio
        )

        return p_sec1

    def point_sec2(self, *args, **kwargs):
        # calculate flange point from impeller object
        p_sec2 = self.imp_flange_sp_sec2.point(*args, **kwargs)

        # calculate 'real' power from rotor conditions
        end_seal_flow_m_sp = flow_m_seal(
            k_seal=self.k_end_seal_mean,
            state_up=p_sec2.suc,
            state_down=self.guarantee_point_sec1.suc,
        )
        ms2r_sp = p_sec2.flow_m - end_seal_flow_m_sp
        p_sec2.power = ms2r_sp * p_sec2.head / p_sec2.eff
        p_sec2.power_shaft = p_sec2.power + p_sec2.power_losses

        # set mach number and mach_diff
        mach_interpolation = parameter_interpolation(
            p_sec2.phi,
            [p.phi for p in self.points_flange_t_sec2],
            [p.mach for p in self.points_flange_t_sec2],
        )
        p_sec2.mach = mach_interpolation
        p_sec2.mach_diff = mach_interpolation - self.guarantee_point_sec2.mach

        # set reynolds number and reynolds_ratio
        reynolds_interpolation = parameter_interpolation(
            p_sec2.phi,
            [p.phi for p in self.points_flange_t_sec2],
            [p.reynolds for p in self.points_flange_t_sec2],
        )
        p_sec2.reynolds = reynolds_interpolation
        p_sec2.reynolds_ratio = (
            reynolds_interpolation / self.guarantee_point_sec2.reynolds
        )
        # set new volume ratio ratio
        p_sec2.volume_ratio_ratio = (
            p_sec2.volume_ratio / self.guarantee_point_sec2.volume_ratio
        )

        return p_sec2

    def calculate_speed_to_match_discharge_pressure(self):
        """Calculate the speed to match the discharge pressure of the guarantee point."""

        def calculate_disch_pressure_delta(x):
            compressor = BackToBack(
                guarantee_point_sec1=self.guarantee_point_sec1,
                guarantee_point_sec2=self.guarantee_point_sec2,
                test_points_sec1=self.test_points_sec1,
                test_points_sec2=self.test_points_sec2,
                speed_operational=x,
                reynolds_correction=self.reynolds_correction,
                bearing_mechanical_losses=self.bearing_mechanical_losses,
            )

            point = compressor.point_sec2(
                flow_m=self.guarantee_point_sec2.flow_m, speed=x
            )
            # add 1 pascal to guarantee that discharge pressure is higher
            delta_p = point.disch.p().m - (self.guarantee_point_sec2.disch.p().m + 1)
            return delta_p

        new_speed = newton(calculate_disch_pressure_delta, self.speed_operational.m)

        return self.__class__(
            guarantee_point_sec1=self.guarantee_point_sec1,
            guarantee_point_sec2=self.guarantee_point_sec2,
            test_points_sec1=self.test_points_sec1,
            test_points_sec2=self.test_points_sec2,
            speed_operational=new_speed,
            reynolds_correction=self.reynolds_correction,
            bearing_mechanical_losses=self.bearing_mechanical_losses,
        )


@check_units
def k_seal(flow_m, state_up, state_down):
    """Function to calculate the seal constant k.

    This seal constant is used to estimate the seal leakage in different conditions.

    Parameters
    ----------
    flow_m : float, pint.Quantity
        Mass flow through the seal (kg/s).
    state_up : ccp.State
        State upstream of the seal.
    state_down : ccp.State
        State downstream of the seal.

    Returns
    -------
    k_end_seal : pint.Quantity
        Seal constant (kelvin ** 0.5 * kilogram ** 0.5 * mole ** 0.5 / pascal / second).
    """
    p_up = state_up.p()
    z_up = state_up.z()
    T_up = state_up.T().to("K")
    MW = state_up.molar_mass()
    p_down = state_down.p()

    k = (flow_m * np.sqrt(z_up * T_up / MW)) / (
        p_up * np.sqrt(1 - (p_down / p_up) ** 2)
    )

    return k


@check_units
def flow_m_seal(k_seal, state_up, state_down):
    """Function to calculate the mass flow across a seal with constant k_seal.

    Parameters
    ----------
    k_seal : pint.Quantity
        Seal constant (kelvin ** 0.5 * kilogram ** 0.5 * mole ** 0.5 / pascal / second).
    state_up : ccp.State
        State upstream of the seal.
    state_down : ccp.State
        State downstream of the seal.

    Returns
    -------
    flow_m_seal : pint.Quantity
        Seal mass flow (kg/s).
    """
    p_up = state_up.p()
    z_up = state_up.z()
    T_up = state_up.T().to("K")
    MW = state_up.molar_mass()
    p_down = state_down.p()

    flow_m_seal = (
        k_seal
        * p_up
        * (np.sqrt(1 - (p_down / p_up) ** 2))
        / (np.sqrt(z_up * T_up / MW))
    )

    return flow_m_seal


def parameter_interpolation(phi, phi_values, parameter_values):
    """Function used to make a linear interpolation for Mach and Reynolds numbers.

    Parameters
    ----------
    phi : float
        Value of phi to interpolate.
    phi_values : list
        List of phi values.
    parameter_values : list
        List of parameter values (Mach or Reynolds).
    """

    if phi < min(phi_values):
        phi_0 = phi_values[0]
        phi_1 = phi_values[1]
    elif phi > max(phi_values):
        phi_0 = phi_values[-2]
        phi_1 = phi_values[-1]
    else:
        phi_0 = [phi_ for phi_ in phi_values if (phi_ - phi) < 0][-1]
        phi_1 = [phi_ for phi_ in phi_values if (phi_ - phi) > 0][0]

    # get phi_values index
    idx0 = phi_values.index(phi_0)
    idx1 = phi_values.index(phi_1)
    parameter0 = parameter_values[idx0]
    parameter1 = parameter_values[idx1]

    # do linear interpolation for phi and parameter
    result = parameter0 + (parameter1 - parameter0) * (phi - phi_0) / (phi_1 - phi_0)

    return result
