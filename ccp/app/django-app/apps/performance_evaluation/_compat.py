"""Cross-unit import shim.

Prefers the real ``apps.core.*`` and ``apps.integrations.*`` modules when they
exist; falls back to local stubs otherwise so this app stays runnable in
isolation while Units 2/3/4/11 are still in flight.
"""

from __future__ import annotations

try:
    from apps.core.services import unit_helpers
except ImportError:  # pragma: no cover - exercised on merged tree
    from ._stubs import unit_helpers  # type: ignore[no-redef]

try:
    from apps.core.services import gas_composition
except ImportError:
    from ._stubs import gas_composition  # type: ignore[no-redef]

try:
    from apps.core.services import parameter_map
except ImportError:
    from ._stubs import parameter_map  # type: ignore[no-redef]

try:
    from apps.core import session_store
except ImportError:
    from ._stubs import session_store  # type: ignore[no-redef]

try:
    from apps.integrations import pi_client
except ImportError:
    from ._stubs import pi_client  # type: ignore[no-redef]

try:
    from apps.core.storage import ccp_file_importer, ccp_file_exporter

    load_ccp_file = ccp_file_importer.load_ccp_file
    export_ccp_file = ccp_file_exporter.export_ccp_file
except ImportError:
    from ._stubs.ccp_file_io import load_ccp_file, export_ccp_file  # type: ignore[no-redef]


__all__ = [
    "unit_helpers",
    "gas_composition",
    "parameter_map",
    "session_store",
    "pi_client",
    "load_ccp_file",
    "export_ccp_file",
]
