"""
django_totp.urls.recovery
=========================

URL patterns for TOTP recovery endpoints.
"""

from rest_framework.routers import DefaultRouter
from ..views import TotpRecoveryViewSet

router = DefaultRouter()
router.register(r"totp", TotpRecoveryViewSet, basename="totp-recovery")

urlpatterns = router.urls
