from django.conf import settings as django_settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models

MAX_BACKUP_CODES = getattr(django_settings, "TOTP_MAX_BACKUP_CODES", 10)

User = get_user_model()


class Totp(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="totp")
    secret_key = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"TOTP for {self.user.username}"


class BackupCode(models.Model):
    totp = models.ForeignKey(
        Totp, on_delete=models.CASCADE, related_name="backup_codes"
    )
    code = models.CharField(max_length=255)
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        if BackupCode.objects.filter(totp=self.totp).count() >= MAX_BACKUP_CODES:
            raise ValidationError(
                f"Cannot create more than {MAX_BACKUP_CODES} backup codes for a user."
            )
        return super().clean()

    def __str__(self):
        return f"Backup code for {self.totp.user.username} - {'Used' if self.is_used else 'Unused'}"
