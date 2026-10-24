"""Page endpoints of the agent API, mounted at ``agent/`` (session auth)."""

from django.urls import path

from . import views

app_name = "agent"

urlpatterns = [
    path("presence/", views.presence, name="presence"),
    path("poll/", views.poll, name="poll"),
    path("revisions/<int:pk>/undo/", views.undo, name="undo"),
    path("notes/<int:pk>/dismiss/", views.note_dismiss, name="note_dismiss"),
    path("panel/<int:pk>/", views.panel, name="panel"),
    path("tokens/", views.tokens, name="tokens"),
    path("tokens/<int:pk>/revoke/", views.token_revoke, name="token_revoke"),
]
