from functools import reduce


def r_setattr(obj, attr, val):
    """Set attributes recursively."""
    # https://stackoverflow.com/a/31174427/5726899

    pre, _, post = attr.rpartition(".")
    return setattr(r_getattr(obj, pre) if pre else obj, post, val)


def r_getattr(obj, attr, *args):
    """Set attributes recursively, e.g.: r_getattr(curve, 'disch.p')."""

    def _getattr(obj, attr):
        return getattr(obj, attr, *args)

    return reduce(_getattr, [obj] + attr.split("."))
