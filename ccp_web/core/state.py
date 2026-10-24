"""Case state updates from submitted forms.

Form inputs are named by the state key, so a POST maps onto the state
directly. Two conventions:

- A checkbox is preceded by a hidden input of the same name with value
  ``false``; the last submitted value wins.
- The gas table is a matrix: ``gas_component_<j>`` names row ``j`` and
  ``gas_fraction_<i>_<j>`` holds gas ``i``'s mol % for that row. It is
  rebuilt into the legacy ``gas_compositions_table`` layout.
"""

import difflib
import math
import re

import ccp
from ccp_web.services import gas, schemas, units

_FRACTION = re.compile(r"^gas_fraction_(\d+)_(\d+)$")
_COMPONENT = re.compile(r"^gas_component_(\d+)$")
_GAS_NAME = re.compile(r"^gas_(\d+)$")

# Per-page updates that follow a state change, ``{app_type: hook(old, new) ->
# {key: value}}``. Registered by the page apps (``AppConfig.ready``) and run
# after both form saves and agent writes, so the two paths end in the same
# state (e.g. switching the flow method keeps the measured flows aside).
POST_SAVE_HOOKS = {}


def register_post_save_hook(app_types, hook):
    """Run ``hook(old_state, new_state) -> updates`` after saves of these types."""
    for app_type in app_types:
        POST_SAVE_HOOKS[app_type] = hook


def run_post_save_hooks(app_type, old, new):
    """``new`` with the page's post-save updates merged in."""
    hook = POST_SAVE_HOOKS.get(app_type)
    if hook is None:
        return new
    updates = hook(old, new)
    if not updates:
        return new
    return {**new, **updates}


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


def base_revision(request):
    """The case revision the submitting page was rendered at (``X-CCP-Rev``).

    None when the header is missing or malformed: the request then skips the
    stale-form guard, as before the agent API existed.
    """
    raw = request.headers.get("X-CCP-Rev")
    try:
        value = int(str(raw).strip())
    except (TypeError, ValueError):
        return None
    return value if value >= 0 else None


def _without_stale_keys(data, keys):
    """A copy of the submission without the keys an agent changed since."""
    data = data.copy()
    gas_table = "gas_compositions_table" in keys
    for key in list(data.keys()):
        if key in keys or (
            gas_table
            and (_COMPONENT.match(key) or _FRACTION.match(key) or _GAS_NAME.match(key))
        ):
            data.pop(key)
    return data


def save_post(case, data, base_revision=None):
    """Apply submitted fields to the stored state under a row lock.

    Re-reading the row keeps keys a job wrote meanwhile (curve names...).
    The page's post-save hooks (``POST_SAVE_HOOKS``) run in the same
    transaction.

    Stale-form guard: pages post the whole form, so a page rendered before
    an agent write would put the old values back. When ``base_revision`` (the
    case revision the page was rendered at) is older than the case's, the keys
    the agent changed since are dropped from the submission and
    ``case.stale`` is set; the view then asks the page to reload. Returns
    ``case`` with ``case.stale`` set either way.
    """
    from django.db import transaction

    from .models import Case

    case.stale = False
    if not data and base_revision is None:
        return case
    with transaction.atomic():
        fresh = Case.objects.select_for_update().get(pk=case.pk)
        if base_revision is not None and base_revision < fresh.revision:
            from ccp_web.agent.revisions import stale_keys

            case.stale = True
            data = _without_stale_keys(data, stale_keys(fresh, base_revision))
        if data:
            old = fresh.state
            new = apply_post(fresh.app_type, old, data)
            fresh.state = run_post_save_hooks(fresh.app_type, old, new)
            fresh.save(update_fields=["state", "updated"])
    case.state = fresh.state
    case.updated = fresh.updated
    case.revision = fresh.revision
    return case


def update_state(case, **values):
    """Merge values into the stored state under a row lock."""
    return merge_state(case, values)


