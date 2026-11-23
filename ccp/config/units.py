"""This module deals with units conversion in the ccp library."""

import inspect
import math
import threading
import warnings
from contextlib import contextmanager
from functools import lru_cache, wraps
from pathlib import Path

import numpy as np
import pint

from .. import config

new_units_path = Path(__file__).parent / "new_units.txt"
ureg = pint.get_application_registry()

# Check if registry is lazy or already initialized
if isinstance(ureg.get(), pint.registry.LazyRegistry):
    # Registry not yet initialized, create new one
    ureg = pint.UnitRegistry()
else:
    # Registry already initialized, get it
    ureg = ureg.get()

# Check if water column units already exist (pint >= 0.24)
# If they don't exist, we'll use the legacy definitions
has_water_units = False
try:
    # Try to create a quantity with meter_H2O and convert it
    # This will succeed in pint >= 0.24
    test_qty = ureg.Quantity(1, "meter_H2O")
    test_qty.to("pascal")
    has_water_units = True
except (pint.errors.UndefinedUnitError, AttributeError, RecursionError):
    has_water_units = False

# Load custom unit definitions
ureg.load_definitions(str(new_units_path))

# If water units don't exist in pint, load legacy definitions
if not has_water_units:
    legacy_units_path = Path(__file__).parent / "legacy_water_units.txt"
    if legacy_units_path.exists():
        ureg.load_definitions(str(legacy_units_path))

# set ureg to make pickle possible
pint.set_application_registry(ureg)

Q_ = ureg.Quantity

with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    pint.Quantity([])

__all__ = [
    "Q_",
    "GAUGE_UNITS",
    "absolute_to_gauge",
    "ambient_pressure",
    "check_units",
    "gauge_to_absolute",
    "gauge_reference_unit",
    "set_ambient_pressure",
]

# gauge units and the absolute unit each one is an offset of
GAUGE_UNITS = {"barg": "bar", "psig": "psi", "kPag": "kPa", "MPag": "MPa"}

# Serializes the changes of the ambient pressure. Never taken to convert a
# quantity: multiprocessing unpickles the states calculated by the workers in a
# thread of its own while the calling thread, which may hold the lock, waits.
_ambient_lock = threading.RLock()


def gauge_reference_unit(units):
    """Absolute unit of a gauge unit.

    Parameters
    ----------
    units : str or pint.Unit

    Returns
    -------
    reference : str or None
        "bar" for "barg", "psi" for "psig", ... None if it is not a gauge unit.
    """
    names = dict(Q_(1, units).unit_items())
    if len(names) != 1:
        return None
    return GAUGE_UNITS.get(next(iter(names)))


def _is_gauge(value):
    return isinstance(value, pint.Quantity) and (
        gauge_reference_unit(value.units) is not None
    )


def _ambient_pascal(value):
    """Validated ambient pressure as a float in Pa."""
    if _is_gauge(value):
        raise ValueError(
            f"The ambient pressure must be an absolute pressure, got {value}."
        )
    if isinstance(value, pint.Quantity):
        value = value.to("pascal").m
    pascal = float(value)
    if not (math.isfinite(pascal) and pascal > 0):
        raise ValueError(
            f"The ambient pressure must be finite and greater than 0, got {pascal} Pa."
        )
    return pascal


# definitions made by _define_gauge_units, empty while it is running
_gauge_definitions = {}


def _define_gauge_units(pascal):
    """Define the gauge units for an ambient pressure in Pa and store it."""
    definitions = [
        f"{name} = {reference}; offset: {float(Q_(pascal, 'pascal').to(reference).m)!r}"
        for name, reference in GAUGE_UNITS.items()
    ]
    _gauge_definitions.clear()
    on_redefinition = ureg._on_redefinition
    ureg._on_redefinition = "ignore"
    try:
        for definition in definitions:
            ureg.define(definition)
    finally:
        ureg._on_redefinition = on_redefinition
    ureg._build_cache()
    # not through setattr, which calls set_ambient_pressure
    vars(config)["AMBIENT_PRESSURE"] = pascal
    _gauge_definitions.update({name: ureg._units[name] for name in GAUGE_UNITS})


