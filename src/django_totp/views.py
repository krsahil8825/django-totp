"""DRF view layer for TOTP enrollment and verification endpoints."""

from django.contrib.auth import authenticate
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from .auth import (
    generate_challenge_token,
    get_user_from_challenge_token,
    is_totp_enabled,
)
from .backup_code_utils import rotate_backup_codes, verify_backup_code
from .serializers import (
    BackupCodeListSerializer,
    EmptySerializer,
    JWTCreateSerializer,
    JWT2FAVerifySerializer,
    TotpConfirmRequestSerializer,
    TotpCreateResponseSerializer,
)
from .totp import create_totp_setup, confirm_totp_setup, disable_totp, verify_totp_code
from .throttle import TotpThrottle


class TotpViewSet(viewsets.GenericViewSet):
    """Expose TOTP enrollment, confirmation, and recovery endpoints."""

    permission_classes = [IsAuthenticated]
    throttle_classes = [TotpThrottle]

    def get_serializer_class(self):
        """Return the serializer that matches the current action."""

        if self.action == "enroll":
            return TotpCreateResponseSerializer
        elif self.action == "confirm":
            return TotpConfirmRequestSerializer
        elif self.action == "disable":
            return EmptySerializer
        elif self.action == "rotate_backup_codes":
            return BackupCodeListSerializer
        return super().get_serializer_class()

    @action(detail=False, methods=["post"], url_path="create", url_name="create")
    def enroll(self, request):
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


class JWTCreateView(GenericAPIView):
    permission_classes = [AllowAny]
    serializer_class = JWTCreateSerializer
    throttle_classes = [TotpThrottle]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = authenticate(
            request,
            username=serializer.validated_data["username"],
            password=serializer.validated_data["password"],
        )

        if not user:
            return Response(
                {"detail": "Invalid credentials."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # User does not have totp enabled
        if not is_totp_enabled(user):
            refresh = RefreshToken.for_user(user)

            serializer = self.get_serializer(
                {
                    "is_totp_enabled": False,
                    "refresh": str(refresh),
                    "access": str(refresh.access_token),
                }
            )

            return Response(
                serializer.data,
                status=status.HTTP_200_OK,
            )

        # User has totp enabled
        challenge_token = generate_challenge_token(user)

        serializer = self.get_serializer(
            {"is_totp_enabled": True, "totp_challenge_token": challenge_token}
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )


class JWTTOTP2FAVerifyView(GenericAPIView):
    permission_classes = [AllowAny]
    serializer_class = JWT2FAVerifySerializer
    throttle_classes = [TotpThrottle]

    def post(self, request, *args, **kwargs):

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        challenge_token = serializer.validated_data["totp_challenge_token"]

        otp_code = serializer.validated_data.get("otp_code")
        backup_code = serializer.validated_data.get("backup_code")

        try:
            user = get_user_from_challenge_token(challenge_token)
        except Exception:
            return Response(
                {"detail": "Invalid or expired challenge token."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # fallback check
        if not is_totp_enabled(user):
            return Response(
                {"detail": "TOTP is not enabled for this user."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        verified = False

        if otp_code:
            verified = verify_totp_code(user, otp_code)
        elif backup_code:
            verified = verify_backup_code(user, backup_code)

        if not verified:
            return Response(
                {"detail": "Invalid 2FA code."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        refresh = RefreshToken.for_user(user)

        serializer = self.get_serializer(
            {
                "refresh": str(refresh),
                "access": str(refresh.access_token),
            }
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )
