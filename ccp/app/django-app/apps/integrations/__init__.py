"""Optional third-party integrations (AI analysis, PI, Sentry).

Every integration in this package must degrade gracefully when its
backing dependency (``google-generativeai``, ``pandaspi``, ``sentry-sdk``)
is not installed or not configured, so that the Django app keeps
working offline outside the Petrobras network.
"""
