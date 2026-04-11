"""Tests for :mod:`apps.integrations.pi_client`."""

from __future__ import annotations

import sys

import pandas as pd

from apps.integrations import pi_client


def test_imports_without_pandaspi(monkeypatch):
    """Module must remain importable when pandaspi is absent."""
    monkeypatch.setitem(sys.modules, "pandaspi", None)
    import importlib

    reloaded = importlib.reload(pi_client)
    assert hasattr(reloaded, "is_pi_available")


def test_is_pi_available_returns_bool():
    assert isinstance(pi_client.is_pi_available(), bool)


def test_is_pi_available_false_when_import_fails(monkeypatch):
    monkeypatch.setitem(sys.modules, "pandaspi", None)
    assert pi_client.is_pi_available() is False


def test_fetch_pi_data_returns_empty_frame_offline(monkeypatch):
    """When PI is unavailable, an empty canonical DataFrame is returned."""
    monkeypatch.setattr(pi_client, "is_pi_available", lambda: False)
    df = pi_client.fetch_pi_data({"suc_p_tag": "TAG_PS"})
    assert isinstance(df, pd.DataFrame)
    assert df.empty
    for col in pi_client.EXPECTED_COLUMNS:
        assert col in df.columns


def test_fetch_pi_data_empty_when_no_tags(monkeypatch):
    monkeypatch.setattr(pi_client, "is_pi_available", lambda: True)
    df = pi_client.fetch_pi_data({})
    assert isinstance(df, pd.DataFrame)
    assert df.empty


def test_clean_pi_data_drops_dict_rows():
    df = pd.DataFrame(
        {
            "ps": [1.0, {"Value": "err"}, 3.0],
            "Ts": [300.0, 301.0, 302.0],
        }
    )
    cleaned = pi_client.clean_pi_data(df)
    assert len(cleaned) == 2
    assert cleaned["ps"].dtype.kind == "f"


def test_clean_pi_data_all_errors_raises():
    df = pd.DataFrame({"ps": [{"Value": "err"}, {"Value": "err"}]})
    try:
        pi_client.clean_pi_data(df)
    except ValueError as exc:
        assert "instrument error" in str(exc)
    else:
        raise AssertionError("Expected ValueError")


def test_clean_pi_data_empty_dataframe():
    df = pd.DataFrame()
    assert pi_client.clean_pi_data(df).empty


def test_build_tags_list_maps_canonical_columns():
    tag_map = {
        "suc_p_tag": "TAG_PS",
        "disch_T_tag": "TAG_TD",
        "speed_tag": "",
    }
    tags, rename_map = pi_client._build_tags_list(tag_map)
    assert "TAG_PS" in tags
    assert "TAG_TD" in tags
    assert rename_map["TAG_PS"] == "ps"
    assert rename_map["TAG_TD"] == "Td"
