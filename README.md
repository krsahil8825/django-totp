# django-totp

<div align="center">

<a href="https://pypi.org/project/django-totp/">
    <img src="https://img.shields.io/pypi/v/django-totp?style=for-the-badge&logo=pypi&logoColor=white" alt="PyPI Version">
</a>

<a href="https://pypi.org/project/django-totp/">
    <img src="https://img.shields.io/pypi/pyversions/django-totp?style=for-the-badge&logo=python&logoColor=white" alt="Python Versions">
</a>

<a href="https://www.djangoproject.com/">
    <img src="https://img.shields.io/badge/Django-5.0+-092E20?style=for-the-badge&logo=django&logoColor=white" alt="Django">
</a>

<a href="https://pypi.org/project/django-totp/">
    <img src="https://img.shields.io/pypi/l/django-totp?style=for-the-badge" alt="License">
</a>

<a href="https://pepy.tech/projects/django-totp">
    <img src="https://img.shields.io/badge/dynamic/json?style=for-the-badge&label=downloads&query=%24.total_downloads&url=https%3A%2F%2Fpepy.tech%2Fapi%2Fv2%2Fprojects%2Fdjango-totp&color=blue" alt="Downloads">
</a>

<a href="https://pypi.org/project/django-totp/">
    <img src="https://img.shields.io/pypi/status/django-totp?style=for-the-badge" alt="PyPI Status">
</a>

<a href="https://djangopackages.org/packages/p/django-totp/">
    <img src="https://img.shields.io/badge/DjangoPackages-django--totp-8c3c26?style=for-the-badge" alt="Django Packages">
</a>

<a href="https://github.com/krsahil8825/django-totp">
    <img src="https://img.shields.io/github/stars/krsahil8825/django-totp?style=for-the-badge&logo=github" alt="GitHub Stars">
</a>

<a href="https://github.com/krsahil8825/django-totp/issues">
    <img src="https://img.shields.io/github/issues/krsahil8825/django-totp?style=for-the-badge&logo=github" alt="GitHub Issues">
</a>

<a href="https://github.com/krsahil8825/django-totp/commits/main">
    <img src="https://img.shields.io/github/last-commit/krsahil8825/django-totp?style=for-the-badge&logo=github" alt="Last Commit">
</a>

<a href="https://docs.astral.sh/ruff/">
    <img src="https://img.shields.io/badge/code%20style-ruff-D7FF64?style=for-the-badge&logo=ruff&logoColor=black" alt="Code Style">
</a>

</div>

Production-ready TOTP (Time-based One-Time Password) support for Django and Django REST Framework.

django-totp adds two-factor authentication (2FA) to a Django project with encrypted secret storage, QR-code enrollment, one-time backup codes, email-based account recovery, and JWT-aware login endpoints - all exposed as a small, composable set of DRF views.

