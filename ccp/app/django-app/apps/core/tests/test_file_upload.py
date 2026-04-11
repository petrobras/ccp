"""Tests for the core upload/download HTTP views."""

from __future__ import annotations

import io
from pathlib import Path

import openpyxl
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, override_settings
from django.urls import reverse

EXAMPLE_CCP = Path(__file__).resolve().parents[4] / "example_straight.ccp"


@pytest.fixture()
def client() -> Client:
    return Client()


def test_example_ccp_file_exists():
    assert EXAMPLE_CCP.exists(), f"fixture missing: {EXAMPLE_CCP}"


def test_upload_ccp_returns_session_id(client):
    payload = EXAMPLE_CCP.read_bytes()
    upload = SimpleUploadedFile(
        "example_straight.ccp", payload, content_type="application/zip"
    )
    resp = client.post(reverse("core:upload-ccp"), {"file": upload})
    assert resp.status_code == 200, resp.content
    data = resp.json()
    assert "session_id" in data
    assert data["name"] == "example_straight.ccp"
    assert isinstance(data["keys"], list)


def test_upload_ccp_missing_file_returns_400(client):
    resp = client.post(reverse("core:upload-ccp"))
    assert resp.status_code == 400
    assert "missing" in resp.json()["error"]


@override_settings(CCP_MAX_UPLOAD_SIZE=16)
def test_upload_ccp_rejects_oversize(client):
    upload = SimpleUploadedFile(
        "too_big.ccp", b"x" * 1024, content_type="application/zip"
    )
    resp = client.post(reverse("core:upload-ccp"), {"file": upload})
    assert resp.status_code == 413


def test_upload_csv_echoes_content(client):
    upload = SimpleUploadedFile(
        "curve.csv", b"x,y\n1,2\n3,4\n", content_type="text/csv"
    )
    resp = client.post(reverse("core:upload-csv"), {"file": upload})
    assert resp.status_code == 200
    data = resp.json()
    assert "x,y" in data["content"]
    assert data["name"] == "curve.csv"


def test_upload_curve_png_round_trip(client):
    fake_png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
    upload = SimpleUploadedFile("head.png", fake_png, content_type="image/png")
    resp = client.post(
        reverse("core:upload-curve-png"),
        {"file": upload, "key": "head"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["key"] == "head"
    assert data["bytes"] == len(fake_png)
    assert "session_id" in data


def test_download_ccp_round_trip(client):
    payload = EXAMPLE_CCP.read_bytes()
    upload = SimpleUploadedFile(
        "example_straight.ccp", payload, content_type="application/zip"
    )
    upload_resp = client.post(reverse("core:upload-ccp"), {"file": upload})
    session_id = upload_resp.json()["session_id"]

    resp = client.get(reverse("core:download-ccp", args=[session_id]))
    assert resp.status_code == 200
    assert resp["Content-Type"] == "application/zip"
    assert b"PK" in resp.content[:4]
    assert ".ccp" in resp["Content-Disposition"]


def test_download_excel_round_trip(client):
    payload = EXAMPLE_CCP.read_bytes()
    upload = SimpleUploadedFile(
        "example_straight.ccp", payload, content_type="application/zip"
    )
    upload_resp = client.post(reverse("core:upload-ccp"), {"file": upload})
    session_id = upload_resp.json()["session_id"]

    resp = client.get(reverse("core:download-excel", args=[session_id]))
    assert resp.status_code == 200
    assert "spreadsheetml" in resp["Content-Type"]
    wb = openpyxl.load_workbook(io.BytesIO(resp.content))
    assert "Parametros" in wb.sheetnames


def test_download_ccp_unknown_session_404(client):
    resp = client.get(reverse("core:download-ccp", args=["does-not-exist"]))
    assert resp.status_code == 404
