"""Gas composition table: six named gases, each a list of (component, mol %).

The state layout is the Streamlit one: ``gas_0`` .. ``gas_5`` hold the gas
names and ``gas_compositions_table`` maps ``gas_i`` to
``{"name", "component_j", "molar_fraction_j"}``.
"""

import functools

import ccp

N_GASES = 6

default_components = [
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


@functools.lru_cache(maxsize=1)
def fluid_list():
    """Sorted component names and aliases known to ccp, with '' first."""
    names = []
    for fluid in ccp.fluid_list.keys():
        names.append(fluid.lower())
        for possible_name in ccp.fluid_list[fluid].possible_names:
            if possible_name != fluid.lower():
                names.append(possible_name)
    names = sorted(set(names))
    names.insert(0, "")
    return names


def default_table():
    table = {}
    for i in range(N_GASES):
        gas = {"name": f"gas_{i}"}
        for j, component in enumerate(default_components):
            gas[f"component_{j}"] = component
            gas[f"molar_fraction_{j}"] = 0.0
        table[f"gas_{i}"] = gas
    return table


def _fraction(value):
    if value in ("", None):
        return 0.0
    try:
        return float(str(value).replace(",", "."))
    except ValueError:
        return 0.0


def rows(gas):
    """Component rows of one gas entry, in index order."""
    indices = sorted(int(k.split("_")[1]) for k in gas if k.startswith("component_"))
    return [
        (gas.get(f"component_{j}", ""), _fraction(gas.get(f"molar_fraction_{j}")))
        for j in indices
    ]


def normalize_state(state):
    """Make ``gas_i`` names and the composition table consistent in place.

    Missing gases get the default component rows; the table ``name`` follows
    the top-level ``gas_i`` key, which the selects use.
    """
    table = state.get("gas_compositions_table")
    if not isinstance(table, dict):
        table = {}
    defaults = default_table()
    for i in range(N_GASES):
        key = f"gas_{i}"
        gas = table.get(key)
        if not isinstance(gas, dict):
            gas = {}
        if not any(k.startswith("component_") for k in gas):
            gas = {**defaults[key], **{k: v for k, v in gas.items() if k == "name"}}
        name = state.get(key) or gas.get("name") or key
        gas["name"] = name
        state[key] = name
        table[key] = gas
    state["gas_compositions_table"] = table
    return state


def gas_names(state):
    return [state.get(f"gas_{i}") or f"gas_{i}" for i in range(N_GASES)]


def composition(state, gas_name):
    """``{component: mol %}`` for the named gas, zero rows dropped.

    Mirrors ``common.get_gas_composition``: ccp normalises the fractions.
    """
    table = state.get("gas_compositions_table") or {}
    for i in range(N_GASES):
        key = f"gas_{i}"
        gas = table.get(key) or {}
        name = state.get(key) or gas.get("name")
        if name == gas_name:
            result = {}
            for component, fraction in rows(gas):
                if component and fraction != 0:
                    result[component] = result.get(component, 0.0) + fraction
            return result
    return {}


def summary(state, gas_name):
    """Totals and dominant component for the inspector panel."""
    comp = composition(state, gas_name)
    total = sum(comp.values())
    dominant = max(comp.items(), key=lambda kv: kv[1]) if comp else None
    return {
        "name": gas_name,
        "total": total,
        "n_components": len(comp),
        "dominant": dominant,
        "valid": abs(total - 100) < 0.5 or abs(total - 1) < 0.005,
    }
