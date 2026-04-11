"""MongoEngine document models for the ccp Django app.

The only document defined here is :class:`Session`, an ephemeral-to-durable
mirror of what used to be Streamlit's ``st.session_state``. A :class:`Session`
is persisted to MongoDB when the user saves a ``.ccp`` file or otherwise
requests long-term storage; Redis-backed caching of the same data is handled
by :mod:`apps.core.session_store`.

Notes
-----
We intentionally do NOT call :func:`mongoengine.connect` at import time -
Unit 1's Django settings are responsible for configuring the connection
via the ``MONGO_URL`` environment variable before the model is used.
"""

from __future__ import annotations

from datetime import datetime

from mongoengine import DateTimeField, DictField, Document, StringField

APP_TYPES = (
    "straight_through",
    "back_to_back",
    "curves_conversion",
    "performance_evaluation",
)


class Session(Document):
    """Persisted mirror of a user's Streamlit-style session state.

    Attributes
    ----------
    name : str
        Human-readable session name (typically the ``.ccp`` file stem).
    app_type : str
        Which page produced the session. One of
        ``{"straight_through", "back_to_back", "curves_conversion",
        "performance_evaluation"}``.
    state : dict
        JSON-serialisable payload equivalent to ``st.session_state``.
        Binary blobs (figures, Impeller TOML, Evaluation ZIPs) are stored
        as base64 strings inside this dict under well-known keys - see
        :mod:`apps.core.storage.ccp_file_importer`.
    ccp_version : str
        The ``ccp.__version__`` that produced the session; used by the
        version-migration helper in :mod:`ccp.app.common`.
    created_at, updated_at : datetime
        Timestamps in UTC.
    """

    name = StringField(required=True)
    app_type = StringField(choices=APP_TYPES)
    state = DictField()
    ccp_version = StringField()
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)

    meta = {
        "collection": "sessions",
        "indexes": ["name", "app_type"],
    }

    def save(self, *args, **kwargs):  # noqa: D401 - short override
        """Update ``updated_at`` on every save."""
        self.updated_at = datetime.utcnow()
        return super().save(*args, **kwargs)
