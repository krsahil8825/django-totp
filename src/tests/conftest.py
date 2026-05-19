import itertools

import pyotp
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from django_totp.auth import generate_challenge_token
from django_totp.backup_code_utils import store_backup_codes
from django_totp.encryption import encrypt
from django_totp.models import Totp


DEFAULT_PASSWORD = "Passw0rd!123"
CLIENT_SEQUENCE = itertools.count(1)


@pytest.fixture
def api_client():
    return APIClient(REMOTE_ADDR=f"127.0.0.{next(CLIENT_SEQUENCE)}")


@pytest.fixture
def password():
    return DEFAULT_PASSWORD


@pytest.fixture
def make_user(password):
    user_model = get_user_model()
    sequence = itertools.count(1)

    def factory(*, username=None, raw_password=None, **extra_fields):
        return user_model.objects.create_user(
            username=username or f"user-{next(sequence)}",
            password=raw_password or password,
            **extra_fields,
        )

    return factory


@pytest.fixture
def user(make_user):
    return make_user(username="plain-user")


@pytest.fixture
def totp_secret():
    return pyotp.random_base32()


@pytest.fixture
def totp_user(make_user, totp_secret):
    user = make_user(username="totp-user")
    Totp.objects.create(user=user, secret_key=encrypt(totp_secret))
    return user


@pytest.fixture
def totp_code(totp_secret):
    return pyotp.TOTP(totp_secret).now()


@pytest.fixture
def backup_codes():
    return ["backup-code-1", "backup-code-2", "backup-code-3"]


@pytest.fixture
def totp_user_with_backup_codes(totp_user, backup_codes):
    store_backup_codes(totp_user, backup_codes)
    return totp_user


@pytest.fixture
def challenge_token(totp_user):
    return generate_challenge_token(totp_user)