"""Views for the home landing page."""

from django.shortcuts import render


def index(request):
    """Render the Portuguese landing page.

    The copy is ported verbatim from ``ccp/app/ccp_app.py`` so the
    Django version matches the existing Streamlit experience.
    """
    return render(request, "home/index.html")
