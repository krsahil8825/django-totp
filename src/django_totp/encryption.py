"""
django_totp.encryption
=======================

This module provides encryption and decryption utilities for 
TOTP secrets using Fernet symmetric encryption.
"""


from cryptography.fernet import Fernet
from django.core.exceptions import ImproperlyConfigured
from django.conf import settings as django_settings


def get_valid_fernet_key(default=None):
    raw_key = getattr(django_settings, "DJANGO_TOTP_ENCRYPTION_KEY")

    if raw_key:
        key = raw_key.encode()
    elif default is not None:
        key = default if isinstance(default, bytes) else default.encode()
    else:
        raise ImproperlyConfigured(
            "DJANGO_TOTP_ENCRYPTION_KEY must be set to a valid Fernet key."
        )

    try:
        Fernet(key)
    except Exception as exc:
        raise ImproperlyConfigured(
            "DJANGO_TOTP_ENCRYPTION_KEY must be a valid Fernet key."
        ) from exc

    return key


_fernet = Fernet(get_valid_fernet_key())


def encrypt(value: str) -> str:
    """
    Encrypt a string using Fernet symmetric encryption.

    Args:
        value (str): Plain text value.

    Returns:
        str: Encrypted string (URL-safe base64 encoded).
    """
    return _fernet.encrypt(value.encode()).decode()


def decrypt(value: str) -> str:
    """
    Decrypt a string encrypted with Fernet.

    Args:
        value (str): Encrypted string (URL-safe base64 encoded).

    Returns:
        str: Decrypted plain text value.
    """
    return _fernet.decrypt(value.encode()).decode()
