"""Root URL configuration used only when running the app in isolation.

# STUB: replaced by Unit 1's ``ccp_web/urls.py`` at merge time
"""

from django.urls import include, path

urlpatterns = [
    path("back-to-back/", include("apps.back_to_back.urls")),
]
