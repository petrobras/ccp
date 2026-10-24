from django.conf import settings
from django.urls import include, path

urlpatterns = [
    path("", include("ccp_web.core.urls")),
    path("performance-test/", include("ccp_web.performance_test.urls")),
    path("curves/", include("ccp_web.curves.urls")),
    path("digitizer/", include("ccp_web.digitizer.urls")),
    path("evaluation/", include("ccp_web.evaluation.urls")),
    path("agent/", include("ccp_web.agent.urls")),
    path("api/agent/v1/", include("ccp_web.agent.api_urls")),
]

if "allauth" in settings.INSTALLED_APPS:
    urlpatterns.append(path("accounts/", include("allauth.urls")))
