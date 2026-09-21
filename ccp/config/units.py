"""This module deals with units conversion in the ccp library."""

import inspect
import warnings
from functools import lru_cache, wraps
from pathlib import Path

import pint

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

__all__ = ["Q_", "check_units"]

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
    arg_units = [_unit_for(name) for name in inspect.getfullargspec(func)[0]]

    @wraps(func)
    def inner(*args, **kwargs):
        base_unit_args = [
            _to_default_unit(value, unit) for value, unit in zip(args, arg_units)
        ]
        base_unit_kwargs = {
            k: _to_default_unit(v, _unit_for(k)) for k, v in kwargs.items()
        }
        return func(*base_unit_args, **base_unit_kwargs)

    return inner
