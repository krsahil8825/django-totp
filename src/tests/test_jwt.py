import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from django_totp.auth import generate_challenge_token, get_user_from_challenge_token


pytestmark = pytest.mark.django_db


class PostJwtCreate:
    def test_returns_token_pair_for_user_without_totp(self, api_client, user, password):
        response = api_client.post(
            reverse("jwt-create"),
            {"username": user.username, "password": password},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["is_totp_enabled"] is False
        assert response.data["access"]
        assert response.data["refresh"]
        assert "totp_challenge_token" not in response.data

    def test_returns_challenge_token_for_user_with_totp(
        self,
        api_client,
        totp_user,
        password,
    ):
        response = api_client.post(
            reverse("jwt-create"),
            {"username": totp_user.username, "password": password},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["is_totp_enabled"] is True
        assert response.data["totp_challenge_token"]
        assert "access" not in response.data
        assert "refresh" not in response.data
        assert get_user_from_challenge_token(response.data["totp_challenge_token"]) == totp_user

    def test_rejects_invalid_credentials(self, api_client, user):
        response = api_client.post(
            reverse("jwt-create"),
            {"username": user.username, "password": "wrong-password"},
            format="json",
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.data["detail"] == "Invalid credentials."

    def test_rejects_missing_password(self, api_client, user):
        response = api_client.post(
            reverse("jwt-create"),
            {"username": user.username},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "password" in response.data


class PostJwtRefresh:
    def test_returns_new_tokens_for_valid_refresh_token(self, api_client, user):
        refresh = RefreshToken.for_user(user)

        response = api_client.post(
            reverse("jwt-refresh"),
            {"refresh": str(refresh)},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["access"]
        assert response.data["refresh"]

    def test_rejects_invalid_refresh_token(self, api_client):
        response = api_client.post(
            reverse("jwt-refresh"),
            {"refresh": "not-a-valid-refresh-token"},
            format="json",
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_rejects_missing_refresh_token(self, api_client):
        response = api_client.post(reverse("jwt-refresh"), {}, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "refresh" in response.data


class PostJwtVerify:
    def test_accepts_valid_token(self, api_client, user):
        token = RefreshToken.for_user(user)

        response = api_client.post(
            reverse("jwt-verify"),
            {"token": str(token)},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK

    def test_rejects_invalid_token(self, api_client):
        response = api_client.post(
            reverse("jwt-verify"),
            {"token": "not-a-valid-token"},
            format="json",
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_rejects_missing_token(self, api_client):
        response = api_client.post(reverse("jwt-verify"), {}, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "token" in response.data


class PostJwtTotpVerify:
    def test_returns_tokens_with_otp_code(
        self,
        api_client,
        challenge_token,
        totp_code,
    ):
        response = api_client.post(
            reverse("jwt-totp-verify"),
            {
                "totp_challenge_token": challenge_token,
                "otp_code": totp_code,
            },
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["access"]
        assert response.data["refresh"]

    def test_returns_tokens_with_backup_code(
        self,
        api_client,
        totp_user_with_backup_codes,
        backup_codes,
    ):
        response = api_client.post(
            reverse("jwt-totp-verify"),
            {
                "totp_challenge_token": generate_challenge_token(totp_user_with_backup_codes),
                "backup_code": backup_codes[0],
            },
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["access"]
        assert response.data["refresh"]

    def test_rejects_invalid_challenge_token(self, api_client):
        response = api_client.post(
            reverse("jwt-totp-verify"),
            {
                "totp_challenge_token": "tampered-token",
                "otp_code": "123456",
            },
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["detail"] == "Invalid or expired challenge token."

    def test_rejects_when_totp_is_not_enabled(self, api_client, user):
        response = api_client.post(
            reverse("jwt-totp-verify"),
            {
                "totp_challenge_token": generate_challenge_token(user),
                "otp_code": "123456",
            },
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["detail"] == "TOTP is not enabled for this user."

    def test_rejects_invalid_two_factor_code(self, api_client, challenge_token):
        response = api_client.post(
            reverse("jwt-totp-verify"),
            {
                "totp_challenge_token": challenge_token,
                "otp_code": "000000",
            },
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["detail"] == "Invalid 2FA code."

    def test_rejects_when_both_codes_are_provided(self, api_client, challenge_token):
        response = api_client.post(
            reverse("jwt-totp-verify"),
            {
                "totp_challenge_token": challenge_token,
                "otp_code": "123456",
                "backup_code": "backup-code",
            },
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Provide only one of otp_code or backup_code, not both." in str(
            response.data
        )

    def test_rejects_when_no_code_is_provided(self, api_client, challenge_token):
        response = api_client.post(
            reverse("jwt-totp-verify"),
            {"totp_challenge_token": challenge_token},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Either otp_code or backup_code is required." in str(response.data)