def merge_state(case, values, unless_changed_from=None, touch=True):
    """Merge ``values`` into the stored state under a row lock.

    ``unless_changed_from``: a state snapshot; a key whose stored value
    differs from it (someone else changed it since the snapshot) is kept.
    Jobs pass the state they started from, so a value an agent or the user
    wrote during a run survives the job's own updates. ``touch=False`` keeps
    ``Case.updated``, for view settings that are not inputs (it tells
    whether the inputs changed after a calculation).
    """
    from django.db import transaction

    from .models import Case

    with transaction.atomic():
        fresh = Case.objects.select_for_update().get(pk=case.pk)
        state = dict(fresh.state)
        if unless_changed_from is not None:
            values = {
                k: v
                for k, v in values.items()
                if state.get(k) == unless_changed_from.get(k)
            }
        state.update(values)
        fresh.state = state
        fresh.save(update_fields=["state", "updated"] if touch else ["state"])
        if not touch:
            fresh.refresh_from_db(fields=["updated"])
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


# --------------------------------------------------------------------------
# Agent writes: JSON values, validated loudly
# --------------------------------------------------------------------------

# Keys an agent may send that are not state keys.
GAS_CONVENIENCE_KEY = "gas"
_UNIT_KEY = re.compile(r"_units?(_|$)")
_TRUE = {"true", "1", "yes", "on"}
_FALSE = {"false", "0", "no", "off"}


class ValuesError(ValueError):
    """Rejected agent values: ``details`` holds ``unknown`` and ``invalid``.

    ``unknown`` maps each unknown key to close schema keys; ``invalid`` maps
    each key to a message. Agents get the whole list at once, unlike forms,
    which silently ignore what they do not know.
    """

    def __init__(self, unknown=None, invalid=None):
        self.unknown = dict(unknown or {})
        self.invalid = dict(invalid or {})
        self.details = {}
        if self.unknown:
            self.details["unknown"] = self.unknown
        if self.invalid:
            self.details["invalid"] = self.invalid
        parts = []
        if self.unknown:
            parts.append("unknown key(s): " + ", ".join(self.unknown))
        if self.invalid:
            parts.append("invalid value(s): " + ", ".join(self.invalid))
        super().__init__("; ".join(parts) or "invalid values")


def _dimensionality(value):
    """The pint dimensionality of unit ``value``, or None when it does not parse."""
    try:
        return ccp.Q_(1, value).dimensionality
    except Exception:
        pass
    try:  # 'barg' only exists inside a calculation context
        with units.calculation_context():
            return ccp.Q_(1, value).dimensionality
    except Exception:
        return None


def _parses_as_unit(value):
    return _dimensionality(value) is not None


_dimensions_cache = {}


def _field_dimensions(f):
    """Dimensionalities of a unit field's options (flow takes mass and volume)."""
    key = (f.key, f.options)
    if key not in _dimensions_cache:
        found = {_dimensionality(o) for o in f.options if o}
        _dimensions_cache[key] = frozenset(d for d in found if d is not None)
    return _dimensions_cache[key]


_unit_field_cache = {}


def is_unit_field(f):
    """Whether a select holds a pint unit (any parseable unit is accepted).

    Mirrors ``schemas.coerce``, which keeps legacy unit strings the options
    do not list. A select of other choices (tappings, flow method, fluid
    fraction units such as ``mol_frac``) is strict. The first option decides,
    since not every listed unit parses (``lbm/h``).
    """
    if f.kind != "select":
        return False
    key = (f.key, f.options)
    if key not in _unit_field_cache:
        options = [o for o in f.options if o]
        _unit_field_cache[key] = bool(_UNIT_KEY.search(f.key)) and (
            not options or _parses_as_unit(options[0])
        )
    return _unit_field_cache[key]


def _number_text(value):
    """``(text, error)`` for a value meant as a number kept as a string."""
    if isinstance(value, bool):
        return None, "expected a number, got a boolean"
    if isinstance(value, (int, float)):
        if isinstance(value, float) and not math.isfinite(value):
            return None, "expected a finite number"
        return str(value), None
    if value is None:
        return "", None
    if not isinstance(value, str):
        return None, f"expected a number, got {type(value).__name__}"
    text = value.strip()
    if text == "":
        return "", None
    try:
        number = float(text)
    except ValueError:
        if "," in text:
            return None, f"'{value}' is not a number; use '.' as decimal separator"
        return None, f"'{value}' is not a number"
    if not math.isfinite(number):
        return None, "expected a finite number"
    return text, None


