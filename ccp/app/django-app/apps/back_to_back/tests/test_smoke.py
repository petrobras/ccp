"""Smoke tests for the back-to-back Django app."""

from __future__ import annotations

from django.test import Client
from django.urls import reverse


def test_index_renders():
    """The root page returns HTTP 200 and the Portuguese heading."""
    client = Client()
    response = client.get(reverse("back_to_back:index"))
    assert response.status_code == 200
    body = response.content.decode("utf-8")
    assert "Performance Test Back-to-Back Compressor" in body
    assert "Data Sheet - First Section" in body


def test_forms_import():
    """Forms module must import and formsets must have 6 slots."""
    from apps.back_to_back.forms import (
        FirstSectionTestPointFormSet,
        SecondSectionTestPointFormSet,
    )

    assert FirstSectionTestPointFormSet.extra == 6
    assert SecondSectionTestPointFormSet.extra == 6


def test_services_module_surface():
    """Services module exposes the ``run_back_to_back`` entry point."""
    from apps.back_to_back import services

    assert callable(services.run_back_to_back)
    assert "sec1" in services.SECTION_KEYS
    assert "sec2" in services.SECTION_KEYS
    assert "head" in services.CURVE_NAMES
    assert "power" in services.CURVE_NAMES


def test_existing_ccp_file_is_loadable():
    """The packaged ``example_back_to_back.ccp`` can be parsed by the importer."""
    from pathlib import Path

    from apps.back_to_back._stubs.bootstrap import install

    install()
    from apps.core.storage.ccp_file_importer import load_ccp_file

    source = (
        Path(__file__).resolve().parents[4] / "example_back_to_back.ccp"
    )
    if not source.exists():
        return
    with source.open("rb") as fp:
        state = load_ccp_file(fp)
    assert isinstance(state, dict)
    assert "div_wall_flow_m_section_1_point_1" in state
