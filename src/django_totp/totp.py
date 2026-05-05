"""
django_totp.totp
================

This module provides functionality for managing TOTP secrets and backup codes for users.
"""

from django.contrib.auth.models import User
from django.conf import settings as django_settings
from typing import List
import pyotp

from .backup_code_utils import save_backup_codes
from .encryption import encrypt, decrypt
from .models import Totp, BackupCode
from .qrsvg import generate_qr_code_svg


TOTP_ISSUER = getattr(django_settings, "TOTP_ISSUER", "MyApp")


def generate_totp_secret() -> str:
    """
    Generate a random TOTP secret.

    Returns:
        str: A base32-encoded TOTP secret.
    """

    return pyotp.random_base32()


def verify_user_totp_input(user: User, input_code: str) -> bool:
    """
    Verify a user's TOTP input code against their stored secret.

    Args:
        user (User): The user whose TOTP code is being verified.
        input_code (str): The TOTP code input by the user.

    Returns:
        bool: True if the code is valid, False otherwise.
    """

    totp_qs = Totp.objects.filter(user=user).first()
    if not totp_qs:
        raise ValueError("User does not have an associated TOTP secret.")

    totp = pyotp.TOTP(decrypt(totp_qs.secret))

    return totp.verify(input_code, valid_window=1)  # allow 1 time step before/after


def create_totp(user: User) -> str:
    """
    Create a TOTP secret for a user.

    Args:
        user (User): The user for whom the TOTP secret is being created.

    Returns:
        str: QR code SVG content as a string.
    """

    if BackupCode.objects.filter(totp__user=user).exists():
        raise ValueError("TOTP already exists for this user.")

    secret = generate_totp_secret()

    Totp.objects.create(user=user, secret=encrypt(secret))

    uri = pyotp.TOTP(secret).provisioning_uri(
        name=user.get_username(), issuer_name=TOTP_ISSUER
    )

    return generate_qr_code_svg(uri)


def confirm_totp_setup(user: User, input_code: str) -> List[str]:
    """
    Confirm TOTP setup by verifying the user's input code.

    Args:
        user (User): The user confirming their TOTP setup.
        input_code (str): The TOTP code input by the user.

    Returns:
        List[str]: A list of plaintext backup codes if verification is successful.
    """

    totp_qs = Totp.objects.filter(user=user).first()
    if not totp_qs:
        raise ValueError("User does not have an associated TOTP secret.")

    if not verify_user_totp_input(user, input_code):
        raise ValueError("Invalid TOTP code.")

    return save_backup_codes(user)


def disable_totp(user: User) -> None:
    """
    Disable TOTP for a user by deleting their TOTP secret and backup codes.

    Args:
        user (User): The user for whom TOTP should be disabled.
    """

    Totp.objects.filter(user=user).delete()
