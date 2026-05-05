"""Authentication helpers for 2FA login flow with temporary tokens."""

from django.contrib.auth.models import User
from django.conf import settings as django_settings
from django.core import signing
from django.core.signing import BadSignature, SignatureExpired

from .models import Totp


# Configurable settings for token generation and verification
TOKEN_SALT = getattr(django_settings, "TOTP_TOKEN_SALT", "django-totp-token-salt")
TOKEN_MAX_AGE = getattr(django_settings, "TOTP_TOKEN_MAX_AGE", 120)  # 2 minutes


def is_totp_enabled(user: User) -> bool:
    """Check if a user has TOTP authentication enabled."""
    if not user.is_authenticated:
        return False

    return Totp.objects.filter(user=user).exists()


def generate_challenge_token(user: User) -> str:
    """Generate a temporary signed token for TOTP verification."""

    data = {
        "user_id": user.id,
        "purpose": "totp_verification",
    }

    return signing.dumps(data, salt=TOKEN_SALT)


def verify_challenge_token(token: str) -> int:
    """Verify and extract user ID from a signed TOTP verification token."""
    try:
        data = signing.loads(
            token,
            salt=TOKEN_SALT,
            max_age=TOKEN_MAX_AGE,
        )
        return data["user_id"]

    except SignatureExpired as exc:
        raise SignatureExpired("TOTP token has expired.") from exc

    except BadSignature as exc:
        raise BadSignature("Invalid or tampered TOTP token.") from exc


def get_user_from_challenge_token(token: str) -> User:
    """Retrieve a user from a signed TOTP verification token."""
    try:
        return User.objects.get(id=verify_challenge_token(token))
    except User.DoesNotExist:
        raise User.DoesNotExist("User not found.")
