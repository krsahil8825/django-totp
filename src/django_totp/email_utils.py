"""
django_totp.email_utils
=======================

Email utility functions for encoding and decoding user primary keys in a URL-safe manner.
"""

from django.utils.encoding import force_bytes, force_str
from django.utils.http import (
    urlsafe_base64_encode,
    urlsafe_base64_decode,
)


def encode_uid(pk) -> str:
    """Encode a primary key as a URL-safe base64 string."""
    return force_str(urlsafe_base64_encode(force_bytes(pk)))


def decode_uid(uid: str) -> str:
    """Decode a URL-safe base64 string back to the original value."""
    return force_str(urlsafe_base64_decode(uid))
