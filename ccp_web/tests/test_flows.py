"""End-to-end flows through the Django views.

These mirror ``ccp/tests/test_app.py`` (the Streamlit AppTest flows): each
loads an example ``.ccp`` file, runs the page's calculation and checks the
resulting object. Jobs run inline (``ImmediateBackend``).
"""

import io
import json
import zipfile

import pytest

import ccp
from ccp.compressor import BackToBack, StraightThrough
from ccp_web.core.models import Artifact, Job
from ccp_web.services import ccpfile

from .conftest import import_case

pytestmark = pytest.mark.django_db


def last_job(case, kind):
    return Job.objects.filter(case=case, kind=kind).order_by("-pk").first()


# --------------------------------------------------------------------------
# Straight-through (test_app.TestStraightThrough)
# --------------------------------------------------------------------------


def test_straight_through_page_loads(web):
    response = web.get("/app/straight_through/", follow=True)
    assert response.status_code == 200
    assert b"Straight-through" in response.content


def test_straight_through_calculate(web, example):
    case, url = import_case(
        web, example("example_straight.ccp"), "example_straight.ccp"
    )
    assert url == f"/performance-test/{case.pk}/"
    assert web.get(url).status_code == 200

    response = web.post(f"/performance-test/{case.pk}/calculate/", {})
    assert response.status_code == 200
    job = last_job(case, "calculate")
    assert job.status == Job.SUCCEEDED, job.error

    artifact = case.artifact("straight_through")
    compressor = StraightThrough.from_dict(
        __import__("toml").loads(artifact.read_text())
    )
    assert isinstance(compressor, StraightThrough)
    assert compressor.speed_operational.to("rpm").m == pytest.approx(10098, rel=1e-6)

    results = web.get(f"/performance-test/{case.pk}/results/")
    assert results.status_code == 200
    assert "Guarantee Point" in results.content.decode()
    xlsx = web.get(f"/performance-test/{case.pk}/excel/st/")
    assert xlsx["Content-Disposition"].endswith('results.xlsx"')
    assert zipfile.is_zipfile(io.BytesIO(xlsx.content))


def test_straight_through_calculate_speed_matches_saved_result(web, example):
    """Calculate Speed reproduces the speed stored by the Streamlit app."""
    case, _ = import_case(web, example("example_straight.ccp"))
    saved = case.artifact("straight_through").read_text()
    reference = StraightThrough.from_dict(
        __import__("toml").loads(saved)
    ).speed_operational
    web.post(f"/performance-test/{case.pk}/calculate/", {"calculate_speed": "1"})
    job = last_job(case, "calculate")
    assert job.status == Job.SUCCEEDED, job.error
    assert job.result["speed_operational_rpm"] == pytest.approx(
        reference.to("rpm").m, rel=1e-3
    )


def test_straight_through_validation_errors(web):
    web.get("/app/straight_through/", follow=True)
    from ccp_web.core.models import Case

    case = Case.objects.get(app_type="straight_through")
    response = web.post(
        f"/performance-test/{case.pk}/calculate/", {"flow_point_guarantee": "1,5"}
    )
    body = response.content.decode()
    assert "Failed" in body and "flow_point_guarantee" in body
    assert "decimal separator" in body
    assert not Job.objects.filter(case=case).exists()  # rejected before any job


def test_orifice_flowrate(web, example):
    case, _ = import_case(web, example("example_straight.ccp"))
    reference = case.state["mass_flow_fo_1"]
    response = web.post(f"/performance-test/{case.pk}/orifice/", {"mass_flow_fo_1": ""})
    assert response.status_code == 200
    case.refresh_from_db()
    assert float(case.state["mass_flow_fo_1"]) == pytest.approx(
        float(reference), rel=1e-4
    )


# --------------------------------------------------------------------------
# Back-to-back (test_app.TestBackToBack)
# --------------------------------------------------------------------------


def test_back_to_back_calculate(web, example):
    case, url = import_case(web, example("example_back_to_back.ccp"))
    assert case.app_type == "back_to_back"
    assert web.get(url).status_code == 200
    web.post(f"/performance-test/{case.pk}/calculate/", {})
    job = last_job(case, "calculate")
    assert job.status == Job.SUCCEEDED, job.error
    compressor = BackToBack.from_dict(
        __import__("toml").loads(case.artifact("back_to_back").read_text())
    )
    assert isinstance(compressor, BackToBack)
    body = web.get(f"/performance-test/{case.pk}/results/").content.decode()
    assert "Overall" in body and "Second Section" in body
    assert web.get(f"/performance-test/{case.pk}/excel/sec2/").status_code == 200


