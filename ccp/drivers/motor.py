"""Induction motor driver.

Estimates motor load and shaft power from field electrical measurements
using the methods of the U.S. DOE fact sheet "Determining Electric Motor
Load and Efficiency" (IEEE 112 field practice): input power, line current
and slip.
"""

import warnings
from dataclasses import dataclass

import numpy as np
import pint
from scipy.interpolate import interp1d

from ccp.config.units import Q_, check_units
from ccp.drivers.driver import Driver


@dataclass(frozen=True)
class MotorEstimate:
    """Result of a motor load/power estimation.

    Attributes
    ----------
    method : str
        Load estimation method used ("input_power", "current" or "slip").
    load : pint.Quantity
        Motor load fraction (shaft power / rated power, dimensionless).
    efficiency : pint.Quantity or None
        Motor efficiency at the estimated load (None for the current and
        slip methods, which do not use the efficiency).
    input_power : pint.Quantity or None
        Three-phase electrical input power (Watt). None for the slip method.
    power_output : pint.Quantity
        Motor shaft power (Watt).
    """

    method: str
    load: pint.Quantity
    efficiency: pint.Quantity
    input_power: pint.Quantity
    power_output: pint.Quantity

    def __str__(self):
        efficiency = f"{self.efficiency.m:.4f}" if self.efficiency is not None else "-"
        input_power = (
            f"{self.input_power.to('kW'):.2f~P}"
            if self.input_power is not None
            else "-"
        )
        return (
            f"Method: {self.method}"
            f"\nLoad: {self.load.m:.4f}"
            f"\nEfficiency: {efficiency}"
            f"\nInput Power: {input_power}"
            f"\nPower Output: {self.power_output.to('kW'):.2f~P}"
        )


