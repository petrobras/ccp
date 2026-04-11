"""Polytropic method mapping used by the UI dropdown.

Keys are human-readable labels shown in the interface; values are the strings
expected by ``ccp.config.POLYTROPIC_METHOD``. Ported verbatim from
``ccp/app/common.py``.
"""

POLYTROPIC_METHODS: dict[str, str] = {
    "Sandberg-Colby": "sandberg_colby",
    "Sandberg-Colby Multistep": "sandberg_colby_multistep",
    "Huntington": "huntington",
    "Mallen-Saville": "mallen_saville",
    "Schultz": "schultz",
}


def get_polytropic_methods() -> dict[str, str]:
    """Return a fresh copy of the polytropic-method mapping.

    Returns
    -------
    dict of str to str
        Copy of :data:`POLYTROPIC_METHODS` safe for mutation by the caller.
    """
    return dict(POLYTROPIC_METHODS)


def resolve(label: str) -> str:
    """Translate a UI label to the ``ccp.config`` value.

    Parameters
    ----------
    label : str
        Human-readable label as displayed in the UI.

    Returns
    -------
    str
        The ``ccp.config.POLYTROPIC_METHOD`` value associated with *label*.

    Raises
    ------
    KeyError
        If *label* is not a known polytropic method.
    """
    return POLYTROPIC_METHODS[label]