def _check_value(f, value):
    """``(stored value, error, warning)`` for one agent value of field ``f``."""
    kind = f.kind
    if kind == "text":
        text, error = _number_text(value)
        return text, error, None
    if kind == "number":
        if value is None or (isinstance(value, str) and value.strip() == ""):
            return f.default, None, None
        text, error = _number_text(value)
        if error:
            return None, error, None
        return schemas.coerce(f, text), None, None
    if kind == "bool":
        if isinstance(value, bool):
            return value, None, None
        if isinstance(value, (int, float)) and value in (0, 1):
            return bool(value), None, None
        if isinstance(value, str) and value.strip().lower() in _TRUE | _FALSE:
            return value.strip().lower() in _TRUE, None, None
        return None, f"expected true or false, got {value!r}", None
    if kind == "select":
        if not isinstance(value, (str, int, float)) or isinstance(value, bool):
            return None, f"expected one of {list(f.options)}", None
        text = str(value).strip()
        if not f.options or text in f.options:
            return text, None, None
        dimension = _dimensionality(text) if is_unit_field(f) and text else None
        if dimension is not None:
            expected = _field_dimensions(f)
            if expected and dimension not in expected:
                # Refused now: the calculation would fail on it later.
                return (
                    None,
                    f"unit '{text}' has dimension {dimension}, expected "
                    + " or ".join(sorted(str(d) for d in expected)),
                    None,
                )
            return (
                text,
                None,
                f"{f.key}: unit '{text}' is not one of the page's options",
            )
        options = [o for o in f.options]
        if is_unit_field(f):
            return (
                None,
                f"'{text}' is not a unit pint understands; e.g. {options}",
                None,
            )
        return None, f"'{text}' is not one of {options}", None
    if kind in ("string", "gas"):
        if value is None:
            return "", None, None
        if isinstance(value, (dict, list)) or isinstance(value, bool):
            return None, f"expected a string, got {type(value).__name__}", None
        return str(value), None, None
    return value, None, None


def _component_names():
    return {name.lower(): name for name in gas.fluid_list() if name}


def _gas_index(key):
    """Index of a gas named ``gas_<i>`` or ``<i>``, or None."""
    m = _GAS_NAME.match(str(key))
    text = m.group(1) if m else str(key)
    if text.isdigit() and int(text) < gas.N_GASES:
        return int(text)
    return None


def _composition_rows(composition, where, invalid):
    """Legacy ``component_j`` / ``molar_fraction_j`` items from ``{name: frac}``."""
    known = _component_names()
    entry = {}
    if not isinstance(composition, dict):
        invalid[where] = "composition must be an object {component: mol fraction}"
        return entry
    for j, (component, fraction) in enumerate(composition.items()):
        name = known.get(str(component).strip().lower())
        if name is None:
            close = difflib.get_close_matches(str(component).lower(), list(known), 3)
            invalid[f"{where}.{component}"] = f"unknown component; close: {close}"
            continue
        text, error = _number_text(fraction)
        if error or text == "":
            invalid[f"{where}.{component}"] = error or "missing fraction"
            continue
        entry[f"component_{j}"] = name
        entry[f"molar_fraction_{j}"] = float(text)
    return entry


def _apply_gas_table(new, table, invalid):
    """Replace the gases given in a legacy-layout table, gas by gas."""
    if not isinstance(table, dict):
        invalid["gas_compositions_table"] = "expected an object keyed gas_0..gas_5"
        return set()
    current = dict(new.get("gas_compositions_table") or {})
    touched = set()
    for key, entry in table.items():
        i = _gas_index(key)
        if i is None or not isinstance(entry, dict):
            invalid[f"gas_compositions_table.{key}"] = (
                "expected gas_0..gas_5 mapped to {name, component_j, molar_fraction_j}"
            )
            continue
        rows = {}
        for j, (component, fraction) in enumerate(gas.rows(entry)):
            if component:
                rows[component] = fraction
        converted = _composition_rows(rows, f"gas_compositions_table.{key}", invalid)
        name = entry.get("name") or new.get(f"gas_{i}") or f"gas_{i}"
        current[f"gas_{i}"] = {"name": str(name), **converted}
        new[f"gas_{i}"] = str(name)
        touched.add(i)
    new["gas_compositions_table"] = current
    return touched


