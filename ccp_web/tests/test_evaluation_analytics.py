"""Evaluation page analytics: driver power inputs, KPI trends and tiles."""

import json
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from ccp_web.services import evaluation as ev
from ccp_web.services import plant_data, schemas
from ccp_web.services.units import InputError

from .conftest import import_case


def test_driver_power_state_keys():
    state = schemas.default_state("performance_evaluation")
    assert state["power_driver_tag"] == "" and state["power_driver_tag_2"] == ""
    assert state["power_driver_unit"] == "kW"
    assert state["transmission_efficiency"] == 1.0
    # old saved cases load: the new keys get their defaults
    old = {k: v for k, v in state.items() if "power_driver" not in k}
    old.pop("transmission_efficiency")
    assert schemas.normalize("performance_evaluation", old)["power_driver_unit"] == "kW"

    state.update(
        suc_p_tag="PT-1",
        power_driver_tag="JI-1",
        power_driver_unit="MW",
        transmission_efficiency=0.98,
        fluid_source="Inform Component Tags",
    )
    tm = plant_data.tag_mappings(state)
    assert tm["power_driver_tag"] == "JI-1"
    tags, rename, _ = plant_data.build_pi_query(tm)
    assert rename["JI-1"] == "power_driver"
    assert plant_data.data_units(state, tm)["power_driver"] == "MW"
    kwargs = ev.evaluation_kwargs(
        state, tm, impellers=[object()], df=pd.DataFrame(), parallel=False
    )
    assert kwargs["transmission_efficiency"] == 0.98
    assert kwargs["data_units"]["power_driver"] == "MW"

    with pytest.raises(InputError):
        ev.transmission_efficiency({"transmission_efficiency": 1.2})


def test_redundant_driver_power_tags_are_averaged():
    tm = {"power_driver_tag_2": "JI-2", "power_driver_unit": "kW"}
    tm["power_driver_unit_2"] = "MW"
    df = pd.DataFrame(
        {"power_driver": [1000.0, np.nan], "power_driver_2": [1.2, 1.1]},
        index=pd.date_range("2026-01-01", periods=2, freq="h"),
    )
    merged = plant_data.merge_redundant_parameter_tags(df, tm)
    assert list(merged.columns) == ["power_driver"]
    assert merged["power_driver"].tolist() == pytest.approx([1100.0, 1100.0])


def synthetic_results(days=60):
    """An ``Evaluation.df`` look-alike with the analytics columns."""
    rng = np.random.default_rng(0)
    index = pd.date_range("2026-01-01", periods=days * 6, freq="4h")
    t = np.arange(len(index)) / len(index)
    wash = np.where(np.arange(len(index)) >= len(index) // 2, 1.5, 0.0)
    df = pd.DataFrame(
        {
            "delta_eff": -3 * t + wash + rng.normal(0, 0.2, len(index)),
            "delta_head": -1.0 * t + rng.normal(0, 0.2, len(index)),
            "flow_dev": rng.normal(-0.5, 0.2, len(index)),
            "delta_Td": rng.normal(0.3, 0.1, len(index)),
            "health_index": 1 + rng.normal(0, 0.002, len(index)),
            "delta_power_balance": rng.normal(1.0, 0.3, len(index)),
            "power_coupling": 5e6,
            "power_shaft": 4.95e6,
            "valid": True,
            "cluster": 0,
        },
        index=index,
    )
    for c in ("eff", "head", "power", "flow_v", "flow_m"):
        df[c] = 1.0
    return df


def test_analyse_adds_trends_and_table_columns():
    from ccp.analytics.trends import analyse_trends

    df = synthetic_results()
    evaluation = SimpleNamespace(
        df=df,
        impellers_new=[],
        trends=lambda kpis=None, **kw: analyse_trends(df, kpis=kpis, **kw),
    )
    analysis, table = ev.analyse(evaluation, {})
    for column in ("flow_dev", "delta_Td", "delta_power_balance", "power_coupling"):
        assert column in table.columns
    json.dumps(analysis)  # stored as JSON
    trends = analysis["trends"]
    assert set(trends["trends"]) == set(ev.TREND_KPIS)
    assert set(trends["figures"]) == set(ev.TREND_KPIS)
    eff = trends["trends"]["delta_eff"]
    assert any(c["kind"] == "recovery" for c in eff["change_points"])

    tiles = {t["kpi"]: t for t in ev.kpi_tiles(analysis)}
    assert tiles["delta_eff"]["change"]["kind"] == "recovery"
    assert tiles["delta_eff"]["slope_range"].startswith("[")
    assert tiles["delta_eff"]["time_to"] is not None  # threshold -2 points
    assert tiles["delta_Td"]["time_to"] is None  # no default threshold
    assert tiles["health_index"]["figure"]["data"]


def test_trend_failure_is_reported():
    def broken(**kw):
        raise ValueError("boom")

    evaluation = SimpleNamespace(df=synthetic_results(10), trends=broken)
    assert ev.trend_analysis(evaluation) == {"error": "ValueError: boom"}
    assert ev.kpi_tiles({"trends": {"error": "x"}}) == []


@pytest.mark.django_db
def test_evaluation_page_analytics(web, example):
    case, url = import_case(web, example("example_evaluation_pi.ccp"))
    body = web.get(url).content.decode()
    assert "Driver shaft power" in body and 'name="transmission_efficiency"' in body
    analysis = json.loads(case.artifact("evaluation_analysis").read())
    # the example was saved before the analytics columns: the KPIs present
    assert {"delta_eff", "delta_head"} <= set(analysis["trends"]["trends"])
    results = web.get(f"/evaluation/{case.pk}/results/").content.decode()
    assert "Health KPIs" in results and "/1000 h" in results

    web.post(
        f"/cases/{case.pk}/state/",
        {"power_driver_tag": "JI-1", "power_driver_unit": "MW"},
    )
    case.refresh_from_db()
    assert case.state["power_driver_tag"] == "JI-1"
    assert case.state["power_driver_unit"] == "MW"
