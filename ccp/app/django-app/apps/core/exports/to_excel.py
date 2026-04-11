"""Excel export for ccp session state.

Ports :func:`ccp.app.common.to_excel` (a thin pandas wrapper that only
produced a single-sheet workbook from a DataFrame) into a richer
``session_to_excel`` that serialises the whole session into a workbook
mirroring the sheet layout downloaded by the Streamlit app. Portuguese
sheet and column names are preserved.
"""

from __future__ import annotations

import io
from typing import Any, Iterable, Mapping

import pandas as pd


SHEET_PARAMETROS = "Parametros"
SHEET_GARANTIA = "Ponto de Garantia"
SHEET_TESTE = "Pontos de Teste"
SHEET_RESULTADOS = "Resultados"
SHEET_GRAFICOS = "Graficos"


def session_to_excel(state: Mapping[str, Any]) -> bytes:
    """Serialize a session state dictionary to an ``.xlsx`` workbook.

    The workbook contains up to five sheets (all in Portuguese to match
    the Streamlit download):

    - ``Parametros`` -- scalar parameters from the session.
    - ``Ponto de Garantia`` -- guarantee-point inputs.
    - ``Pontos de Teste`` -- test-point inputs.
    - ``Resultados`` -- a pre-computed results DataFrame, when present.
    - ``Graficos`` -- references (not binary) to plot payloads stored
      in the session so the file stays portable without embedded PNGs.

    Parameters
    ----------
    state : Mapping[str, Any]
        Session state dictionary. Missing keys are silently skipped; an
        empty state still produces a valid (but minimal) workbook.

    Returns
    -------
    bytes
        The bytes of the generated ``.xlsx`` workbook.
    """
    buf = io.BytesIO()
    engine = _pick_engine()
    with pd.ExcelWriter(buf, engine=engine) as writer:
        _write_parameters_sheet(writer, state)
        _write_points_sheet(
            writer, SHEET_GARANTIA, _coerce_points(state.get("guarantee_point"))
        )
        _write_points_sheet(
            writer, SHEET_TESTE, _coerce_points(state.get("test_points"))
        )
        _write_results_sheet(writer, state)
        _write_plots_sheet(writer, state)
    return buf.getvalue()


def _pick_engine() -> str:
    """Return the first available pandas Excel engine.

    Prefers ``xlsxwriter`` (matching the original Streamlit helper),
    falling back to ``openpyxl``.
    """
    try:
        import xlsxwriter  # noqa: F401

        return "xlsxwriter"
    except ImportError:
        return "openpyxl"


def _write_parameters_sheet(writer: pd.ExcelWriter, state: Mapping[str, Any]) -> None:
    params = state.get("parameters") or state.get("parametros") or {}
    rows = []
    if isinstance(params, Mapping):
        for key, value in params.items():
            if isinstance(value, Mapping):
                rows.append(
                    {
                        "Parametro": key,
                        "Valor": value.get("value", value.get("valor")),
                        "Unidade": value.get("units", value.get("unidade")),
                    }
                )
            else:
                rows.append({"Parametro": key, "Valor": value, "Unidade": None})
    for scalar_key in ("speed", "rotor_name", "tag", "case_name"):
        if scalar_key in state and not any(r["Parametro"] == scalar_key for r in rows):
            rows.append(
                {"Parametro": scalar_key, "Valor": state[scalar_key], "Unidade": None}
            )
    df = pd.DataFrame(rows or [{"Parametro": None, "Valor": None, "Unidade": None}])
    df.to_excel(writer, sheet_name=SHEET_PARAMETROS, index=False)


def _coerce_points(points: Any) -> list[dict[str, Any]]:
    """Normalise the many shapes a session may hold for points."""
    if points is None:
        return []
    if isinstance(points, Mapping):
        if all(isinstance(v, Mapping) for v in points.values()):
            return [{"Nome": k, **dict(v)} for k, v in points.items()]
        return [dict(points)]
    if isinstance(points, Iterable):
        out = []
        for item in points:
            if isinstance(item, Mapping):
                out.append(dict(item))
        return out
    return []


def _write_points_sheet(
    writer: pd.ExcelWriter, sheet: str, rows: list[dict[str, Any]]
) -> None:
    df = pd.DataFrame(rows) if rows else pd.DataFrame([{"Ponto": None}])
    df.to_excel(writer, sheet_name=sheet, index=False)


def _write_results_sheet(writer: pd.ExcelWriter, state: Mapping[str, Any]) -> None:
    results = state.get("results") or state.get("resultados")
    if isinstance(results, pd.DataFrame):
        df = results
    elif isinstance(results, Mapping):
        df = pd.DataFrame(results)
    elif isinstance(results, list):
        df = pd.DataFrame(results)
    else:
        df = pd.DataFrame([{"Resultado": None}])
    df.to_excel(writer, sheet_name=SHEET_RESULTADOS, index=False)


def _write_plots_sheet(writer: pd.ExcelWriter, state: Mapping[str, Any]) -> None:
    plots = state.get("plots") or state.get("graficos") or {}
    rows = []
    if isinstance(plots, Mapping):
        for name, payload in plots.items():
            rows.append(
                {
                    "Grafico": name,
                    "Tipo": type(payload).__name__,
                    "Tamanho (bytes)": len(payload)
                    if hasattr(payload, "__len__")
                    else None,
                }
            )
    df = pd.DataFrame(rows) if rows else pd.DataFrame([{"Grafico": None}])
    df.to_excel(writer, sheet_name=SHEET_GRAFICOS, index=False)
