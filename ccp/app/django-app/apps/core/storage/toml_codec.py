"""Small TOML codec for ccp library objects.

This wraps the ``_dict_to_save`` / ``load`` pair the ccp library
exposes on :class:`StraightThrough`, :class:`BackToBack`, and
:class:`Impeller`, so callers can go from a ccp object to a TOML
string and back without reaching into library internals themselves.
"""

from __future__ import annotations

import io
from typing import Any

import toml

import ccp
from ccp.compressor import BackToBack, StraightThrough

# Map the logical app_type produced by :func:`load_ccp_file` to the
# ccp class whose ``.load`` constructor should be used to rebuild the
# object from a TOML document.
_LOADERS = {
    "straight_through": StraightThrough,
    "back_to_back": BackToBack,
    "impeller": ccp.Impeller,
    "curves_conversion": ccp.Impeller,
}


def encode_ccp_object(obj: Any) -> str:
    """Encode a ccp object as a TOML string.

    Parameters
    ----------
    obj : StraightThrough or BackToBack or Impeller
        Any object exposing ``_dict_to_save``.

    Returns
    -------
    str
        TOML document.

    Raises
    ------
    TypeError
        If ``obj`` lacks ``_dict_to_save``.
    """
    if not hasattr(obj, "_dict_to_save"):
        raise TypeError(
            f"Object of type {type(obj).__name__} does not support _dict_to_save."
        )
    return toml.dumps(obj._dict_to_save())


def decode_ccp_object(app_type: str, toml_str: str):
    """Decode a TOML string back into a ccp library object.

    Parameters
    ----------
    app_type : str
        One of ``"straight_through"``, ``"back_to_back"``,
        ``"impeller"``, or ``"curves_conversion"``.
    toml_str : str
        TOML document produced by :func:`encode_ccp_object`.

    Returns
    -------
    object
        A freshly constructed ccp library object.

    Raises
    ------
    ValueError
        If ``app_type`` is not recognised.
    """
    try:
        loader = _LOADERS[app_type]
    except KeyError as exc:
        raise ValueError(f"Unknown app_type for TOML decode: {app_type!r}") from exc
    return loader.load(io.StringIO(toml_str))