def _is_current(pascal):
    """Whether the gauge units in the registry are those of an ambient pressure.

    They are not if a redefinition was interrupted or if other code redefined
    the units in the registry, which is shared.
    """
    return pascal == config.AMBIENT_PRESSURE and all(
        name in _gauge_definitions and ureg._units[name] is _gauge_definitions[name]
        for name in GAUGE_UNITS
    )


_define_gauge_units(config.AMBIENT_PRESSURE)


def set_ambient_pressure(ambient_pressure):
    """Set the ambient pressure used by the gauge units (barg, psig, kPag, MPag).

    The change is global to the process. Waits for the
    :func:`ccp.ambient_pressure` contexts of other threads to exit.

    Parameters
    ----------
    ambient_pressure : float, pint.Quantity
        Absolute ambient pressure (Pa).
    """
    pascal = _ambient_pascal(ambient_pressure)
    with _ambient_lock:
        # redefining the units and rebuilding the pint cache takes about 15 ms
        if not _is_current(pascal):
            _define_gauge_units(pascal)


@contextmanager
def ambient_pressure(ambient_pressure):
    """Context manager with a temporary ambient pressure.

    The previous value is restored on exit. A lock is held in the block, so
    that contexts in different threads run one at a time (they can be nested in
    the same thread). Threads that convert gauge quantities outside a context
    get the value that is in effect at that moment. The lock belongs to the
    thread: do not ``await`` or ``yield`` in the block.

    Parameters
    ----------
    ambient_pressure : float, pint.Quantity
        Absolute ambient pressure (Pa).

    Examples
    --------
    >>> import ccp
    >>> Q_ = ccp.Q_
    >>> with ccp.ambient_pressure(Q_(0.9, "bar")):
    ...     p = Q_(10, "barg").to("bar")
    >>> round(p.m, 6)
    10.9
    """
    pascal = _ambient_pascal(ambient_pressure)
    with _ambient_lock:
        previous = config.AMBIENT_PRESSURE
        try:
            set_ambient_pressure(pascal)
            yield
        finally:
            set_ambient_pressure(previous)


def _plain_pressure(value, name):
    if not isinstance(value, pint.Quantity):
        value = Q_(value, "pascal")
    if _is_gauge(value):
        raise ValueError(
            f"{name} must not be in a gauge unit such as {value.units}: use the "
            f"plain unit, {gauge_reference_unit(value.units)}."
        )
    return value


def _ambient_quantity(value):
    """Ambient pressure of the pure functions: the current one if None, or arrays."""
    if value is None:
        return Q_(config.AMBIENT_PRESSURE, "pascal")
    value = _plain_pressure(value, "The ambient pressure")
    if not np.all(np.isfinite(value.m) & (np.asarray(value.m) > 0)):
        raise ValueError(
            f"The ambient pressure must be finite and greater than 0, got {value}."
        )
    return value


def gauge_to_absolute(p, ambient_pressure=None):
    """Absolute pressure from a gauge reading.

    Parameters
    ----------
    p : float, pint.Quantity
        Gauge reading (Pa) in a plain unit: ``Q_(10, "bar")`` for 10 bar gauge.
    ambient_pressure : float, pint.Quantity, optional
        Absolute ambient pressure (Pa).
        Default is ccp.config.AMBIENT_PRESSURE.

    Returns
    -------
    p : pint.Quantity
        Absolute pressure in the unit of the reading.

    Examples
    --------
    >>> import ccp
    >>> Q_ = ccp.Q_
    >>> p = ccp.units.gauge_to_absolute(Q_(10, "kgf/cm²"), Q_(1.0, "kgf/cm²"))
    >>> round(p.to("kgf/cm²").m, 6)
    11.0
    """
    p = _plain_pressure(p, "The gauge reading")
    ambient = _ambient_quantity(ambient_pressure)
    return p + ambient.to(p.units)


