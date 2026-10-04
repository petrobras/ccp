"""Read and write ``.ccp`` session files.

A ``.ccp`` file is a zip archive written by the Streamlit app:

- ``ccp.version``: version string (missing in files older than 0.3.6).
- ``session_state.json``: flat dump of the widget keys.
- ``fig_<curve>[_secN].png``: curve images (performance test pages).
- ``straight_through.toml`` / ``back_to_back.toml``: ``to_dict()`` results.
- ``impeller_case_<X>.toml``, ``converted_impeller.toml``: impellers.
- Engauge CSVs, either ``case_<X>/<original name>.csv`` or the legacy
  ``curves_file_<N>_case_<X>.csv``.
- ``evaluation.zip``: ``ccp.Evaluation.save`` output.
- Curves digitizer (web app only): the vendor PDF at the root and
  ``digitized.json`` / ``digitized_original.json`` (edited and original
  digitization).

``read_ccp`` returns plain data; ``write_ccp`` produces a file the Streamlit
loaders accept.
"""

import io
import json
import re
import zipfile
from dataclasses import dataclass, field

import toml
from packaging.version import InvalidVersion, Version

import ccp

from . import schemas

APP_TYPES = [
    "straight_through",
    "back_to_back",
    "curves_conversion",
    "performance_evaluation",
    "curves_digitizer",
]

DIGITIZER_ARTIFACTS = ("digitized", "digitized_original")

RESULT_TOML_KEYS = {
    "straight_through": "straight_through",
    "back_to_back": "back_to_back",
}


class CcpFileError(ValueError):
    pass


@dataclass
class CcpFile:
    """Contents of a ``.ccp`` archive.

    ``files`` maps a case-file key to ``(kind, name, bytes)``; ``artifacts``
    maps an artifact key to ``(name, bytes)``.
    """

    app_type: str
    version: str
    state: dict
    files: dict = field(default_factory=dict)
    artifacts: dict = field(default_factory=dict)


def _parse_version(text):
    try:
        return Version(text)
    except InvalidVersion:
        return Version("0.3.5")


def migrate_state(data, version):
    """Port of ``common.convert`` for the session dict.

    Before 0.3.7 the gas table was stored as flat ``gas_i_component_j`` and
    ``gas_i_molar_fraction_j`` keys.
    """
    if _parse_version(version) >= Version("0.3.7"):
        return data
    data = dict(data)
    gas_list = set()
    for key in data:
        if key.startswith("gas"):
            try:
                gas_list.add(f"gas_{int(key.split('_')[1])}")
            except (ValueError, IndexError):
                continue
    table = {}
    for gas_key in sorted(gas_list):
        table[gas_key] = {}
        for k, v in list(data.items()):
            if k.startswith(gas_key) and "component" in k:
                table[gas_key][f"component_{k.split('_')[-1]}"] = v
                del data[k]
            elif k.startswith(gas_key) and "molar_fraction" in k:
                table[gas_key][f"molar_fraction_{k.split('_')[-1]}"] = v
                del data[k]
    if table and all(table.values()):
        data["gas_compositions_table"] = table
    return data


def migrate_result_toml(text, version):
    """Port of ``common.convert`` for result TOML.

    ``speed`` became ``speed_operational`` in 0.3.6.
    """
    if _parse_version(version) >= Version("0.3.6"):
        return text
    parsed = toml.loads(text)
    renamed = {
        ("speed_operational" if k == "speed" else k): v for k, v in parsed.items()
    }
    return toml.dumps(renamed)


def detect_app_type(raw_state, names):
    """Infer the page a file belongs to.

    ``app_type`` in the JSON is unreliable (the back-to-back example says
    ``straight_through``), so the content decides first.
    """
    if "div_wall_flow_m_section_1_point_1" in raw_state or "back_to_back.toml" in names:
        return "back_to_back"
    if "flow_point_guarantee" in raw_state or "straight_through.toml" in names:
        return "straight_through"
    declared = raw_state.get("app_type")
    if declared == "curves_digitizer" or "digitized.json" in names:
        return "curves_digitizer"
    if "evaluation.zip" in names or declared in (
        "performance_evaluation",
        "online_monitoring",
    ):
        return "performance_evaluation"
    if declared == "curves_conversion" or "converted_impeller.toml" in names:
        return "curves_conversion"
    if any(k.startswith("pi_server_name") or k.endswith("_tag") for k in raw_state):
        return "performance_evaluation"
    if any(n.startswith("impeller_case_") for n in names) or any(
        k.startswith("suc_p_case_") for k in raw_state
    ):
        return "curves_conversion"
    raise CcpFileError("Could not determine which page this .ccp file belongs to.")


def _max_y(content):
    """Largest y value of an Engauge CSV (``x,<speed>`` header, x,y rows)."""
    values = []
    for line in content.decode("utf-8", errors="replace").splitlines()[1:]:
        parts = [
            p.strip().strip('"')
            for p in re.split(r',(?=(?:[^"]*"[^"]*")*[^"]*$)', line)
        ]
        if len(parts) < 2 or not parts[1]:
            continue
        try:
            values.append(float(parts[1].replace(",", ".")))
        except ValueError:
            continue
    return max(values) if values else None


def _legacy_curve_kind(content, other, file_num):
    mine = _max_y(content)
    theirs = _max_y(other) if other else None
    if mine is not None and theirs is not None:
        if mine <= 1.0 < theirs:
            return "eff"
        if theirs <= 1.0 < mine:
            return "head"
    return "head" if file_num == "1" else "eff"


