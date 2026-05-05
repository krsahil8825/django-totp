"""Throttle configuration for the TOTP API endpoints."""

from django.conf import settings as django_settings
from rest_framework.throttling import UserRateThrottle

THROTTLE_RATE = getattr(django_settings, "TOTP_THROTTLE_RATE", "10/minute")


class TotpThrottle(UserRateThrottle):
    """Apply a configurable rate limit to TOTP-related API actions."""

    rate = THROTTLE_RATE
