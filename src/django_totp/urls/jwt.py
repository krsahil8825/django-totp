"""URL patterns for TOTP 2FA JWT authentication."""

from django.urls import path
from rest_framework_simplejwt import views
from ..views import (
    JWTCreateView,
    JWTTOTP2FAVerifyView,
)

urlpatterns = [
    path("jwt/create/", JWTCreateView.as_view(), name="jwt-create"),
    path("jwt/totp/verify/", JWTTOTP2FAVerifyView.as_view(), name="jwt-totp-verify"),
    path("jwt/refresh/", views.TokenRefreshView.as_view(), name="jwt-refresh"),
    path("jwt/verify/", views.TokenVerifyView.as_view(), name="jwt-verify"),
]
