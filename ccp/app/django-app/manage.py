#!/usr/bin/env python
"""Django command-line utility for administrative tasks."""

import os
import sys


def main() -> None:
    """Run administrative tasks."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ccp_web.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Install it with `uv sync --extra django-app`."
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
