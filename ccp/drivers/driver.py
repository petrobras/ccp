"""Base class for compressor drivers.

A driver delivers shaft power to the compressor (e.g. an electric motor, a
steam turbine or a gas turbine). Driver classes estimate that power from
field measurements, so it can be compared with the thermodynamic power
calculated by ccp (``Point.power_shaft``).
"""

from dataclasses import dataclass

import pint

from ccp.config.units import check_units
from ccp.data_io.serializers import Serializable


@dataclass(frozen=True)
class PowerComparison:
    """Result of comparing driver power with a performance point.

    Attributes
    ----------
    driver_power : pint.Quantity
        Driver shaft power (Watt).
    transmitted_power : pint.Quantity
        Power delivered at the compressor coupling (Watt):
        driver power times coupling and gearbox efficiencies.
    point_power : pint.Quantity
        Compressor shaft power from the performance point (Watt).
    delta : pint.Quantity
        transmitted_power - point_power (Watt). Positive means the driver
        delivers more power than the thermodynamic calculation requires.
    delta_ratio : pint.Quantity
        delta / point_power (dimensionless).
    method : str
        Load estimation method used by the driver.
    load : pint.Quantity
        Driver load fraction (dimensionless).
    """

    driver_power: pint.Quantity
    transmitted_power: pint.Quantity
    point_power: pint.Quantity
    delta: pint.Quantity
    delta_ratio: pint.Quantity
    method: str
    load: pint.Quantity

    def __str__(self):
        return (
            f"Driver Power: {self.driver_power.to('kW'):.2f~P}"
            f"\nTransmitted Power: {self.transmitted_power.to('kW'):.2f~P}"
            f"\nPoint Shaft Power: {self.point_power.to('kW'):.2f~P}"
            f"\nDelta: {self.delta.to('kW'):.2f~P}"
            f"\nDelta Ratio: {self.delta_ratio.m:.4f}"
            f"\nMethod: {self.method}"
            f"\nLoad: {self.load.m:.4f}"
        )


class Driver(Serializable):
    """Base class for compressor drivers.

    Subclasses hold the driver's fixed (nameplate) data and implement
    :meth:`estimate`, which computes the driver shaft power from field
    measurements passed as keyword arguments.

    Parameters
    ----------
    rated_power : float, pint.Quantity
        Rated shaft output power (Watt).
    rated_speed : float, pint.Quantity
        Rated speed (rad/s).
    tag : str, optional
        Tag to identify the driver.
    """

    @check_units
    def __init__(self, rated_power=None, rated_speed=None, tag=None):
        self.rated_power = rated_power
        self.rated_speed = rated_speed
        self.tag = tag

    def estimate(self, **measurements):
        """Estimate driver load and shaft power from field measurements."""
        raise NotImplementedError

    def power_output(self, **measurements):
        """Driver shaft power (Watt) estimated from field measurements."""
        return self.estimate(**measurements).power_output

    @check_units
    def compare(
        self, point, coupling_efficiency=1.0, gearbox_efficiency=1.0, **measurements
    ):
        """Compare driver power with the shaft power of a performance point.

        Parameters
        ----------
        point : ccp.Point
            Performance point with the compressor shaft power
            (``point.power_shaft``).
        coupling_efficiency : float, pint.Quantity, optional
            Coupling efficiency between driver and compressor.
            Default is 1.0.
        gearbox_efficiency : float, pint.Quantity, optional
            Gearbox efficiency between driver and compressor.
            Default is 1.0.
        **measurements
            Field measurements passed to :meth:`estimate`
            (e.g. voltage, current, power_factor for an induction motor).

        Returns
        -------
        comparison : ccp.drivers.PowerComparison
            Comparison with driver power, transmitted power, point power and
            deltas.
        """
        estimate = self.estimate(**measurements)
        transmitted_power = (
            estimate.power_output * coupling_efficiency * gearbox_efficiency
        ).to("watt")
        point_power = point.power_shaft.to("watt")
        delta = transmitted_power - point_power

        return PowerComparison(
            driver_power=estimate.power_output.to("watt"),
            transmitted_power=transmitted_power,
            point_power=point_power,
            delta=delta,
            delta_ratio=(delta / point_power).to("dimensionless"),
            method=estimate.method,
            load=estimate.load,
        )
