"""Sentry initialization with a graceful fallback.

Ported from ``ccp/app/common.py::init_sentry``. The import of
``sentry_sdk`` is optional so the Django app can run in environments
where the dependency is not available.
"""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)

_DEFAULT_DSN = (
    "https://8fd0e79dffa94dbb9747bf64e7e55047@o348313.ingest.sentry.io/4505046640623616"
)


def init_sentry(dsn: str | None = None) -> None:
    """Initialise Sentry error tracking when possible.

    This is a no-op when any of the following conditions hold:

    - ``sentry_sdk`` is not installed,
    - the resolved DSN is falsy,
    - the environment variable ``CCP_STANDALONE`` is set (mirrors the
      original Streamlit behaviour).

    Parameters
    ----------
    dsn : str or None, optional
        Explicit DSN to use. When ``None``, falls back to the
        ``SENTRY_DSN`` environment variable and then to the hard-coded
        legacy DSN from the Streamlit app. Pass an empty string to
        force the no-op path.
    """
    if os.environ.get("CCP_STANDALONE"):
        logger.debug("Sentry init skipped: CCP_STANDALONE is set.")
        return

    if dsn is None:
        dsn = os.environ.get("SENTRY_DSN") or _DEFAULT_DSN

    if not dsn:
        logger.debug("Sentry init skipped: no DSN provided.")
        return

    try:
        import sentry_sdk
    except ImportError:
        logger.info("sentry-sdk not installed; Sentry integration disabled.")
        return

    try:
        sentry_sdk.init(
            dsn=dsn,
            traces_sample_rate=1.0,
            auto_enabling_integrations=False,
        )
    except Exception as exc:
        logger.warning("Sentry initialization failed: %s", exc)
