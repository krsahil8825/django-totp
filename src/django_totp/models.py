"""Database models for Django TOTP secrets and backup codes."""

from django.conf import settings as django_settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models

MAX_BACKUP_CODES = int(getattr(django_settings, "TOTP_MAX_BACKUP_CODES", 10))

User = get_user_model()


class Totp(models.Model):
    """Persist the encrypted TOTP secret for a user."""

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="totp")
    secret_key = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"TOTP for {self.user.get_username()}"


class BackupCode(models.Model):
    """Store a single encrypted backup code for a user's TOTP account."""

    totp = models.ForeignKey(
        Totp, on_delete=models.CASCADE, related_name="backup_codes"
    )
    code = models.CharField(max_length=255)
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        if (
            self.totp_id is not None
            and BackupCode.objects.filter(totp=self.totp).exclude(pk=self.pk).count()
            >= MAX_BACKUP_CODES
        ):
            raise ValidationError(
                f"A user cannot have more than {MAX_BACKUP_CODES} backup codes."
            )
        return super().clean()

    def __str__(self) -> str:
        status = "used" if self.is_used else "unused"
        return f"Backup code for {self.totp.user.get_username()} ({status})"
