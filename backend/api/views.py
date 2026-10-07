from django.contrib.auth import authenticate, login
from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from .serializers import LoginSerializer, RegisterSerializer, UserSerializer


@api_view(["GET"])
def health(request):
    return Response({"status": "ok"})


class RegisterView(generics.CreateAPIView):
    """POST /api/auth/register/ — docs/api-design.md §2.1, issue #22.

    Unauthenticated (anyone may register). On success also establishes a
    session via `login()`, per docs/mvp-scope.md §3.1 ("inscription
    immédiate") and decision 0003 (session-cookie auth, no token issued) —
    matching what register/+page.svelte already assumes: it redirects to
    `/` on a successful response with nothing to store itself.
    """

    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    def perform_create(self, serializer):
        user = serializer.save()
        login(self.request, user)


class LoginView(generics.GenericAPIView):
    """POST /api/auth/login/ — docs/api-design.md §2.2, issue #23.

    Response shape deviates from §2.2 as documented: no `token` field —
    decision 0003 is session-cookie auth, established here via `login()`
    exactly as it is in RegisterView. The 200 body is the user resource
    (`UserSerializer`), not `{"token": ..., "user": {...}}`.

    AC-2 (no user-existence leakage): `authenticate()` returns `None` for
    both "no such email" and "wrong password" alike, and both get the
    identical 401 response here — there is no branch anywhere in this view
    that could tell a caller which one happened. Django's `ModelBackend`
    also runs the password hasher against a dummy value when no user
    matches, so a wrong password and a wrong email take roughly the same
    amount of time to reject (timing side-channel).

    Returns the 401 directly rather than `raise AuthenticationFailed(...)`:
    DRF's `handle_exception` silently rewrites that exception's status to
    403 unless the *first* configured authenticator provides a
    `WWW-Authenticate` challenge header. The global default authenticator
    order (settings.py doesn't override `DEFAULT_AUTHENTICATION_CLASSES`)
    is `SessionAuthentication` first, which has no such header — so the
    exception path silently becomes a 403. login/+page.svelte explicitly
    branches on `err.status === 401`, so this needs to actually be 401.

    AC-3 (brute-force): `ScopedRateThrottle` on the "login" scope (rate in
    REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"], settings.py) is the whole of
    this project's brute-force mitigation, and it is intentionally minimal
    — per-IP, not per-account, and easy to exhaust from behind a shared
    NAT. Documented, not hidden: see
    docs/decisions/0004-login-rate-limiting.md for why this is judged
    acceptable for an MVP demo and what a real deployment would need
    instead (e.g. per-account lockout, CAPTCHA).
    """

    serializer_class = LoginSerializer
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = authenticate(
            request,
            username=serializer.validated_data["email"],
            password=serializer.validated_data["password"],
        )
        if user is None:
            return Response(
                {"detail": "Invalid email or password."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        login(request, user)
        return Response(UserSerializer(user).data, status=status.HTTP_200_OK)
