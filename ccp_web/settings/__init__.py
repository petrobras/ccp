"""Settings for the ccp web application.

``CCP_PROFILE`` selects the runtime profile:

- ``desktop`` (default): single local user, SQLite and media in the user data
  directory, auto-login.
- ``hosted``: multi-user service with allauth accounts and PostgreSQL.
- ``test``: used by the test suite.

``DJANGO_SETTINGS_MODULE`` points at this package; the profile module is
imported here so that ``manage.py``, the WSGI entry and the task workers all
resolve the same settings.
"""

import os

PROFILE = os.environ.get("CCP_PROFILE", "desktop").strip().lower() or "desktop"
# ``DJANGO_SETTINGS_MODULE=ccp_web.settings.test`` (pytest) names a profile
# module directly; importing this package must not load another profile.
_DIRECT = os.environ.get("DJANGO_SETTINGS_MODULE", "").startswith("ccp_web.settings.")

if _DIRECT:
    pass
elif PROFILE == "desktop":
    from .desktop import *  # noqa: F401,F403
elif PROFILE == "hosted":
    from .hosted import *  # noqa: F401,F403
elif PROFILE == "test":
    from .test import *  # noqa: F401,F403
else:
    raise RuntimeError(
        f"Unknown CCP_PROFILE {PROFILE!r}; use 'desktop', 'hosted' or 'test'."
    )
