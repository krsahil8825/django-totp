"""
django_totp.backup_code
=======================

This module provides functionality to generate backup codes for TOTP authentication.
"""

import secrets
from typing import List
from .models import MAX_BACKUP_CODES


def generate_backup_codes() -> List[str]:
    """
    Generate a list of unique backup codes.

    Returns:
        List[str]: A list of backup codes.
    """

    return [secrets.token_urlsafe(12) for _ in range(MAX_BACKUP_CODES)]