_LEGACY_CSV = re.compile(r"^curves_file_(\d)_case_([A-Z])\.csv$")
_CASE_CSV = re.compile(r"^case_([A-Z])/(.+\.csv)$")


def read_ccp(data, expected_app_type=None):
    """Parse ``.ccp`` bytes.

    Parameters
    ----------
    data : bytes or file-like
        The archive.
    expected_app_type : str, optional
        Raise ``CcpFileError`` if the file belongs to another page.
    """
    if isinstance(data, (bytes, bytearray)):
        data = io.BytesIO(data)
    try:
        archive = zipfile.ZipFile(data)
    except zipfile.BadZipFile as exc:
        raise CcpFileError("Not a .ccp file (not a zip archive).") from exc

    with archive:
        names = archive.namelist()
        try:
            version = archive.read("ccp.version").decode("utf-8").strip()
        except KeyError:
            version = "0.3.5"

        raw_state = {}
        json_names = [n for n in names if n.endswith(".json")]
        if "session_state.json" in json_names:
            json_names.remove("session_state.json")
            json_names.insert(0, "session_state.json")
        if json_names:
            raw_state = json.loads(archive.read(json_names[0]))
        raw_state = migrate_state(raw_state, version)

        app_type = detect_app_type(raw_state, names)
        if expected_app_type and app_type != expected_app_type:
            raise CcpFileError(
                f"File is a {app_type.replace('_', ' ')} file, "
                f"not {expected_app_type.replace('_', ' ')}."
            )

        files = {}
        artifacts = {}
        legacy = {}
        for name in names:
            base = name.rsplit("/", 1)[-1]
            if name.endswith(".png") and "/" not in name:
                key = base[: -len(".png")]
                files[key] = ("curve_image", base, archive.read(name))
            elif name.endswith(".csv"):
                m_case = _CASE_CSV.match(name)
                m_legacy = _LEGACY_CSV.match(name)
                if m_case:
                    case, original = m_case.groups()
                    key = f"curves_file_1_case_{case}"
                    if key in files:
                        key = f"curves_file_2_case_{case}"
                    files[key] = ("engauge_csv", original, archive.read(name))
                elif m_legacy:
                    file_num, case = m_legacy.groups()
                    legacy[(case, file_num)] = archive.read(name)
            elif name.endswith(".toml"):
                key = base[: -len(".toml")]
                text = archive.read(name).decode("utf-8")
                if key in RESULT_TOML_KEYS:
                    text = migrate_result_toml(text, version)
                artifacts[key] = (base, text.encode("utf-8"))
            elif name == "evaluation.zip":
                artifacts["evaluation"] = ("evaluation.zip", archive.read(name))
            elif name.lower().endswith(".pdf") and "/" not in name:
                files["curve_pdf"] = ("curve_pdf", base, archive.read(name))
            elif name in (f"{k}.json" for k in DIGITIZER_ARTIFACTS):
                artifacts[base[: -len(".json")]] = (base, archive.read(name))

    for (case, file_num), content in legacy.items():
        # The original Engauge name is lost. Rebuild it from the curve name so
        # the curves can be loaded again; head or eff comes from the values
        # when they tell (efficiency as a fraction), else from the Streamlit
        # convention file 1 = head, file 2 = eff.
        curve_name = raw_state.get(f"curve_name_case_{case}") or f"case-{case.lower()}"
        other = legacy.get((case, "2" if file_num == "1" else "1"))
        suffix = _legacy_curve_kind(content, other, file_num)
        files[f"curves_file_{file_num}_case_{case}"] = (
            "engauge_csv",
            f"{curve_name}-{suffix}.csv",
            content,
        )

    state = schemas.normalize(app_type, raw_state)
    return CcpFile(
        app_type=app_type,
        version=version,
        state=state,
        files=files,
        artifacts=artifacts,
    )


def export_state(app_type, state):
    """The ``session_state.json`` dict written for a case."""
    schema = schemas.get_schema(app_type)
    out = {}
    for key, f in schema.fields.items():
        if not f.export:
            continue
        out[key] = state.get(key, f.default)
    out["app_type"] = app_type
    out["ccp_version"] = ccp.__version__
    # Streamlit page state that its loaders expect to exist.
    if app_type in ("straight_through", "back_to_back"):
        out["expander_state"] = True
    return out


def write_ccp(app_type, state, files=(), artifacts=()):
    """Build ``.ccp`` bytes.

    Parameters
    ----------
    files : iterable of (key, kind, name, bytes)
    artifacts : iterable of (key, name, bytes)
    """
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("ccp.version", ccp.__version__)
        # File 1 before file 2: readers assign the case_<X>/ CSVs in order.
        for key, kind, name, content in sorted(files, key=lambda f: f[0]):
            if kind == "curve_image":
                archive.writestr(f"{key}.png", content)
            elif kind == "engauge_csv":
                m = re.match(r"curves_file_\d_case_([A-Z])$", key)
                if m:
                    archive.writestr(f"case_{m.group(1)}/{name}", content)
            elif kind == "curve_pdf":
                archive.writestr(name.rsplit("/", 1)[-1], content)
        for key, name, content in artifacts:
            if key == "evaluation":
                archive.writestr("evaluation.zip", content)
            elif name.endswith(".toml"):
                archive.writestr(f"{key}.toml", content)
            elif key in DIGITIZER_ARTIFACTS:
                archive.writestr(f"{key}.json", content)
        archive.writestr(
            "session_state.json", json.dumps(export_state(app_type, state))
        )
    return buffer.getvalue()