def absolute_to_gauge(p, units=None, ambient_pressure=None):
    """Gauge value (difference to the ambient pressure) of an absolute pressure.

    Parameters
    ----------
    p : float, pint.Quantity
        Absolute pressure (Pa).
    units : str, optional
        Plain unit of the gauge value (e.g. "bar", "kgf/cm²").
        Default is the unit of ``p``.
    ambient_pressure : float, pint.Quantity, optional
        Absolute ambient pressure (Pa).
        Default is ccp.config.AMBIENT_PRESSURE.

    Returns
    -------
    p : pint.Quantity
        Gauge value, in a plain unit.

    Examples
    --------
    >>> import ccp
    >>> Q_ = ccp.Q_
    >>> p = ccp.units.absolute_to_gauge(Q_(11, "bar"), "bar", Q_(1.0, "bar"))
    >>> round(p.m, 6)
    10.0
    """
    p = _plain_pressure(p, "The absolute pressure")
    if units is not None:
        _plain_pressure(Q_(1, units), "The gauge value")
        p = p.to(units)
    ambient = _ambient_quantity(ambient_pressure)
    return p - ambient.to(p.units)


def _absolute(value):
    """Gauge quantities converted to Pa, other values unchanged.

    For values sent to worker processes, which have the default ambient pressure.
    """
    return value.to("pascal") if _is_gauge(value) else value


units = {
    "E": "N/m**2",
    "Gs": "N/m**2",
    "rho": "kg/m**3",
    "density": "kg/m**3",
    "L": "meter",
    "idl": "meter",
    "idr": "meter",
    "odl": "meter",
    "odr": "meter",
    "id": "meter",
    "od": "meter",
    "i_d": "meter",
    "o_d": "meter",
    "speed": "radian/second",
    "frequency": "radian/second",
    "specific_heat": "J/kg/degK",
    "mx": "kg",
    "my": "kg",
    "Ip": "kg*m**2",
    "Id": "kg*m**2",
    "width": "meter",
    "depth": "meter",
    "thickness": "meter",
    "pitch": "meter",
    "height": "meter",
    "radius": "meter",
    "diameter": "meter",
    "clearance": "meter",
    "length": "meter",
    "area": "meter**2",
    "unbalance_magnitude": "kg*m",
    "unbalance_phase": "rad",
    "pressure": "pascal",
    "pressure_ratio": "dimensionless",
    "p": "pascal",
    "temperature": "degK",
    "T": "degK",
    "velocity": "m/s",
    "angle": "rad",
    "arc": "rad",
    "convection": "W/(m²*degK)",
    "conductivity": "W/(m*degK)",
    "expansion": "1/degK",
    "stiffness": "N/m",
    "weight": "N",
    "load": "N",
    "force": "N",
    "torque": "N*m",
    "flow_v": "meter**3/second",
    "flow_m": "kilogram/second",
    "fit": "m",
    "viscosity": "pascal*s",
    "h": "joule/kilogram",
    "s": "joule/(kelvin kilogram)",
    "b": "meter",
    "D": "meter",
    "d": "meter",
    "dc": "meter",
    "roughness": "meter",
    "head": "joule/kilogram",
    "eff": "dimensionless",
    "power": "watt",
    "phi_ratio": "dimensionless",
    "psi_ratio": "dimensionless",
    "reynolds_ratio": "dimensionless",
    "mach_diff": "dimensionless",
    "volume_ratio_ratio": "dimensionless",
    "voltage": "volt",
    "current": "ampere",
    # full-name entries: the token scan would match "power" -> watt
    "power_factor": "dimensionless",
    "rated_power_factor": "dimensionless",
    "efficiency": "dimensionless",
    # full-name entries: the token scan would match "frequency" -> radian/second
    "rated_frequency": "hertz",
    "supply_frequency": "hertz",
}
for i, unit in zip(["k", "c"], ["N/m", "N*s/m"]):
    for j in ["x", "y", "z"]:
        for k in ["x", "y", "z"]:
            units["".join([i, j, k])] = unit


