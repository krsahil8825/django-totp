"""URL patterns for TOTP authentication."""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import TotpViewSet

router = DefaultRouter()
router.register(r"totp", TotpViewSet, basename="totp")

urlpatterns = [
    path("", include(router.urls)),
]
