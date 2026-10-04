"""Curves digitizer page: upload, digitize, edit, export, hand-off.

The PDF is the synthetic vendor-style sheet of ``ccp/tests/test_digitize.py``
(drawn with pypdfium2), so the flow runs without vendor documents. Needs the
``digitize`` extra and Tesseract; skipped otherwise.
"""

import io
import json
import zipfile

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from ccp_web.core.models import Case, Job
from ccp_web.services import ccpfile, digitizer
from ccp_web.services.units import InputError

pytestmark = pytest.mark.django_db

needs_digitizer = pytest.mark.skipif(
    not digitizer.available(), reason="digitize extra or tesseract missing"
)


# --------------------------------------------------------------- services


@pytest.mark.parametrize(
    "text, pages",
    [("", None), ("3", [3]), ("3-5, 9", [3, 4, 5, 9]), ("2;2 1", [1, 2])],
)
def test_parse_pages(text, pages):
    assert digitizer.parse_pages(text) == pages


@pytest.mark.parametrize("text", ["a", "5-3", "0"])
def test_parse_pages_errors(text):
    with pytest.raises(InputError):
        digitizer.parse_pages(text)


def _doc():
    return {
        "plots": [
            {
                "id": "3-0",
                "page": 3,
                "box": [0, 0, 10, 10],
                "dpi": 300,
                "curves": [{"speed": 1000.0, "flow": [1, 2], "value": [3, 4]}],
            }
        ],
        "cases": [],
    }


def test_update_plot_sorts_and_drops_bad_lines():
    data = _doc()
    notes = digitizer.update_plot(
        data,
        "3-0",
        [
            {"speed": 2000, "points": [[3, 1], [1, 2], ["x", 1]]},
            {"speed": 1000, "points": [[1, 1]]},
            {"speed": None, "points": [[1, 1], [2, 2]]},
        ],
    )
    plot = data["plots"][0]
    assert plot["edited"] is True
    assert plot["curves"] == [
        {"speed": 2000.0, "flow": [1.0, 3.0], "value": [2.0, 1.0]}
    ]
    assert len(notes) == 2


def test_update_plot_rejects_duplicate_speeds():
    with pytest.raises(InputError):
        digitizer.update_plot(
            _doc(),
            "3-0",
            [{"speed": 1, "points": [[1, 1], [2, 2]]}] * 2,
        )


# --------------------------------------------------------------- flow


@pytest.fixture(scope="module")
def sheet_pdf(tmp_path_factory):
    from ccp.tests.test_digitize import make_sheet

    path = tmp_path_factory.mktemp("sheet") / "vendor curves.pdf"
    make_sheet(path)
    return path.read_bytes()


