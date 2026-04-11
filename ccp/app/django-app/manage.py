#!/usr/bin/env python
"""Django management entry point (Unit 12 local scaffold).

# STUB: replaced by Unit 1 at merge time.
"""

import os
import sys


def main():
    """Run administrative tasks."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ccp_web.settings")
    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