This README is the single source of documentation for installation, configuration, integration, and operations.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Requirements](#requirements)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Configuration Reference](#configuration-reference)
- [API Endpoints](#api-endpoints)
- [Email Templates](#email-templates)
- [Signals](#signals)
- [Django Admin](#django-admin)
- [Integrating 2FA Into Login Flow](#integrating-2fa-into-login-flow)
- [Integrating Account Recovery](#integrating-account-recovery)
- [Security and Production Checklist](#security-and-production-checklist)
- [Troubleshooting](#troubleshooting)
- [Data Model](#data-model)
- [Public Python API](#public-python-api)
- [Interactive Helper Tools](#interactive-helper-tools)
- [Contributing](#contributing)
- [Maintainers](#maintainers)
- [License](#license)

## Overview

django-totp stores each user's TOTP secret in encrypted form and exposes API actions to:

1. Create an enrollment and return a provisioning QR code
2. Confirm enrollment with a valid OTP and receive backup codes
3. Disable TOTP, or rotate backup codes, for an already-enrolled user
4. Recover an account by email when a user has lost their TOTP device, without ever requiring the device itself

It's designed to be used as:

- A drop-in REST API module in an existing Django + DRF project
- A building block for fully custom authentication and recovery flows, via its lower-level helper functions

## Features

- Encrypted secret and backup-code storage using `cryptography.Fernet`
- Configurable issuer name shown in authenticator apps
- One-to-one user-to-TOTP mapping with cascading cleanup on disable
- Configurable number of backup codes per user, enforced at the model level
- Backup code verification with constant-time comparison and one-time-use marking
- Email-based account recovery flow for users who lose access to their TOTP device, with no enumeration of which emails exist
- Configurable rate limiting for both authenticated and anonymous endpoints, to protect against brute-force and enumeration attacks on both login and recovery surfaces
- Signed, short-lived challenge tokens for two-step login flows
- Django admin integration with masked secrets and masked backup codes
- A signal for every state-changing action, for audit logging or custom side effects

## Requirements

- Python 3.12+
- Django 5.0+
- Django REST Framework 3.15+
- djangorestframework-simplejwt 5.5.1+ (only required if you use the JWT endpoints)

Installed dependencies used by this package: `cryptography`, `pyotp`, `qrcode`.

## Installation

Install from PyPI:

```bash
pip install django-totp
```

## Quick Start

### 1. Add the app

```python
# settings.py
INSTALLED_APPS = [
    # Django apps...
    "rest_framework",
    "django_totp",
]
```

### 2. Set the encryption key (required)

Generate a Fernet key once:

```bash
python -c "from django_totp.encryption import generate_fernet_key; print(generate_fernet_key())"
```

Load it from the environment rather than hardcoding it:

```python
# settings.py
import os
TOTP_ENCRYPTION_KEY = os.environ["TOTP_ENCRYPTION_KEY"]
```

Generate this key once per environment and never rotate it casually - rotating it makes every previously encrypted TOTP secret and backup code unreadable. See [Security and Production Checklist](#security-and-production-checklist) for the full reasoning.

### 3. Include the URLs

django-totp ships three independent URL modules so you can include only what you need:

```python
# urls.py
from django.urls import include, path

urlpatterns = [
    # your routes...
    path("api/", include("django_totp.urls")),           # enroll / confirm / disable / rotate backup codes
    path("api/", include("django_totp.urls.jwt")),        # JWT login + 2FA verification
    path("api/", include("django_totp.urls.recovery")),   # email-based account recovery
]
```

All three are optional independently of each other: a project that doesn't use JWT can omit `django_totp.urls.jwt`, and a project that doesn't want self-service recovery can omit `django_totp.urls.recovery`.

### 4. Run migrations

```bash
python manage.py migrate
```

### 5. Call the endpoints

TOTP management endpoints (authenticated):

- `POST /api/totp/create/`
- `POST /api/totp/confirm/`
- `POST /api/totp/disable/`
- `POST /api/totp/rotate_backup_codes/`

TOTP recovery endpoints (unauthenticated):

- `POST /api/totp/recovery/`
- `POST /api/totp/recovery_confirm/`

JWT authentication endpoints:

- `POST /api/jwt/create/`
- `POST /api/jwt/totp/verify/`
- `POST /api/jwt/refresh/`
- `POST /api/jwt/verify/`

## Configuration Reference

All settings are optional unless marked otherwise, and are read once at import time via `getattr(settings, ...)`, with sensible defaults.

### Encryption

| Setting               | Required | Default | Purpose                                                                                                                |
| --------------------- | -------- | ------- | ---------------------------------------------------------------------------------------------------------------------- |
| `TOTP_ENCRYPTION_KEY` | Yes      | -       | Fernet key used to encrypt TOTP secrets and backup codes at rest. Raises `ImproperlyConfigured` if missing or invalid. |

### Enrollment and Backup Codes

| Setting                 | Required | Default   | Purpose                                               |
| ----------------------- | -------- | --------- | ----------------------------------------------------- |
| `TOTP_ISSUER`           | No       | `"MyApp"` | Issuer label shown inside authenticator apps.         |
| `TOTP_MAX_BACKUP_CODES` | No       | `10`      | Number of backup codes generated and stored per user. |

### Throttling

| Setting              | Required | Default       | Purpose                                                                                                                                   |
| -------------------- | -------- | ------------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| `TOTP_THROTTLE_RATE` | No       | `"10/minute"` | Rate limit applied to every django-totp endpoint, for both authenticated (`TotpUserThrottle`) and anonymous (`TotpAnonThrottle`) callers. |

> `TotpThrottle` still exists as an alias of `TotpUserThrottle` for backward compatibility, but is deprecated and will be removed in a future release. New code should depend on `TotpUserThrottle` directly.

### 2FA Login Challenge Tokens

These govern the short-lived token issued by `/api/jwt/create/` while a user is mid-login and has not yet supplied their TOTP or backup code.

| Setting              | Required                  | Default                    | Purpose                                                                                                      |
| -------------------- | ------------------------- | -------------------------- | ------------------------------------------------------------------------------------------------------------ |
| `TOTP_TOKEN_SALT`    | Recommended in production | `"django-totp-token-salt"` | Salt used when signing the challenge token. Changing it invalidates every challenge token already in flight. |
| `TOTP_TOKEN_MAX_AGE` | No                        | `120` (seconds)            | How long the challenge token remains valid after `/api/jwt/create/` is called.                               |

### Account Recovery and Email

| Setting                        | Required                  | Default                                        | Purpose                                                                                                                                                                |
| ------------------------------ | ------------------------- | ---------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `TOTP_RECOVERY_CONFIRM_URL`    | No                        | `"/totp-recovery/{uid}/{token}"`               | Path template embedded in the recovery email. `{uid}` and `{token}` are substituted automatically; point this at your frontend's recovery page, not at the API itself. |
| `TOTP_RECOVERY_EMAIL_TEMPLATE` | No                        | `"email/totp_recovery.html"`                   | Template used for the initial recovery email.                                                                                                                          |
| `TOTP_DISABLED_EMAIL_TEMPLATE` | No                        | `"email/totp_disabled.html"`                   | Template used for the confirmation email sent once TOTP has actually been disabled.                                                                                    |
| `DOMAIN`                       | Recommended in production | `"localhost:3000"`                             | Host used to build the recovery link. Point this at your frontend, not your API, if they're on different hosts.                                                        |
| `PROTOCOL`                     | Recommended in production | `"http"`                                       | Scheme used to build the recovery link. Use `"https"` in production.                                                                                                   |
| `SITE_NAME`                    | Recommended in production | `"localhost"`                                  | Display name interpolated into the email subject and body.                                                                                                             |
| `DEFAULT_FROM_EMAIL`           | Recommended in production | Django's own default (`"webmaster@localhost"`) | Sender address for both recovery emails. This is Django's built-in setting, not one defined by django-totp.                                                            |

Recovery links are signed with Django's own `default_token_generator` (the same mechanism Django uses for password resets), not with `TOTP_TOKEN_SALT` / `TOTP_TOKEN_MAX_AGE` - those two only govern the separate, much shorter-lived 2FA login challenge token described above. As a result, recovery link expiry is controlled by Django's native `PASSWORD_RESET_TIMEOUT` setting (3 days by default), and a recovery link is automatically invalidated the moment the user's password changes.

### DRF and JWT Integration

Required only if you're using the JWT endpoints:

```python
# settings.py
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
}

from datetime import timedelta

SIMPLE_JWT = {
    "AUTH_HEADER_TYPES": ("Bearer",),
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=20),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=1),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    # other settings as needed...
}
```

See the [djangorestframework-simplejwt settings reference](https://django-rest-framework-simplejwt.readthedocs.io/en/latest/settings.html) for the full list of available options.

## API Endpoints

All endpoints return error payloads as JSON with a `detail` field, unless otherwise noted.

### TOTP Management Endpoints

A user enables TOTP by calling `create` to receive a QR code, then `confirm` with a valid OTP to finalize enrollment and receive backup codes. All four endpoints require an authenticated user.

#### `POST /api/totp/create/`

Starts TOTP enrollment, creating an encrypted secret and returning a QR-code SVG.

Request body: empty.

Success response (201):

```json
{ "svg": "<svg ...>...</svg>" }
```

Error examples (400): TOTP already exists for this user.

#### `POST /api/totp/confirm/`

Confirms enrollment using a valid code from an authenticator app and returns backup codes.

Request body:

```json
{ "input_code": "123456" }
```

Success response (200):

```json
{ "backup_codes": ["code1", "code2", "..."] }
```

Error examples (400): user has no associated TOTP secret; invalid TOTP code.

#### `POST /api/totp/disable/`

Disables TOTP and deletes associated backup codes.

Request body: empty.

Success response: 204 No Content.

Error examples (400): user has no associated TOTP secret.

#### `POST /api/totp/rotate_backup_codes/`

Replaces all existing backup codes with a new set.

Request body: empty.

Success response (200):

```json
{ "backup_codes": ["new1", "new2", "..."] }
```

### TOTP Recovery Endpoints

These two endpoints exist for users who have lost their TOTP device and therefore can't satisfy a normal authenticated request. Both are unauthenticated by design, and both are throttled for anonymous as well as authenticated callers.

#### `POST /api/totp/recovery/`

Sends a recovery email if, and only if, an account with the given email exists and has TOTP enabled - but the response is identical either way, to avoid leaking which emails are registered.

Request body:

```json
{ "email": "user@example.com" }
```

Success response (200), always returned regardless of whether the account exists:

```json
{ "details": "If an account with that email exists and has TOTP enabled, a recovery email has been sent." }
```

#### `POST /api/totp/recovery_confirm/`

Validates the signed `uid`/`token` pair from the recovery email together with the account's current password, then disables TOTP on the account and sends a confirmation email.

Request body:

```json
{ "uid": "...", "token": "...", "password": "current_account_password" }
```

Success response: 204 No Content.

Error examples (400):

```json
{ "message": ["The recovery link is invalid or has expired."] }
```

```json
{ "message": ["The provided credentials is invalid."] }
```

> Requiring the account's current password here, in addition to the signed link, means a leaked or intercepted recovery email alone is not enough to disable a user's 2FA.

### JWT Authentication Endpoints

Use these when django-totp is integrated with JWT authentication, for 2FA-aware token issuance.

#### `POST /api/jwt/create/`

Initiates login with username and password. Returns JWT tokens directly if the user has no TOTP enabled, or a challenge token if 2FA is required.

Request body:

```json
{ "username": "user@example.com", "password": "secure_password" }
```

Success response (200) - no TOTP enabled:

```json
{ "is_totp_enabled": false, "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc...", "access": "eyJ0eXAiOiJKV1QiLCJhbGc..." }
```

Success response (200) - TOTP enabled:

```json
{ "is_totp_enabled": true, "totp_challenge_token": "eyJ0eXAiOiJKV1QiLCJhbGc..." }
```

Error examples (401): invalid username/password combination.

#### `POST /api/jwt/totp/verify/`

Verifies a TOTP code or backup code and returns JWT tokens. Must be called after `/api/jwt/create/` when TOTP is enabled.

Request body (TOTP code):

```json
{ "totp_challenge_token": "...", "otp_code": "123456" }
```

Request body (backup code):

```json
{ "totp_challenge_token": "...", "backup_code": "BACKUP-CODE-1" }
```

Success response (200):

```json
{ "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc...", "access": "eyJ0eXAiOiJKV1QiLCJhbGc..." }
```

Error examples (400): invalid or expired challenge token; invalid TOTP code; invalid backup code, and both or neither otp_code and backup_code is provided in the same request.

#### `POST /api/jwt/refresh/`

Refreshes an expired access token using a valid refresh token.

Request body:

```json
{ "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..." }
```

Success response (200):

```json
{ "access": "eyJ0eXAiOiJKV1QiLCJhbGc...", "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..." }
```

#### `POST /api/jwt/verify/`

Verifies the validity of an access or refresh token.

Request body:

```json
{ "token": "eyJ0eXAiOiJKV1QiLCJhbGc..." }
```

Success response (200): an empty body indicates a valid token.

## Email Templates

Both recovery emails are rendered from a single Django template per email, split into named blocks rather than separate subject/body files:

| Block                           | Used for                                                               |
| ------------------------------- | ---------------------------------------------------------------------- |
| &#123;% block subject %&#125;   | Email subject line                                                     |
| &#123;% block text_body %&#125; | Plain-text body (always attached)                                      |
| &#123;% block html_body %&#125; | HTML alternative (attached if both bodies render to non-empty content) |

Override either template by placing a file at the same relative path earlier in your template loader's search order, or by pointing `TOTP_RECOVERY_EMAIL_TEMPLATE` / `TOTP_DISABLED_EMAIL_TEMPLATE` at a different path entirely. Available context variables:

- `totp_recovery.html`: `site_name`, `protocol`, `domain`, `url`, `user`
- `totp_disabled.html`: `site_name`, `user`

`EMAIL_BACKEND` is read from your own Django settings as usual - django-totp doesn't configure one for you, so use the console or file-based backend in development and a real transactional backend in production.

## Signals

django-totp sends the following signals via `send_robust`, so a failing receiver never breaks the request itself:

- `totp_created`: sent after a new TOTP enrollment is confirmed.
- `totp_disabled`: sent after TOTP is disabled, whether by the user directly or via account recovery.
- `backup_codes_rotated`: sent after backup codes are rotated.
- `totp_login_succeeded`: sent after a successful 2FA verification (TOTP code or backup code) during login.
- `non_totp_login_succeeded`: sent after a successful login for a user who doesn't have TOTP enabled.
- `totp_recovery_succeeded`: sent after a successful account recovery, immediately before `totp_disabled` fires for the same request.

```python
# example signal handler
from django.dispatch import receiver
from django_totp.signals import totp_created

@receiver(totp_created)
def handle_totp_created(sender, request, user, **kwargs):
    # Custom logic after TOTP enrollment creation
    print(f"TOTP created for user: {user.username}")
```

## Django Admin

Registering `django_totp` gives you an admin view for the `Totp` model out of the box, with no extra wiring. It lists each user's email, username, and a live `used/total` backup-code count, and shows backup codes inline. Both the TOTP secret and every backup code are masked in the admin (only the first four encrypted characters are shown) - the underlying encrypted values are never exposed, and there's no way to retrieve a plaintext secret or code through the admin.

## Integrating 2FA Into Login Flow

Typical two-step login flow:

1. Validate username/password via `/api/jwt/create/`.
2. If the user has TOTP enabled, the response carries a short-lived signed challenge token instead of tokens.
3. Prompt the user for a TOTP code or backup code.
4. Submit it, along with the challenge token, to `/api/jwt/totp/verify/`.
5. Issue final JWTs only after that verification succeeds.

## Integrating Account Recovery

Typical recovery flow for a user who has lost their TOTP device:

1. The user submits their email to `/api/totp/recovery/`. The response is identical whether or not the account exists or has TOTP enabled, so the frontend should show the same message either way.
2. If eligible, the user receives an email containing a link built from `TOTP_RECOVERY_CONFIRM_URL`, pointed at your frontend.
3. Your frontend's recovery page extracts `uid` and `token` from the URL and prompts for the account's current password.
4. The frontend submits `uid`, `token`, and `password` to `/api/totp/recovery_confirm/`.
5. On success, TOTP is disabled on the account, a confirmation email is sent, and the user can log in normally (without 2FA) and re-enroll a new device.

## Security and Production Checklist

### Configure the Encryption Key Correctly

`TOTP_ENCRYPTION_KEY` encrypts every stored TOTP secret and backup code.

- Store it in an environment variable or a secret manager, never in source control.
- Generate it once and reuse the same value across deployments and restarts.
- Do not rotate it after users have enrolled unless you intend to invalidate all existing encrypted data - rotation makes previously encrypted secrets and backup codes permanently unreadable.

### Use HTTPS in Production

Serve every authentication-related endpoint over HTTPS - TOTP setup, recovery, and JWT endpoints alike. Never expose OTP codes, challenge tokens, recovery links, or JWTs over plain HTTP. Set `PROTOCOL = "https"` so recovery links reflect this too.

### Configure Throttling

Keep `TOTP_THROTTLE_RATE` strict for both login and recovery surfaces, since both are realistic targets for brute-force and enumeration attempts:

```python
TOTP_THROTTLE_RATE = "5/minute"
```

### Handle Backup Codes Securely

Backup codes are recovery credentials and should be treated like passwords: show them only once, at generation or rotation time, ask users to store them securely, and never log or expose them in plaintext anywhere - debug responses, monitoring, or error traces included.

### Handle OTP Codes Securely

Never log a submitted OTP code, never persist it, and keep it out of debugging tools and error traces.

### Configure Challenge Token Expiry Carefully

`TOTP_TOKEN_MAX_AGE` controls how long the 2FA login challenge token stays valid (default `120` seconds). Keep this short; there's little reason to extend it significantly in production.

### Configure the Token Salt Before Production

`TOTP_TOKEN_SALT` signs the 2FA login challenge token. Change the default value before going live, then keep it stable - changing it later invalidates every challenge token currently in flight (which only matters for the few seconds a user is mid-login, so this is low-risk to rotate if needed).

### Configure Recovery Email Settings Correctly

Point `DOMAIN` and `PROTOCOL` at your actual frontend, not at the Django backend, so the link inside the recovery email lands on a page that can read `uid`/`token` and submit them. Recovery requires the user's current password in addition to the link, but it's still worth treating recovery emails with the same care as password-reset emails.

### Keep Dependencies Updated

Apply security updates promptly for Django, `cryptography`, `pyotp`, `djangorestframework`, and `djangorestframework-simplejwt`.

## Troubleshooting

### `ImproperlyConfigured: TOTP_ENCRYPTION_KEY must be set`

Cause: missing or invalid Fernet key.

Fix: generate a valid Fernet key, set `TOTP_ENCRYPTION_KEY` in the environment, and restart the application.

### Confirm endpoint always returns "Invalid TOTP code"

Possible causes: device clock drift, the wrong issuer/account was scanned, or the code was submitted after it expired.

Fixes: make sure the server's clock is synchronized via NTP; re-run enrollment and rescan the QR code; submit the currently active code from the authenticator app.

### Backup code rejected

Cause: the code was already used (each backup code is one-time-use), or there's a copy/paste whitespace mismatch.

Fix: rotate backup codes and redistribute them securely.

### Recovery link is invalid or has expired

Possible causes: the link is older than Django's `PASSWORD_RESET_TIMEOUT` (3 days by default), the account's password changed after the link was issued, or the link has already been used once.

Fix: request a new recovery email via `/api/totp/recovery/`.

## Data Model

django_totp defines two models:

- `Totp`
  - `user` - one-to-one with `AUTH_USER_MODEL`
  - `secret_key` - encrypted
  - `created_at`
- `BackupCode`
  - `totp` - foreign key to `Totp`
  - `code` - encrypted
  - `is_used`
  - `created_at`

## Public Python API

Helpers you can import directly, for building custom flows on top of the same primitives the bundled views use:

- `django_totp.auth`
  - `is_totp_enabled(user)`
  - `generate_challenge_token(user)`
  - `verify_challenge_token(token)`
  - `get_user_from_challenge_token(token)`
- `django_totp.totp`
  - `generate_totp_secret()`
  - `verify_totp_code(user, input_code)`
  - `create_totp_setup(user)`
  - `confirm_totp_setup(user, input_code)`
  - `disable_totp(user)`
- `django_totp.backup_code_utils`
  - `store_backup_codes(user, codes)`
  - `verify_backup_code(user, input_code)`
  - `rotate_backup_codes(user)`
- `django_totp.email`
  - `TotpRecoveryEmail(request, context)`
  - `TotpDisabledEmail(request, context)`
- `django_totp.email_utils`
  - `encode_uid(pk)`
  - `decode_uid(uid)`
- `django_totp.encryption`
  - `generate_fernet_key()`
  - `resolve_fernet_key(default=None)`
  - `encrypt(value)`
  - `decrypt(value)`

## Interactive Helper Tools

Utilities for development, debugging, and response inspection:

- **SVG Viewer** - render and inspect the SVG payload returned by the TOTP `create` endpoint.
- **JSON to TXT Converter** - convert backup-code JSON responses into a plain-text downloadable file.

Available at: https://django-totp-helper.pages.dev/

## Contributing

Contributions are welcome. Please open an issue for bugs or feature requests, and submit pull requests for improvements.

## Maintainers

- Kumar Sahil
  - GitHub: [@krsahil8825](https://github.com/krsahil8825)
  - Email: [krsahil8825@gmail.com](mailto:krsahil8825@gmail.com)

## License

MIT License. See [LICENSE](LICENSE) for details.
