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


class JWTCreateSerializer(serializers.Serializer):
    """Serializer for JWT authentication request."""

    username = serializers.CharField(write_only=True)
    password = serializers.CharField(write_only=True)

    is_totp_enabled = serializers.BooleanField(read_only=True, default=False)
    access = serializers.CharField(read_only=True, required=False)
    refresh = serializers.CharField(read_only=True, required=False)
    totp_challenge_token = serializers.CharField(read_only=True, required=False)


class JWT2FAVerifySerializer(serializers.Serializer):
    """Serializer for JWT 2FA verification request."""

    totp_challenge_token = serializers.CharField(write_only=True)
    otp_code = serializers.CharField(required=False, write_only=True)
    backup_code = serializers.CharField(required=False, write_only=True)

    access = serializers.CharField(read_only=True)
    refresh = serializers.CharField(read_only=True)

    def validate(self, attrs):
        otp_code = attrs.get("otp_code").strip() if attrs.get("otp_code") else None
        backup_code = (
            attrs.get("backup_code").strip() if attrs.get("backup_code") else None
        )

        if not otp_code and not backup_code:
            raise serializers.ValidationError(
                "Either otp_code or backup_code is required."
            )
        
        if otp_code and backup_code:
            raise serializers.ValidationError(
                "Provide only one of otp_code or backup_code, not both."
            )

        return attrs
