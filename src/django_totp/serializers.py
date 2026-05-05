"""Serializer definitions for the django_totp API layer."""

from rest_framework import serializers


class TotpCreateResponseSerializer(serializers.Serializer):
    """Serialized response for TOTP enrollment initiation."""

    svg = serializers.CharField(read_only=True)


class BackupCodeListSerializer(serializers.Serializer):
    """Serialized response containing plaintext backup codes."""

    backup_codes = serializers.ListField(
        child=serializers.CharField(),
        read_only=True,
    )


class TotpConfirmRequestSerializer(BackupCodeListSerializer):
    """Request payload used to confirm a TOTP enrollment."""

    input_code = serializers.CharField(trim_whitespace=True, write_only=True)