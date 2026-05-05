"""Persistence and verification helpers for encrypted backup codes."""

from cryptography.fernet import InvalidToken
from django.contrib.auth.models import User
from django.db import transaction
from secrets import compare_digest

from .backup_code import generate_backup_codes
from .encryption import decrypt, encrypt
from .models import BackupCode, Totp


def _get_user_totp_model_obj(user: User) -> Totp:
    """Return the TOTP record for a user or raise a helpful error."""

    totp = Totp.objects.filter(user=user).first()
    if not totp:
        raise ValueError("User does not have an associated TOTP secret.")

    return totp


def store_backup_codes(user: User, codes: list[str]) -> list[str]:
    """Replace a user's backup codes with the provided plaintext values."""

    with transaction.atomic():
        totp = _get_user_totp_model_obj(user)

        BackupCode.objects.filter(totp=totp).delete()

        backup_codes = [
            BackupCode(
                totp=totp,
                code=encrypt(code),
            )
            for code in codes
        ]

        BackupCode.objects.bulk_create(backup_codes)

        return codes


def verify_backup_code(user: User, input_code: str) -> bool:
    """Verify a backup code, then mark the matched code as used."""

    with transaction.atomic():
        totp = _get_user_totp_model_obj(user)

        backup_codes = BackupCode.objects.select_for_update().filter(
            totp=totp,
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


def rotate_backup_codes(user: User) -> list[str]:
    """Generate and persist a fresh backup-code set for a user."""

    new_codes = generate_backup_codes()

    return store_backup_codes(user, new_codes)
