"""Root URLconf for Unit 12 local scaffold.

# STUB: replaced by Unit 1 at merge time.
"""

from django.urls import include, path

urlpatterns = [
    path("core/", include("apps.core.urls")),
]