# --------------------------------------------------------------------------
# Curves conversion (test_app.TestCurvesConversion)
# --------------------------------------------------------------------------


def test_curves_convert(web, example):
    case, url = import_case(web, example("curves-conversion-example.ccp"))
    assert case.app_type == "curves_conversion"
    assert web.get(url).status_code == 200
    web.post(f"/curves/{case.pk}/convert/", {})
    job = last_job(case, "convert_curves")
    assert job.status == Job.SUCCEEDED, job.error
    converted = ccp.Impeller.from_dict(
        __import__("toml").loads(case.artifact("converted_impeller").read_text())
    )
    assert len(converted.points) > 0
    panel = web.get(f"/curves/{case.pk}/plots/converted/")
    assert panel.status_code == 200 and "Converted point" in panel.content.decode()
    # Changing the operating point re-renders the panel.
    panel = web.post(
        f"/curves/{case.pk}/plots/converted/", {"converted_speed_input": "10000"}
    )
    case.refresh_from_db()
    assert case.state["converted_speed_input"] == 10000


def test_curves_load_design_case(web, example):
    """test_app.TestPerformanceEvaluation: Load Curves for Case A."""
    case, _ = import_case(web, example("example_evaluation_pi.ccp"))
    Artifact.objects.filter(case=case, key="impeller_case_A").delete()
    web.post(f"/curves/{case.pk}/load/A/", {})
    job = last_job(case, "load_curves")
    assert job.status == Job.SUCCEEDED, job.error
    impeller = ccp.Impeller.from_dict(
        __import__("toml").loads(case.artifact("impeller_case_A").read_text())
    )
    assert len(impeller.points) > 0
    case.refresh_from_db()
    assert case.state["curve_name_case_A"] == "case-a"


def test_curves_convert_needs_a_design_case(web):
    web.get("/app/curves_conversion/", follow=True)
    from ccp_web.core.models import Case

    case = Case.objects.get(app_type="curves_conversion")
    body = web.post(f"/curves/{case.pk}/convert/", {}).content.decode()
    assert "Failed" in body and "load at least one design case" in body


# --------------------------------------------------------------------------
# Performance evaluation (test_app.TestPerformanceEvaluation)
# --------------------------------------------------------------------------


def test_evaluation_imported_analysis_report_and_monitoring(web, example):
    case, url = import_case(web, example("example_evaluation_pi.ccp"))
    # Opening the page builds the plots of the imported evaluation.
    assert web.get(url).status_code == 200
    job = last_job(case, "analysis")
    assert job.status == Job.SUCCEEDED, job.error
    analysis = json.loads(case.artifact("evaluation_analysis").read())
    assert analysis["n_rows"] > 0 and len(analysis["trend"]) == 4
    case.refresh_from_db()
    assert case.state["eval_start"].startswith("2026-02")  # window from the data

    body = web.get(f"/evaluation/{case.pk}/results/").content.decode()
    assert "Trend analysis" in body
    perf = web.get(f"/evaluation/{case.pk}/perf/?cluster=1&similarity=0")
    assert perf.status_code == 200
    xlsx = web.get(f"/evaluation/{case.pk}/table.xlsx")
    assert zipfile.is_zipfile(io.BytesIO(xlsx.content))

    web.post(f"/evaluation/{case.pk}/report/", {})
    job = last_job(case, "report")
    assert job.status == Job.SUCCEEDED, job.error
    html = case.artifact("report").read_text()
    assert html.startswith("<!DOCTYPE html>") or "<html" in html[:500]

    # Online monitoring on mock data, two ticks.
    case.state = {**case.state, "data_source": "mock"}
    case.save()
    from ccp_web.core import jobs

    monitor = jobs.start_job(case, "monitoring", {"max_ticks": 1})
    monitor.refresh_from_db()
    assert monitor.status == Job.SUCCEEDED, monitor.error
    view = monitor.result["view"]
    assert len(view["metrics"]) == 4 and set(view["figures"]) == {
        "head",
        "eff",
        "power",
        "disch_p",
    }
    panel = web.get(f"/evaluation/{case.pk}/monitoring/")
    assert "Recent points" in panel.content.decode()


def test_evaluation_run_is_incremental(web, example):
    """Run with the saved window only appends; nothing new keeps the evaluation."""
    case, url = import_case(web, example("example_evaluation_pi.ccp"))
    web.get(url)
    case.state = {**case.state, "data_source": "mock"}
    case.save()
    web.post(f"/evaluation/{case.pk}/run/", {})
    job = last_job(case, "evaluation")
    assert job.status == Job.SUCCEEDED, job.error
    assert "No new data" in job.message


