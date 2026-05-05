"""Fernet helpers for encrypting and decrypting TOTP secrets."""

from functools import lru_cache

from cryptography.fernet import Fernet
from django.conf import settings as django_settings
from django.core.exceptions import ImproperlyConfigured


def generate_fernet_key() -> str:
    """Generate and return a new Fernet key."""

    return Fernet.generate_key().decode()


def resolve_fernet_key(default: str | bytes | None = None) -> bytes:
    """Return a valid Fernet key from Django settings or a fallback value."""

    raw_key = getattr(django_settings, "TOTP_ENCRYPTION_KEY", None)

    if raw_key:
        key = raw_key.encode() if isinstance(raw_key, str) else raw_key
    elif default is not None:
        key = default if isinstance(default, bytes) else default.encode()
    else:
        raise ImproperlyConfigured(
            "TOTP_ENCRYPTION_KEY must be set to a valid Fernet key."
        )

    try:
        Fernet(key)
    except Exception as exc:  # pragma: no cover - defensive validation
        raise ImproperlyConfigured(
            "TOTP_ENCRYPTION_KEY must be a valid Fernet key."
        ) from exc

    return key


@lru_cache(maxsize=1)
def _get_fernet() -> Fernet:
    """Build the Fernet instance after Django settings are loaded."""

    return Fernet(resolve_fernet_key())


def encrypt(value: str) -> str:
    """Encrypt and return a URL-safe Fernet token."""

    return _get_fernet().encrypt(value.encode()).decode()


def decrypt(value: str) -> str:
    """Decrypt a Fernet token and return the original plaintext value."""

    return _get_fernet().decrypt(value.encode()).decode()
