"""
django_totp.utils
========================

Utility functions for TOTP backup code management.
"""

from cryptography.fernet import InvalidToken
from django.contrib.auth.models import User
from django.db import transaction
from secrets import compare_digest

from .backup_code import generate_backup_codes
from .encryption import encrypt, decrypt
from .models import Totp, BackupCode


def save_backup_codes(user: User, codes: list[str]) -> list[str]:
    """
    Store encrypted backup codes for a user.

    Any previously stored backup codes are deleted before saving the new set.

    Note:
        The plaintext codes are returned because the user must be able to
        view and securely store them at least once. After this point, only
        the encrypted versions are retained in the database, and the
        plaintext values cannot be retrieved again.

    Args:
        user (User): The user for whom the backup codes are generated.
        codes (list[str]): A list of plaintext backup codes.

    Returns:
        list[str]: The plaintext backup codes that were just saved.
    """

    with transaction.atomic():
        totp_qs = Totp.objects.filter(user=user).first()
        if not totp_qs:
            raise ValueError("User does not have an associated TOTP secret.")

        # remove existing backup codes before saving new ones
        BackupCode.objects.filter(totp=totp_qs).delete()

        backup_codes = [
            BackupCode(
                totp=totp_qs,
                code=encrypt(code),
            )
            for code in codes
        ]

        BackupCode.objects.bulk_create(backup_codes)

        return codes


def verify_backup_code(user: User, input_code: str) -> bool:
    """
    Verify a backup code and mark it as used.

    Args:
        user (User): Target user.
        input_code (str): Code provided by user.

    Returns:
        bool: True if valid, False otherwise.
    """
    with transaction.atomic():
        totp_qs = Totp.objects.filter(user=user).first()
        if not totp_qs:
            raise ValueError("User does not have an associated TOTP secret.")

        backup_codes = BackupCode.objects.select_for_update().filter(
            totp=totp_qs,
            is_used=False,
        )

        for code_obj in backup_codes:
            try:
                decrypted_code = decrypt(code_obj.code)
            except InvalidToken:
                continue

            if compare_digest(decrypted_code, input_code):
                code_obj.is_used = True
                code_obj.save(update_fields=["is_used"])
                return True

    return False


def regenerate_backup_codes(user: User) -> list[str]:
    """
    Regenerate backup codes for a user.

    This function deletes all existing backup codes and generates a new set of
    plaintext backup codes, which are then encrypted and stored in the database.

    Args:
        user (User): The user for whom to regenerate backup codes.

    Returns:
        list[str]: The new plaintext backup codes that were generated.
    """

    new_codes = generate_backup_codes()

    return save_backup_codes(user, new_codes)
