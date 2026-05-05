"""Public API for django_totp—a TOTP authentication helper for Django.

Essential methods for TOTP enrollment and verification:
- create_totp_setup: Initiate TOTP enrollment
- confirm_totp_setup: Complete enrollment and get backup codes
- generate_fernet_key: Generate a new Fernet key
- verify_totp_code: Verify a user's one-time code
- disable_totp: Remove TOTP for a user
- verify_backup_code: Verify a backup code
- rotate_backup_codes: Generate new backup codes
"""

from .backup_code_utils import (
    rotate_backup_codes,
    verify_backup_code,
)
from .encryption import generate_fernet_key
from .totp import (
    confirm_totp_setup,
    create_totp_setup,
    disable_totp,
    verify_totp_code,
)

__all__ = [
    "confirm_totp_setup",
    "create_totp_setup",
    "disable_totp",
    "generate_fernet_key",
    "rotate_backup_codes",
    "verify_backup_code",
    "verify_totp_code",
]
