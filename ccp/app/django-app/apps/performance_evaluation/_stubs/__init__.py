"""Local fallbacks for symbols owned by sister units.

These stubs let the performance evaluation app load in isolation before
Units 2, 3, 10 and 11 are merged into the worktree. Every stub is marked
with ``# STUB: replaced by Unit N`` and imported via ``try/except`` in the
real modules.
"""