class InductionMotor(Driver):
    """Induction motor driver.

    Holds the motor nameplate data and estimates load and shaft power from
    field measurements (voltage, current, power factor, speed), following the
    U.S. DOE fact sheet "Determining Electric Motor Load and Efficiency":

    - Input power method (preferred): three-phase input power
      P = sqrt(3) * V * I * PF times the motor efficiency. When an efficiency
      curve is given, the efficiency at the estimated load is found
      iteratively.
    - Current method: load = (I / rated current) * (V / rated voltage);
      unreliable below 50% load, where the current-load relation becomes
      non-linear.
    - Slip method: load = slip / rated slip, optionally voltage compensated
      by (V / rated voltage)**2. Accuracy is limited by the NEMA tolerance
      on the nameplate full-load speed.

    For motors fed by a variable frequency drive (VFD), pass the drive output
    frequency as ``supply_frequency`` to the estimation methods (synchronous
    speed follows it) and set ``vfd_efficiency`` if the electrical
    measurements are taken at the drive input rather than at the motor
    terminals. The slip method under VFD assumes constant rated slip in
    absolute speed units (constant V/f), a reasonable approximation for
    ~30-100% of rated frequency.

    Note that pint treats radian as dimensionless, so converting between
    "Hz" and "rad/s" does not apply a 2*pi factor. Electrical frequencies
    are kept in Hz and the synchronous speed is computed explicitly as
    4*pi*f/poles.

    Parameters
    ----------
    rated_power : float, pint.Quantity
        Rated (nameplate) shaft output power (Watt).
    rated_voltage : float, pint.Quantity
        Rated line-to-line RMS voltage (Volt).
    rated_current : float, pint.Quantity
        Rated line RMS current (Ampere).
    rated_speed : float, pint.Quantity
        Nameplate full-load speed (rad/s).
    rated_frequency : float, pint.Quantity
        Rated supply frequency (Hz).
    poles : int, optional
        Number of poles (even). If not given, it is derived from
        rated_frequency and rated_speed.
    rated_power_factor : float, pint.Quantity, optional
        Power factor at rated load (dimensionless).
    efficiency : float, pint.Quantity, optional
        Full-load efficiency (dimensionless). Provide either efficiency or
        efficiency_curve, not both.
    efficiency_curve : array-like, optional
        (N, 2) array with (load fraction, efficiency) rows, e.g.
        [[0.25, 0.90], [0.5, 0.93], [0.75, 0.936], [1.0, 0.93]].
        Interpolated with degree 3 when more than 3 points are given
        (degree 1 otherwise) and clamped at the end points.
    vfd_efficiency : float, pint.Quantity, optional
        Variable frequency drive efficiency (dimensionless). Set only when
        the electrical measurements are taken at the drive input; the input
        power is multiplied by this value to obtain the power at the motor
        terminals.
    tag : str, optional
        Tag to identify the motor.

    Examples
    --------
    >>> import ccp
    >>> Q_ = ccp.Q_
    >>> motor = ccp.InductionMotor(
    ...     rated_power=Q_(40, "hp"),
    ...     rated_voltage=Q_(460, "volt"),
    ...     rated_current=Q_(46, "ampere"),
    ...     rated_speed=Q_(1780, "rpm"),
    ...     rated_frequency=Q_(60, "Hz"),
    ...     rated_power_factor=0.86,
    ...     efficiency=0.93,
    ... )
    >>> motor.input_power(voltage=469.7, current=37, power_factor=0.763).to("kW")
    <Quantity(22.9671681, 'kilowatt')>
    >>> motor.power_output(voltage=469.7, current=37, power_factor=0.763).to("kW")
    <Quantity(21.3594664, 'kilowatt')>
    """

    @check_units
    def __init__(
        self,
        rated_power=None,
        rated_voltage=None,
        rated_current=None,
        rated_speed=None,
        rated_frequency=None,
        poles=None,
        rated_power_factor=None,
        efficiency=None,
        efficiency_curve=None,
        vfd_efficiency=None,
        tag=None,
    ):
        super().__init__(rated_power=rated_power, rated_speed=rated_speed, tag=tag)
        self.rated_voltage = rated_voltage
        self.rated_current = rated_current
        self.rated_frequency = rated_frequency
        self.rated_power_factor = rated_power_factor
        self.vfd_efficiency = vfd_efficiency

        if efficiency is not None and efficiency_curve is not None:
            raise ValueError("Provide either efficiency or efficiency_curve, not both.")
        self.efficiency = efficiency

        self._efficiency_interp = None
        if efficiency_curve is not None:
            curve = np.asarray(getattr(efficiency_curve, "m", efficiency_curve))
            if curve.ndim != 2 or curve.shape[1] != 2:
                raise ValueError(
                    "efficiency_curve must be an (N, 2) array with "
                    "(load fraction, efficiency) rows."
                )
            curve = curve[np.argsort(curve[:, 0])]
            self._efficiency_interp = interp1d(
                curve[:, 0],
                curve[:, 1],
                kind=3 if len(curve) > 3 else 1,
                bounds_error=False,
                fill_value=(curve[0, 1], curve[-1, 1]),
            )
            self.efficiency_curve = curve
        else:
            self.efficiency_curve = None

        if poles is None and rated_frequency is not None and rated_speed is not None:
            # poles from the synchronous speed immediately above the
            # full-load speed: 120 * f / rpm rounded down to an even number
            poles = 2 * int(60 * rated_frequency.to("Hz").m / rated_speed.to("rpm").m)
        self.poles = poles

    @check_units
    def input_power(self, voltage=None, current=None, power_factor=None):
        """Three-phase electrical input power (Watt).

        P = sqrt(3) * V * I * PF, with V the mean line-to-line RMS voltage
        and I the mean RMS current.

        Parameters
        ----------
        voltage : float, pint.Quantity
            Line-to-line RMS voltage (Volt), mean of the 3 phases.
        current : float, pint.Quantity
            RMS current (Ampere), mean of the 3 phases.
        power_factor : float, pint.Quantity
            Power factor (dimensionless), mean of the 3 phases.

        Returns
        -------
        input_power : pint.Quantity
            Three-phase input power (Watt).
        """
        if voltage is None or current is None or power_factor is None:
            raise ValueError(
                "voltage, current and power_factor are required to calculate "
                "the input power."
            )
        return (np.sqrt(3) * voltage * current * power_factor).to("watt")

    def efficiency_at_load(self, load):
        """Motor efficiency at a given load fraction.

        Interpolated from the efficiency curve when available, otherwise the
        single efficiency value is returned.

        Parameters
        ----------
        load : float
            Load fraction (shaft power / rated power, dimensionless).

        Returns
        -------
        efficiency : pint.Quantity
            Efficiency at the given load (dimensionless).
        """
        load = getattr(load, "m", load)
        if self._efficiency_interp is not None:
            return Q_(float(self._efficiency_interp(load)), "dimensionless")
        if self.efficiency is not None:
            return self.efficiency
        raise ValueError(
            "No efficiency information. Provide efficiency or efficiency_curve "
            "to use the input power method."
        )

    @check_units
    def synchronous_speed(self, supply_frequency=None):
        """Synchronous speed for a supply frequency.

        Parameters
        ----------
        supply_frequency : float, pint.Quantity, optional
            Supply frequency (Hz). Defaults to the rated frequency.

        Returns
        -------
        synchronous_speed : pint.Quantity
            Synchronous speed (rad/s): 4 * pi * f / poles.
        """
        if supply_frequency is None:
            supply_frequency = self.rated_frequency
        if supply_frequency is None or self.poles is None:
            raise ValueError(
                "supply_frequency (or rated_frequency) and poles are required "
                "to calculate the synchronous speed."
            )
        return Q_(4 * np.pi * supply_frequency.to("Hz").m / self.poles, "rad/s")

    @check_units
    def estimate(
        self,
        voltage=None,
        current=None,
        power_factor=None,
        input_power=None,
        speed=None,
        supply_frequency=None,
        method=None,
    ):
        """Estimate motor load and shaft power from field measurements.

        The method is selected automatically from the available measurements
        (input_power or voltage + current + power_factor -> "input_power";
        current -> "current"; speed -> "slip") and can be forced with the
        method argument.

        Parameters
        ----------
        voltage : float, pint.Quantity, optional
            Measured line-to-line RMS voltage (Volt), mean of the 3 phases.
        current : float, pint.Quantity, optional
            Measured RMS current (Ampere), mean of the 3 phases.
        power_factor : float, pint.Quantity, optional
            Measured power factor (dimensionless).
        input_power : float, pint.Quantity, optional
            Measured three-phase input power (Watt), when directly available.
        speed : float, pint.Quantity, optional
            Measured motor speed (rad/s), for the slip method.
        supply_frequency : float, pint.Quantity, optional
            Supply frequency (Hz) when different from rated (VFD operation).
        method : str, optional
            Force the estimation method: "input_power", "current" or "slip".

        Returns
        -------
        estimate : ccp.drivers.MotorEstimate
            Estimation result with method, load, efficiency, input power and
            power output.
        """
        if method is None:
            if input_power is not None or (
                voltage is not None and current is not None and power_factor is not None
            ):
                method = "input_power"
            elif current is not None:
                method = "current"
            elif speed is not None:
                method = "slip"
            else:
                raise ValueError(
                    "Insufficient measurements. Provide input_power (or "
                    "voltage, current and power_factor), current, or speed."
                )

        if method == "input_power":
            return self._estimate_input_power(
                voltage, current, power_factor, input_power
            )
        elif method == "current":
            return self._estimate_current(current, voltage)
        elif method == "slip":
            return self._estimate_slip(speed, supply_frequency, voltage)
        raise ValueError(
            f"Unknown method {method!r}. "
            'Options are "input_power", "current" or "slip".'
        )

    def estimate_load(self, **measurements):
        """Motor load fraction (dimensionless) estimated from measurements."""
        return self.estimate(**measurements).load

    def _estimate_input_power(self, voltage, current, power_factor, input_power):
        if input_power is None:
            input_power = self.input_power(
                voltage=voltage, current=current, power_factor=power_factor
            )
        motor_input = input_power
        if self.vfd_efficiency is not None:
            motor_input = motor_input * self.vfd_efficiency

        if self.rated_power is None:
            raise ValueError("rated_power is required to estimate the motor load.")

        efficiency = self.efficiency_at_load(1.0)
        if self._efficiency_interp is not None:
            for _ in range(50):
                load = (motor_input * efficiency / self.rated_power).to("dimensionless")
                new_efficiency = self.efficiency_at_load(load.m)
                converged = abs(new_efficiency.m - efficiency.m) < 1e-6
                efficiency = new_efficiency
                if converged:
                    break

        power_output = (motor_input * efficiency).to("watt")
        load = (power_output / self.rated_power).to("dimensionless")

        return MotorEstimate(
            method="input_power",
            load=load,
            efficiency=efficiency,
            input_power=input_power.to("watt"),
            power_output=power_output,
        )

    def _estimate_current(self, current, voltage):
        if current is None:
            raise ValueError("current is required for the current method.")
        if self.rated_current is None or self.rated_power is None:
            raise ValueError(
                "rated_current and rated_power are required for the current method."
            )

        load = (current / self.rated_current).to("dimensionless")
        if voltage is not None:
            if self.rated_voltage is None:
                raise ValueError("rated_voltage is required for voltage compensation.")
            load = (load * voltage / self.rated_voltage).to("dimensionless")

        if load.m < 0.5:
            warnings.warn(
                "The current method is unreliable below 50% load, where the "
                "current-load relation becomes non-linear."
            )

        return MotorEstimate(
            method="current",
            load=load,
            efficiency=None,
            input_power=None,
            power_output=(load * self.rated_power).to("watt"),
        )

    def _estimate_slip(self, speed, supply_frequency, voltage):
        if speed is None:
            raise ValueError("speed is required for the slip method.")
        if (
            self.rated_frequency is None
            or self.rated_speed is None
            or self.rated_power is None
        ):
            raise ValueError(
                "rated_frequency, rated_speed and rated_power are required "
                "for the slip method."
            )

        if supply_frequency is None:
            supply_frequency = self.rated_frequency
        synchronous_speed = self.synchronous_speed(supply_frequency=supply_frequency)
        rated_slip = self.synchronous_speed() - self.rated_speed

        load = ((synchronous_speed - speed) / rated_slip).to("dimensionless")
        if voltage is not None:
            if self.rated_voltage is None:
                raise ValueError("rated_voltage is required for voltage compensation.")
            load = (load * (voltage / self.rated_voltage) ** 2).to("dimensionless")

        # under VFD (constant V/f), rated slip is assumed constant in absolute
        # speed units, and available power scales with frequency
        frequency_ratio = (supply_frequency / self.rated_frequency).to("dimensionless")
        power_output = (load * self.rated_power * frequency_ratio).to("watt")

        return MotorEstimate(
            method="slip",
            load=load,
            efficiency=None,
            input_power=None,
            power_output=power_output,
        )

    def to_dict(self):
        """Return motor parameters as a dict (None fields omitted)."""
        parameters = {}
        for attr in [
            "rated_power",
            "rated_voltage",
            "rated_current",
            "rated_speed",
            "rated_frequency",
            "rated_power_factor",
            "efficiency",
            "vfd_efficiency",
        ]:
            value = getattr(self, attr)
            if value is not None:
                parameters[attr] = str(value)
        if self.poles is not None:
            parameters["poles"] = int(self.poles)
        if self.efficiency_curve is not None:
            parameters["efficiency_curve"] = self.efficiency_curve.tolist()
        if self.tag is not None:
            parameters["tag"] = self.tag
        return parameters

    @classmethod
    def from_dict(cls, dict_parameters):
        """Create motor from a dict created with :meth:`to_dict`."""
        parameters = {k: v for k, v in dict_parameters.items() if k != "ccp_version"}
        for k in [
            "rated_power",
            "rated_voltage",
            "rated_current",
            "rated_speed",
            "rated_frequency",
            "rated_power_factor",
            "efficiency",
            "vfd_efficiency",
        ]:
            if k in parameters:
                parameters[k] = Q_(parameters[k])
        return cls(**parameters)
