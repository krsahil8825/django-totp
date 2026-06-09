"""
django_totp.totp
================

High-level TOTP lifecycle helpers for Django users.
"""

from cryptography.fernet import InvalidToken
from django.conf import settings as django_settings
from django.contrib.auth.models import User
from django.db import transaction, IntegrityError

import pyotp
from typing import List

from .backup_code import generate_backup_codes
from .backup_code_utils import store_backup_codes
from .encryption import decrypt, encrypt
from .models import BackupCode, Totp
from .qrsvg import render_qr_code_svg


TOTP_ISSUER = getattr(django_settings, "TOTP_ISSUER", "MyApp")


def generate_totp_secret() -> str:
    """Return a new base32-encoded TOTP secret."""

    return pyotp.random_base32()


def verify_totp_code(user: User, input_code: str) -> bool:
    """
    Verify a user-provided TOTP code against the stored secret,
    allowing for a 30-second clock skew.
    """

    totp = Totp.objects.filter(user=user).first()
    if not totp:
        raise ValueError("User does not have an associated TOTP secret.")

    try:
        secret = decrypt(totp.secret_key)
    except InvalidToken:
        # Treat decryption failure as invalid code
        return False

    totp = pyotp.TOTP(secret)

    return totp.verify(input_code, valid_window=1)


def create_totp_setup(user: User) -> str:
    """Create and persist a new TOTP secret, then return the QR-code SVG."""

    with transaction.atomic():
        existing_totp = Totp.objects.filter(user=user).first()

        if existing_totp:
            if BackupCode.objects.filter(totp=existing_totp).exists():
                raise ValueError(
                    "TOTP is already enabled. Disable it before creating a new one."
                )

            existing_totp.delete()

        secret = generate_totp_secret()

        try:
            Totp.objects.create(
                user=user,
                secret_key=encrypt(secret),
            )
        except IntegrityError:
            raise ValueError("TOTP already exists for this user.")

        uri = pyotp.TOTP(secret).provisioning_uri(
            name=user.get_username(), issuer_name=TOTP_ISSUER
        )

        return render_qr_code_svg(uri)


def confirm_totp_setup(user: User, input_code: str) -> List[str]:
    """Confirm TOTP enrollment and return freshly generated backup codes."""

    with transaction.atomic():
        totp = Totp.objects.select_for_update().filter(user=user).first()

        if not totp:
            raise ValueError("User does not have an associated TOTP secret.")

        if BackupCode.objects.filter(totp=totp).exists():
            raise ValueError("Backup codes already exist for this user.")

        if not verify_totp_code(user, input_code):
            raise ValueError("Invalid TOTP code.")

        return store_backup_codes(user, generate_backup_codes())


def disable_totp(user: User) -> None:
    """Remove the user's TOTP secret and any stored backup codes."""
    with transaction.atomic():
        totp = Totp.objects.filter(user=user).first()
        if not totp:
            raise ValueError("User does not have an associated TOTP secret.")

        BackupCode.objects.filter(totp=totp).delete()
        totp.delete()
