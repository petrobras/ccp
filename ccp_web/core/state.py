"""Case state updates from submitted forms.

Form inputs are named by the state key, so a POST maps onto the state
directly. Two conventions:

- A checkbox is preceded by a hidden input of the same name with value
  ``false``; the last submitted value wins.
- The gas table is a matrix: ``gas_component_<j>`` names row ``j`` and
  ``gas_fraction_<i>_<j>`` holds gas ``i``'s mol % for that row. It is
  rebuilt into the legacy ``gas_compositions_table`` layout.
"""

import re

from ccp_web.services import gas, schemas

_FRACTION = re.compile(r"^gas_fraction_(\d+)_(\d+)$")
_COMPONENT = re.compile(r"^gas_component_(\d+)$")


def gas_matrix(state):
    """Rows (component, [mol % per gas]) for the gas table, union of all gases."""
    table = state.get("gas_compositions_table") or {}
    components = []
    values = {}
    for i in range(gas.N_GASES):
        entry = table.get(f"gas_{i}") or {}
        for component, fraction in gas.rows(entry):
            if component not in values:
                components.append(component)
                values[component] = [0.0] * gas.N_GASES
            values[component][i] += fraction
    return [(c, values[c]) for c in components]


def _gas_table_from_post(data, state):
    rows = {}
    for key in data:
        m = _COMPONENT.match(key)
        if m:
            rows[int(m.group(1))] = data.getlist(key)[-1].strip()
    order = [j for j in sorted(rows)]
    table = {}
    for i in range(gas.N_GASES):
        name = data.get(f"gas_{i}") or state.get(f"gas_{i}") or f"gas_{i}"
        entry = {"name": name}
        n = 0
        for j in order:
            component = rows[j]
            if not component:
                continue
            raw = (data.get(f"gas_fraction_{i}_{j}") or "").strip().replace(",", ".")
            try:
                fraction = float(raw) if raw else 0.0
            except ValueError:
                fraction = 0.0
            entry[f"component_{n}"] = component
            entry[f"molar_fraction_{n}"] = fraction
            n += 1
        table[f"gas_{i}"] = entry
    return table


def save_post(case, data):
    """Apply submitted fields to the stored state under a row lock.

    Re-reading the row keeps keys a job wrote meanwhile (curve names...).
    """
    from django.db import transaction

    from .models import Case

    if not data:
        return case
    with transaction.atomic():
        fresh = Case.objects.select_for_update().get(pk=case.pk)
        fresh.state = apply_post(fresh.app_type, fresh.state, data)
        fresh.save(update_fields=["state", "updated"])
    case.state = fresh.state
    case.updated = fresh.updated
    return case


def update_state(case, **values):
    """Merge values into the stored state under a row lock."""
    from django.db import transaction

    from .models import Case

    with transaction.atomic():
        fresh = Case.objects.select_for_update().get(pk=case.pk)
        state = dict(fresh.state)
        state.update(values)
        fresh.state = state
        fresh.save(update_fields=["state", "updated"])
    case.state = fresh.state
    case.updated = fresh.updated
    return case


def apply_post(app_type, state, data):
    """Return a new state with the submitted keys applied.

    Only keys present in the submission change; unknown keys are ignored.
    """
    schema = schemas.get_schema(app_type)
    new = dict(state)
    for key in data:
        f = schema.fields.get(key)
        if f is None or f.kind == "json":
            continue
        values = data.getlist(key)
        new[key] = schemas.coerce(f, values[-1] if values else "")
    if any(_COMPONENT.match(k) for k in data):
        new["gas_compositions_table"] = _gas_table_from_post(data, new)
    return schemas.normalize(app_type, new)
