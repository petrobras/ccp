import inspect
from functools import wraps

from .. import Q_

units = {
    "p": "pascal",
    "disch_p": "pascal",
    "T": "kelvin",
    "rho": "kilogram/m**3",
    "speed": "radian/second",
    "flow_v": "meter**3/second",
    "flow_m": "kilogram/second",
    "h": "joule/kilogram",
    "s": "joule/(kelvin kilogram)",
    "b": "meter",
    "D": "meter",
    "head": "joule/kilogram",
    "eff": "dimensionless",
    "power": "watt",
}


def check_units(func):
    """Wrapper to check and convert units to base_units."""

    @wraps(func)
    def inner(*args, **kwargs):
        base_unit_args = []
        args_names = inspect.getfullargspec(func)[0]

        for arg_name, arg_value in zip(args_names, args):
            if arg_name in units:
                try:
                    base_unit_args.append(arg_value.to(units[arg_name]))
                except AttributeError:
                    base_unit_args.append(Q_(arg_value, units[arg_name]))
            else:
                base_unit_args.append(arg_value)

        base_unit_kwargs = {}
        for k, v in kwargs.items():
            if k in units and v is not None:
                try:
                    base_unit_kwargs[k] = v.to(units[k])
                except AttributeError:
                    base_unit_kwargs[k] = Q_(v, units[k])
            else:
                base_unit_kwargs[k] = v

        return func(*base_unit_args, **base_unit_kwargs)

    return inner


def change_data_units(x_data, y_data, x_units=None, y_units=None):
    """Change data units for plotting."""
    if x_units is not None:
        x_data = x_data.to(x_units)

    if y_units is not None:
        y_data = y_data.to(y_units)

    return x_data, y_data
