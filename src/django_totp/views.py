"""DRF view layer for TOTP enrollment and verification endpoints."""

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .backup_code_utils import rotate_backup_codes
from .serializers import (
    BackupCodeListSerializer,
    TotpConfirmRequestSerializer,
    TotpCreateResponseSerializer,
)
from .totp import create_totp_setup, confirm_totp_setup, disable_totp
from .throttle import TotpThrottle


class TotpViewSet(viewsets.GenericViewSet):
    """Expose TOTP enrollment, confirmation, and recovery endpoints."""

    permission_classes = [IsAuthenticated]
    throttle_classes = [TotpThrottle]

    def get_serializer_class(self):
        """Return the serializer that matches the current action."""

        if self.action == "create":
            return TotpCreateResponseSerializer
        elif self.action == "confirm":
            return TotpConfirmRequestSerializer
        elif self.action == "disable":
            return None
        elif self.action == "rotate_backup_codes":
            return BackupCodeListSerializer
        return super().get_serializer_class()

    @action(detail=False, methods=["post"])
    def create(self, request):
        """Start TOTP enrollment and return the provisioning QR code."""

        try:
            svg = create_totp_setup(request.user)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        serializer = self.get_serializer({"svg": svg})

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["post"])
    def confirm(self, request):
        """Confirm TOTP enrollment and return backup codes."""

        request_serializer = self.get_serializer(data=request.data)
        request_serializer.is_valid(raise_exception=True)

        input_code = request_serializer.validated_data["input_code"]

        try:
            backup_codes = confirm_totp_setup(request.user, input_code)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        response_serializer = self.get_serializer({"backup_codes": backup_codes})

        return Response(response_serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["post"])
    def disable(self, request):
        """Disable TOTP for the authenticated user."""

        try:
            disable_totp(request.user)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=["post"])
    def rotate_backup_codes(self, request):
        """Generate a new backup-code set for the authenticated user."""

        new_codes = rotate_backup_codes(request.user)

        response_serializer = self.get_serializer({"backup_codes": new_codes})

        return Response(response_serializer.data, status=status.HTTP_200_OK)
