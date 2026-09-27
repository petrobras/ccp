"""Desktop profile middleware: log every request in as the one local user."""

from django.contrib.auth import get_user_model, login

LOCAL_USERNAME = "local"


def get_local_user():
    """Return the implicit desktop user, creating it on first start."""
    User = get_user_model()
    user, created = User.objects.get_or_create(
        username=LOCAL_USERNAME, defaults={"first_name": "Local", "last_name": "user"}
    )
    if created:
        user.set_unusable_password()
        user.save(update_fields=["password"])
    return user


class LocalUserMiddleware:
    """Authenticate requests as the local user (desktop profile only).

    The desktop server listens on 127.0.0.1 behind the native window, so there
    is no login screen; the hosted profile uses allauth instead.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not request.user.is_authenticated:
            login(
                request,
                get_local_user(),
                backend="django.contrib.auth.backends.ModelBackend",
            )
        return self.get_response(request)
