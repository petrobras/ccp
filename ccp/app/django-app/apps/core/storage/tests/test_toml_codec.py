"""Tests for the TOML codec wrapper."""

from __future__ import annotations

import pytest

from apps.core.storage.toml_codec import decode_ccp_object, encode_ccp_object


def test_encode_rejects_objects_without_dict_to_save():
    """Encoding bare objects raises :class:`TypeError`."""
    with pytest.raises(TypeError):
        encode_ccp_object(object())


def test_decode_rejects_unknown_app_type():
    """Unknown app types raise :class:`ValueError`."""
    with pytest.raises(ValueError):
        decode_ccp_object("nonsense", "")
