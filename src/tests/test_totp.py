import pytest
from django.urls import reverse
from rest_framework import status

from django_totp.encryption import decrypt
from django_totp.models import BackupCode, MAX_BACKUP_CODES, Totp


pytestmark = pytest.mark.django_db


class PostTotpCreate:
    def test_creates_totp_and_returns_svg(self, api_client, user):
        api_client.force_authenticate(user=user)

        response = api_client.post(reverse("totp-create"), {}, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert "<svg" in response.data["svg"]
        assert Totp.objects.filter(user=user).exists()

    def test_rejects_when_totp_already_exists(self, api_client, totp_user):
        api_client.force_authenticate(user=totp_user)

        response = api_client.post(reverse("totp-create"), {}, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["detail"] == "TOTP already exists for this user."

    def test_requires_authentication(self, api_client):
        response = api_client.post(reverse("totp-create"), {}, format="json")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class PostTotpConfirm:
    def test_confirms_enrollment_and_returns_backup_codes(
        self,
        api_client,
        totp_user,
        totp_code,
    ):
        api_client.force_authenticate(user=totp_user)

        response = api_client.post(
            reverse("totp-confirm"),
            {"input_code": totp_code},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["backup_codes"]) == MAX_BACKUP_CODES
        assert BackupCode.objects.filter(totp__user=totp_user).count() == MAX_BACKUP_CODES

    def test_rejects_invalid_totp_code(self, api_client, totp_user):
        api_client.force_authenticate(user=totp_user)

        response = api_client.post(
            reverse("totp-confirm"),
            {"input_code": "000000"},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["detail"] == "Invalid TOTP code."

    def test_rejects_when_no_totp_secret_exists(self, api_client, user):
        api_client.force_authenticate(user=user)

        response = api_client.post(
            reverse("totp-confirm"),
            {"input_code": "000000"},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["detail"] == "User does not have an associated TOTP secret."

    def test_rejects_when_backup_codes_already_exist(
        self,
        api_client,
        totp_user_with_backup_codes,
        totp_code,
    ):
        api_client.force_authenticate(user=totp_user_with_backup_codes)

        response = api_client.post(
            reverse("totp-confirm"),
            {"input_code": totp_code},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["detail"] == "Backup codes already exist for this user."


class PostTotpDisable:
    def test_disables_totp_and_removes_backup_codes(
        self,
        api_client,
        totp_user_with_backup_codes,
    ):
        api_client.force_authenticate(user=totp_user_with_backup_codes)

        response = api_client.post(reverse("totp-disable"), {}, format="json")

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Totp.objects.filter(user=totp_user_with_backup_codes).exists()
        assert not BackupCode.objects.filter(totp__user=totp_user_with_backup_codes).exists()

    def test_rejects_when_totp_secret_is_missing(self, api_client, user):
        api_client.force_authenticate(user=user)

        response = api_client.post(reverse("totp-disable"), {}, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["detail"] == "User does not have an associated TOTP secret."


class PostTotpRotateBackupCodes:
    def test_rotates_and_replaces_backup_codes(
        self,
        api_client,
        totp_user_with_backup_codes,
        monkeypatch,
    ):
        api_client.force_authenticate(user=totp_user_with_backup_codes)

        new_codes = [
            "new-backup-code-1",
            "new-backup-code-2",
            "new-backup-code-3",
            "new-backup-code-4",
            "new-backup-code-5",
            "new-backup-code-6",
            "new-backup-code-7",
            "new-backup-code-8",
            "new-backup-code-9",
            "new-backup-code-10",
        ]
        monkeypatch.setattr(
            "django_totp.backup_code_utils.generate_backup_codes", lambda: new_codes
        )

        response = api_client.post(
            reverse("totp-rotate-backup-codes"),
            {},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["backup_codes"] == new_codes
        assert BackupCode.objects.filter(totp__user=totp_user_with_backup_codes).count() == MAX_BACKUP_CODES
        assert [
            decrypt(code.code)
            for code in BackupCode.objects.filter(
                totp__user=totp_user_with_backup_codes
            ).order_by("id")
        ] == new_codes

    def test_rejects_when_totp_secret_is_missing(self, api_client, user):
        api_client.force_authenticate(user=user)

        response = api_client.post(reverse("totp-rotate-backup-codes"), {}, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["detail"] == "User does not have an associated TOTP secret."