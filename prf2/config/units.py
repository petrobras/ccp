from .. import Q_

units = {'p': 'pascal', 'T': 'kelvin', 'speed': 'radian/second'}


def check_units(func):
    """Wrapper to check and convert units to base_units."""
    def inner(*args, **kwargs):
        base_unit_kwargs = {}
        for k, v in kwargs.items():
            if k in units:
                try:
                    base_unit_kwargs[k] = v.to(units[k])
                except AttributeError:
                    base_unit_kwargs[k] = Q_(v, units[k])
            else:
                base_unit_kwargs[k] = v

        return func(*args, **base_unit_kwargs)
    return inner