@lru_cache(maxsize=None)
def _unit_for(arg_name):
    """Default unit for an argument name, or None when it has no unit.

    The check is carried out by splitting the argument name on '_' and looking
    each token up in :data:`units` (the full name is tried first). Resolved
    once per name: the decorator resolves positional names when the function
    is decorated and keyword names on first use.
    """
    names = arg_name.split("_")
    if "units" in names:
        return None
    # treat flow_v and flow_m separately
    if "flow_v" in arg_name:
        names.insert(0, "flow_v")
    if "flow_m" in arg_name:
        names.insert(0, "flow_m")
    if arg_name not in names:
        # check first for arg_name in units
        names.insert(0, arg_name)
    for name in names:
        if name in units:
            return units[name]
    return None


@lru_cache(maxsize=None)
def _is_pressure_difference(arg_name):
    return _unit_for(arg_name) == "pascal" and not {
        "delta",
        "differential",
        "drop",
        "difference",
    }.isdisjoint(arg_name.split("_"))


def _check_difference(arg_name, value):
    """Refuse a gauge unit, which has an offset, for a pressure difference."""
    if _is_pressure_difference(arg_name) and _is_gauge(value):
        raise ValueError(
            f"{arg_name} is a pressure difference and cannot be in a gauge unit "
            f"such as {value.units}: use {gauge_reference_unit(value.units)}."
        )


def _to_default_unit(value, unit):
    if unit is None or value is None:
        return value
    # For now, we only return the magnitude for the converted Quantity
    # If pint is fully adopted by ross in the future, and we have all Quantities
    # using it, we could remove this, which would allows us to use pint in its full capability
    try:
        return value.to(unit)
    except AttributeError:
        try:
            return Q_(value, unit)
        except TypeError:
            # Handle errors that we get with bool for example
            return value


def check_units(func):
    """Wrapper to check and convert units to base_units.
    If we use the check_units decorator in a function the arguments are checked,
    and if they are in the dictionary, they are converted to the 'default' unit given
    in the dictionary.
    The check is carried out by splitting the argument name on '_', and checking
    if any of the names are in the dictionary. So an argument such as 'inlet_pressure',
    will be split into ['inlet', 'pressure'], and since we have the name 'pressure'
    in the dictionary mapped to 'Pa', we will automatically convert the value to
    this default unit.
    Gauge pressures (barg, psig, kPag, MPag) are converted to absolute pressure
    with the ambient pressure, and are refused for pressure differences
    ('delta_p', 'pressure_drop').
    For example, 'L' is mapped to 'meter' in the units dictionary:

    >>> @check_units
    ... def foo(L=None):
    ...     print(L)

    If we call the function with the argument as a float, it is assumed to be
    in the default unit:

    >>> foo(L=0.5)
    0.5 meter

    If we call the function with a pint.Quantity object the value is automatically
    converted to the default:

    >>> foo(L=Q_(0.5, 'inches'))
    0.0127 meter
    """

    # resolved once per decorated function instead of once per call
    arg_names = inspect.getfullargspec(func)[0]
    arg_units = [_unit_for(name) for name in arg_names]
    differences = [
        (i, name) for i, name in enumerate(arg_names) if _is_pressure_difference(name)
    ]

    @wraps(func)
    def inner(*args, **kwargs):
        for i, name in differences:
            if i < len(args):
                _check_difference(name, args[i])
        for name, value in kwargs.items():
            _check_difference(name, value)
        base_unit_args = [
            _to_default_unit(value, unit) for value, unit in zip(args, arg_units)
        ]
        base_unit_kwargs = {
            k: _to_default_unit(v, _unit_for(k)) for k, v in kwargs.items()
        }
        return func(*base_unit_args, **base_unit_kwargs)

    return inner