@pytest.mark.skipif(
    "not config.getoption('--run-full-evaluation', default=False)",
    reason="minutes long; run with --run-full-evaluation",
)
def test_evaluation_full_rebuild_mock(web, example):
    """test_app.TestPerformanceEvaluation.test_run_evaluation_with_example_file."""
    case, _ = import_case(web, example("example_evaluation_pi.ccp"))
    case.state = {**case.state, "data_source": "mock"}
    case.save()
    web.post(f"/evaluation/{case.pk}/run/", {"mode": "full_rebuild"})
    job = last_job(case, "evaluation")
    assert job.status == Job.SUCCEEDED, job.error
    assert job.result["n_rows"] > 0
    # Two cluster centres of this plant gas sit at the dew line: the
    # evaluation warns instead of failing.
    assert any("phase envelope" in w for w in job.warnings)


def test_evaluation_run_validates_source(web, example):
    case, _ = import_case(web, example("example_evaluation_pi.ccp"))
    case.state = {**case.state, "data_source": "file"}
    case.save()
    body = web.post(f"/evaluation/{case.pk}/run/", {}).content.decode()
    assert "Failed" in body and "plant data file" in body


# --------------------------------------------------------------------------
# Files, export and ownership
# --------------------------------------------------------------------------


def test_export_is_streamlit_loadable(web, example):
    case, _ = import_case(web, example("example_back_to_back.ccp"))
    content = web.get(f"/cases/{case.pk}/export/").content
    with zipfile.ZipFile(io.BytesIO(content)) as z:
        names = z.namelist()
        state = json.loads(z.read("session_state.json"))
    assert "back_to_back.toml" in names and "fig_head_sec1.png" in names
    # The Streamlit back-to-back loader checks this key.
    assert "div_wall_flow_m_section_1_point_1" in state
    assert ccpfile.read_ccp(content).app_type == "back_to_back"


def test_autosave_merges_fields(web, example):
    case, _ = import_case(web, example("example_straight.ccp"))
    response = web.post(
        f"/cases/{case.pk}/state/",
        {
            "flow_point_guarantee": "123",
            "opt_reynolds_correction": ["false"],
            "gas_0": "renamed",
            "gas_component_0": "methane",
            "gas_fraction_0_0": "100",
            "unknown_key": "ignored",
        },
    )
    assert response.status_code == 200
    case.refresh_from_db()
    assert case.state["flow_point_guarantee"] == "123"
    assert case.state["opt_reynolds_correction"] is False
    assert case.state["gas_0"] == "renamed"
    assert case.state["gas_compositions_table"]["gas_0"]["component_0"] == "methane"
    assert "unknown_key" not in case.state
    # References to the renamed gas fall back to the first gas.
    assert case.state["gas_point_guarantee"] == "renamed"


def test_curve_image_upload(web, example):
    from django.core.files.uploadedfile import SimpleUploadedFile

    case, _ = import_case(web, example("example_straight.ccp"))
    png = example("example_straight.ccp")[:0] + b"\x89PNG\r\n\x1a\n"
    response = web.post(
        f"/cases/{case.pk}/files/fig_power/", {"file": SimpleUploadedFile("p.png", png)}
    )
    assert response.status_code == 200
    assert case.file("fig_power").read() == png
    assert web.get(f"/cases/{case.pk}/files/fig_power/").status_code == 200
    assert (
        web.post(
            f"/cases/{case.pk}/files/bad_key/",
            {"file": SimpleUploadedFile("x.png", png)},
        ).status_code
        == 400
    )


def test_other_users_cases_are_invisible(web, example, django_user_model, client):
    case, _ = import_case(web, example("example_straight.ccp"))
    bob = django_user_model.objects.create_user(
        username="bob", email="bob@example.com", password="pw-bob-123"
    )
    client.force_login(bob)
    assert client.get(f"/performance-test/{case.pk}/").status_code == 404
    assert client.get(f"/cases/{case.pk}/export/").status_code == 404
    assert (
        client.post(
            f"/cases/{case.pk}/state/", {"flow_point_guarantee": "1"}
        ).status_code
        == 404
    )


def test_secret_handoff_is_single_use():
    from ccp_web.core import secrets

    secrets.stash_for_job(42, "pi_password", "s3cret")
    assert secrets.take_for_job(42, "pi_password") == "s3cret"
    assert secrets.take_for_job(42, "pi_password") == ""
