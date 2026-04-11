"""Gas composition helpers ported from ``ccp/app/common.py``.

Provides the sorted fluid list used by selection widgets, the default
6-component mixture referenced by the Streamlit pages, and helpers to resolve
a named composition from a ``gas_compositions_table`` document.
"""

from __future__ import annotations

import ccp

DEFAULT_COMPONENTS: list[str] = [
    "methane",
    "ethane",
    "propane",
    "n-butane",
    "i-butane",
    "n-pentane",
    "i-pentane",
    "n-hexane",
    "n-heptane",
    "n-octane",
    "n-nonane",
    "nitrogen",
    "h2s",
    "co2",
    "h2o",
]


def _build_fluid_list() -> list[str]:
    """Build the sorted fluid list used by the UI dropdowns.

    Returns
    -------
    list of str
        Sorted list of every ``ccp.fluid_list`` key plus each registered
        ``possible_names`` alias, prefixed with an empty string for the
        placeholder row.
    """
    names: list[str] = []
    for fluid in ccp.fluid_list.keys():
        names.append(fluid.lower())
        for possible_name in ccp.fluid_list[fluid].possible_names:
            if possible_name != fluid.lower():
                names.append(possible_name)
    names.sort()
    names.insert(0, "")
    return names


FLUID_LIST: list[str] = _build_fluid_list()


def default_composition() -> dict[str, float]:
    """Return the default 6-component gas mixture.

    The mixture contains the first six :data:`DEFAULT_COMPONENTS` with
    methane at 1.0 and the remaining components zeroed out, mirroring the
    initial row of ``gas_compositions_table`` populated in ``common.py``.

    Returns
    -------
    dict of str to float
        Mapping from component name to molar fraction.
    """
    composition: dict[str, float] = {name: 0.0 for name in DEFAULT_COMPONENTS[:6]}
    composition["methane"] = 1.0
    return composition


def get_gas_composition(
    gas_name: str,
    gas_compositions_table: dict,
    default_components: list[str] | None = None,
) -> dict[str, float]:
    """Resolve a named gas composition into a component-to-fraction dict.

    Parameters
    ----------
    gas_name : str
        Logical name of the gas as stored in
        ``gas_compositions_table[...]['name']``.
    gas_compositions_table : dict
        Nested dict shaped like the ``gas_compositions_table`` produced by the
        Streamlit ``gas_selection_form``.
    default_components : list of str, optional
        Unused — kept for signature parity with ``common.get_gas_composition``.

    Returns
    -------
    dict of str to float
        Non-zero components only.
    """
    del default_components
    composition: dict[str, float] = {}
    for gas in gas_compositions_table.keys():
        entry = gas_compositions_table[gas]
        if entry.get("name") != gas_name:
            continue
        for column in entry:
            if "component" not in column:
                continue
            idx = column.split("_")[1]
            component = entry[f"component_{idx}"]
            molar_fraction = entry.get(f"molar_fraction_{idx}", 0)
            if molar_fraction == "":
                molar_fraction = 0
            molar_fraction = float(molar_fraction)
            if molar_fraction != 0:
                composition[component] = molar_fraction
    return composition


def get_index_selected_gas(gas_options: list[str], gas_name: str) -> int:
    """Return the index of *gas_name* in *gas_options*, or 0 if missing.

    Parameters
    ----------
    gas_options : list of str
        Ordered list of gas choices.
    gas_name : str
        Name to locate within *gas_options*.

    Returns
    -------
    int
        Zero-based index, defaulting to ``0`` when *gas_name* is absent.
    """
    try:
        return gas_options.index(gas_name)
    except ValueError:
        return 0
