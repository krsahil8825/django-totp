"""Generate plaintext backup codes for TOTP authentication."""

import secrets
from typing import List

from .models import MAX_BACKUP_CODES


def generate_backup_codes() -> List[str]:
    """Return a new batch of unique, plaintext backup codes."""

    return [secrets.token_urlsafe(12) for _ in range(MAX_BACKUP_CODES)]
