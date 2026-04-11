"""Persistence helpers for ccp ``.ccp`` archive files.

The ``.ccp`` file format is a ZIP archive containing

- ``ccp.version`` - the ``ccp`` library version that produced the file;
- ``session_state.json`` - the JSON-serialisable part of the session;
- zero or more ``*.toml`` files holding ccp library objects
  (:class:`StraightThrough`, :class:`BackToBack`, :class:`Impeller`);
- zero or more ``*.csv`` curve files;
- zero or more ``*.png`` plot snapshots;
- optionally an ``evaluation.zip`` for performance evaluations.

This package exposes the importer/exporter pair used by the Django
views to round-trip those archives, and a small TOML codec that wraps
the ccp library's ``_dict_to_save`` / ``load`` helpers.
"""

from apps.core.storage.ccp_file_exporter import export_ccp_file
from apps.core.storage.ccp_file_importer import load_ccp_file
from apps.core.storage.toml_codec import decode_ccp_object, encode_ccp_object

__all__ = [
    "decode_ccp_object",
    "encode_ccp_object",
    "export_ccp_file",
    "load_ccp_file",
]