def _apply_gas_convenience(new, value, invalid):
    """``{"gas_0": {"name": ..., "composition": {component: fraction}}}``."""
    if not isinstance(value, dict):
        invalid[GAS_CONVENIENCE_KEY] = (
            'expected {"gas_0": {"name": "...", "composition": {"methane": 0.9}}}'
        )
        return set()
    current = dict(new.get("gas_compositions_table") or {})
    touched = set()
    for key, spec in value.items():
        i = _gas_index(key)
        where = f"{GAS_CONVENIENCE_KEY}.{key}"
        if i is None or not isinstance(spec, dict):
            invalid[where] = "expected gas_0..gas_5 mapped to {name?, composition?}"
            continue
        unknown = set(spec) - {"name", "composition"}
        if unknown:
            invalid[where] = f"unknown entries {sorted(unknown)}; use name, composition"
            continue
        entry = dict(current.get(f"gas_{i}") or {})
        if "composition" in spec:
            rows = _composition_rows(spec["composition"], where, invalid)
            entry = {k: v for k, v in entry.items() if k == "name"} | rows
        if spec.get("name"):
            entry["name"] = str(spec["name"]).strip()
            new[f"gas_{i}"] = entry["name"]
        current[f"gas_{i}"] = entry
        touched.add(i)
    new["gas_compositions_table"] = current
    return touched


def apply_values(app_type, state, values):
    """Return ``(new_state, warnings)`` with JSON values from an agent applied.

    The agent counterpart of ``apply_post``: the same coercion and
    normalisation, but every key and value is validated and the whole
    request is rejected with ``ValuesError`` when any is wrong. Besides the
    state keys, ``gas`` takes ``{"gas_0": {"name", "composition"}}``. A gas
    renamed here is renamed in the selects that used it.
    """
    schema = schemas.get_schema(app_type)
    if not isinstance(values, dict):
        raise ValuesError(invalid={"values": "expected an object {key: value}"})
    unknown = {}
    invalid = {}
    warnings = []
    new = dict(state)
    old_names = gas.gas_names(state)
    for key, value in values.items():
        if key == GAS_CONVENIENCE_KEY:
            continue
        f = schema.fields.get(key)
        if f is None:
            unknown[key] = difflib.get_close_matches(
                key, list(schema.fields) + [GAS_CONVENIENCE_KEY], n=5, cutoff=0.6
            )
            continue
        if f.kind == "json":
            continue
        stored, error, warning = _check_value(f, value)
        if error:
            invalid[key] = error
            continue
        if warning:
            warnings.append(warning)
        new[key] = stored
    if "gas_compositions_table" in values:
        if "gas_compositions_table" not in schema.fields:
            unknown["gas_compositions_table"] = []
        else:
            _apply_gas_table(new, values["gas_compositions_table"], invalid)
    if GAS_CONVENIENCE_KEY in values:
        if "gas_compositions_table" not in schema.fields:
            unknown[GAS_CONVENIENCE_KEY] = []
        else:
            _apply_gas_convenience(new, values[GAS_CONVENIENCE_KEY], invalid)
    if unknown or invalid:
        raise ValuesError(unknown, invalid)
    for i in range(gas.N_GASES):
        # An explicit ``gas_<i>`` wins over a name inside the table.
        if f"gas_{i}" in values and f"gas_{i}" in schema.fields:
            new[f"gas_{i}"] = str(values[f"gas_{i}"] or f"gas_{i}").strip()

    names = gas.gas_names(new)
    if len(set(names)) != len(names):
        raise ValuesError(invalid={"gas_names": f"gas names must be unique: {names}"})
    renamed = {
        old: name
        for old, name in zip(old_names, names)
        if old != name and old not in names
    }
    for key, f in schema.fields.items():
        if f.kind != "gas":
            continue
        if key in values:
            if new.get(key) not in names:
                invalid[key] = f"'{new.get(key)}' is not a defined gas; one of {names}"
        elif new.get(key) in renamed:
            new[key] = renamed[new[key]]
    if invalid:
        raise ValuesError(invalid=invalid)

    if "gas_compositions_table" in values or GAS_CONVENIENCE_KEY in values:
        for i, name in enumerate(names):
            entry = (new.get("gas_compositions_table") or {}).get(f"gas_{i}") or {}
            total = sum(fraction for _, fraction in gas.rows(entry))
            if total and not (abs(total - 100) < 0.5 or abs(total - 1) < 0.005):
                warnings.append(
                    f"gas '{name}' fractions add up to {total:g}; "
                    "expected 100 (mol %) or 1 (mol fraction)"
                )
    return schemas.normalize(app_type, new), warnings