@needs_digitizer
def test_digitizer_flow(web, sheet_pdf, monkeypatch):
    monkeypatch.setenv("CCP_DIGITIZE_WORKERS", "1")
    response = web.get("/app/curves_digitizer/", follow=True)
    assert response.status_code == 200
    assert b"Curves digitizer" in response.content
    case = Case.objects.get(app_type=Case.CURVES_DIGITIZER)
    base = f"/digitizer/{case.pk}"

    # digitize without a PDF: a field error, no job
    response = web.post(f"{base}/digitize/", {})
    assert b"Upload a curve PDF first" in response.content

    response = web.post(
        f"/cases/{case.pk}/files/curve_pdf/",
        {"file": SimpleUploadedFile("vendor curves.pdf", sheet_pdf)},
    )
    assert response.status_code == 200
    assert case.file("curve_pdf").kind == "curve_pdf"

    response = web.post(f"{base}/digitize/", {"digitize_pages": "1"})
    job = Job.objects.filter(case=case, kind="digitize_pdf").latest("pk")
    assert job.status == Job.SUCCEEDED, job.error
    assert job.result["cases"] == 1

    page = web.get(f"{base}/").content.decode()
    assert "TEST-1 CASE A" in page
    data = json.loads(case.artifact("digitized").read())
    case_dict = data["cases"][0]
    head_id = case_dict["plots"]["head"]
    eff_id = case_dict["plots"]["eff"]

    # editor and image
    response = web.get(f"{base}/plot/{head_id}/")
    assert response.status_code == 200
    assert 'id="dz-plot"' in response.content.decode()
    assert web.get(f"{base}/?plot={head_id}").status_code == 200
    png = web.get(f"{base}/plot/{head_id}/image.png")
    assert png["Content-Type"] == "image/png"
    assert png.content[:8] == b"\x89PNG\r\n\x1a\n"

    # edit: drop the last point of the first line and move its first point
    payload = digitizer.editor_payload(data, head_id)
    curves = payload["curves"]
    first = curves[0]
    first["points"] = first["points"][:-1]
    first["points"][0][1] += 5.0
    response = web.post(
        f"{base}/plot/{head_id}/save/",
        json.dumps({"curves": curves}),
        content_type="application/json",
    )
    assert response.status_code == 200, response.content
    assert response.json()["ok"] is True
    saved = json.loads(case.artifact("digitized").read())
    plot = next(p for p in saved["plots"] if p["id"] == head_id)
    assert plot["edited"] is True
    assert len(plot["curves"][0]["flow"]) == len(first["points"])
    assert plot["curves"][0]["value"][0] == pytest.approx(first["points"][0][1])

    bad = web.post(
        f"{base}/plot/{head_id}/save/",
        json.dumps({"curves": [curves[0], curves[0]]}),
        content_type="application/json",
    )
    assert bad.status_code == 400

    # reset restores the automatic digitization
    assert web.post(f"{base}/plot/{head_id}/reset/").status_code == 200
    reset = json.loads(case.artifact("digitized").read())
    original = json.loads(case.artifact("digitized_original").read())
    assert (
        next(p for p in reset["plots"] if p["id"] == head_id)["curves"]
        == next(p for p in original["plots"] if p["id"] == head_id)["curves"]
    )

    # CSV export
    response = web.get(f"{base}/export.zip")
    names = zipfile.ZipFile(io.BytesIO(response.content)).namelist()
    slug = digitizer.load(reset).cases[0].slug
    assert f"{slug}-head.csv" in names and f"{slug}-eff.csv" in names
    assert "digitized.json" in names

    # hand-off to a new curves conversion case
    response = web.post(f"{base}/to-conversion/", {"case": [slug]})
    assert response.status_code == 302
    conversion = Case.objects.filter(app_type=Case.CURVES_CONVERSION).latest("pk")
    assert response["Location"] == conversion.get_absolute_url()
    assert conversion.state["suc_p_case_A"] == pytest.approx(12.5)
    assert conversion.state["suc_T_case_A"] == pytest.approx(32.5)
    assert conversion.state["loaded_curves_head_units"] == "kJ/kg"
    f1 = conversion.file("curves_file_1_case_A")
    f2 = conversion.file("curves_file_2_case_A")
    assert {f1.name, f2.name} == {f"{slug}-head.csv", f"{slug}-eff.csv"}
    assert f1.read().decode().startswith("x,")
    assert eff_id  # both plots of the pair exist

    # .ccp round trip keeps the PDF and both digitizations
    content = web.get(f"/cases/{case.pk}/export/").content
    parsed = ccpfile.read_ccp(content)
    assert parsed.app_type == "curves_digitizer"
    assert parsed.files["curve_pdf"][1] == "vendor curves.pdf"
    assert set(parsed.artifacts) >= {"digitized", "digitized_original"}
    assert parsed.state["digitize_pages"] == "1"


def test_thin_plot_keeps_ends_and_original_points():
    flow = [float(i) for i in range(40)]
    plot = {
        "dpi": 300,
        "x_axis": {"offset": 0.0, "slope": 2.0},  # 2 px per unit: 78 px long
        "y_axis": {"offset": 0.0, "slope": -1.0},
        "curves": [{"speed": 1.0, "flow": flow, "value": [0.0] * 40}],
    }
    digitizer.thin_plot(plot, spacing=25, min_points=3)
    kept = plot["curves"][0]["flow"]
    assert kept[0] == 0.0 and kept[-1] == 39.0
    assert 3 <= len(kept) <= 5
    assert set(kept) <= set(flow)
