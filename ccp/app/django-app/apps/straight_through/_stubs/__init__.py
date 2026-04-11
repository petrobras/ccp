"""Local stand-ins for cross-unit dependencies.

These modules let :mod:`apps.straight_through` import and run in isolation
while the other migration units are still under development. They are marked
``# STUB: replaced by Unit N`` and will be superseded at merge time.
"""
