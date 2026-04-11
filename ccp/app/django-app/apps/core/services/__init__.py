"""Pure-Python service layer wrapping the ``ccp`` library for Django views.

Nothing in this package touches Django's ORM, request/response cycle, or the
Streamlit runtime. Each submodule can be imported and exercised in isolation.
"""

from apps.core.services import (
    ccp_service,
    gas_composition,
    parameter_map,
    polytropic_methods,
    unit_helpers,
)

__all__ = [
    "ccp_service",
    "gas_composition",
    "parameter_map",
    "polytropic_methods",
    "unit_helpers",
]
