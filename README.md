# django-totp

Production-ready TOTP (Time-based One-Time Password) support for Django and Django REST Framework.

django-totp helps you add two-factor authentication (2FA) to your Django project with:

- Secure TOTP secret storage (Fernet encryption)
- Enrollment QR generation (SVG)
- Backup code generation, verification, and rotation
- DRF endpoints for enrollment lifecycle
- Token helpers for two-step authentication flows

This README is the single source of documentation for installation, configuration, integration, and operations.

## Table of Contents

- Overview
- Features
- Requirements
- Installation
- Quick Start
- Configuration Reference
- API Endpoints
- Integrating 2FA Into Login Flow
- Security and Production Checklist
- Troubleshooting
- Data Model
- Public Python API

## Overview

django-totp stores each user's TOTP secret in encrypted form and provides API actions to:

1. Create enrollment and return a QR code
2. Confirm enrollment using a valid OTP
3. Return one-time backup recovery codes
4. Rotate backup codes
5. Disable TOTP

You can use it as:

- A drop-in REST API module in an existing Django + DRF project
- A building block for custom authentication endpoints

## Features

- Encrypted secret storage using cryptography.Fernet
- Configurable issuer name for authenticator apps
- One-to-one user-to-TOTP mapping
- Configurable number of backup codes per user
- Backup code verification with one-time-use marking
- Rate limiting for TOTP endpoints
- Signed short-lived token helpers for step-up login flows

## Requirements

- Python 3.12+
- Django 5.0+
- Django REST Framework 3.15+

Installed dependencies used by this package:

- cryptography
- pyotp
- qrcode

## Installation

Install from PyPI:

    pip install django-totp

## Quick Start

### 1. Add apps

In Django settings:

    INSTALLED_APPS = [
    	# Django apps...
    	"rest_framework",
    	"django_totp",
    ]

### 2. Set encryption key (required)

Generate a Fernet key once:

    python -c "from django_totp.encryption import generate_fernet_key; print(generate_fernet_key())"

Add it as an environment variable:

    TOTP_ENCRYPTION_KEY=your-generated-key

And load in settings:

    import os
    TOTP_ENCRYPTION_KEY = os.environ["TOTP_ENCRYPTION_KEY"]

Important:

- Do not generate a new key on each start in production
- Changing this key later makes previously encrypted TOTP data unreadable

### 3. Include URLs

In your project URL configuration:

    from django.urls import include, path

    urlpatterns = [
    	# your routes...
    	path("api/", include("django_totp.urls")),
    ]

### 4. Run migrations

    python manage.py migrate

### 5. Call endpoints as authenticated user

Enrollment create:

    POST /api/totp/create/

Confirm enrollment:

    POST /api/totp/confirm/

Disable TOTP:

    POST /api/totp/disable/

Rotate backup codes:

    POST /api/totp/rotate_backup_codes/

## Configuration Reference

All settings below are read from Django settings.

### TOTP_ENCRYPTION_KEY

- Required: Yes
- Type: string (valid Fernet key)
- Purpose: Encrypts TOTP secrets and backup codes at rest

If missing or invalid, django-totp raises ImproperlyConfigured.

### TOTP_ISSUER

- Required: No
- Default: MyApp
- Type: string
- Purpose: Issuer label shown in authenticator apps

Example:

    TOTP_ISSUER = "XYZ Platform"

### TOTP_MAX_BACKUP_CODES

- Required: No
- Default: 10
- Type: integer
- Purpose: Number of backup codes generated per user set

Example:

    TOTP_MAX_BACKUP_CODES = 12

### TOTP_THROTTLE_RATE

- Required: No
- Default: 10/minute
- Type: DRF throttle rate string
- Purpose: Rate limit for all django-totp endpoint actions

Example:

    TOTP_THROTTLE_RATE = "5/minute"

### TOTP_TOKEN_SALT

- Required: No
- Default: django-totp-token-salt
- Type: string
- Purpose: Salt used for signed temporary token helpers

### TOTP_TOKEN_MAX_AGE

- Required: No
- Default: 120
- Type: integer (seconds)
- Purpose: Token expiry for signed temporary token helpers

## API Endpoints

Base path assumes you include django_totp.urls at /api/.

All endpoints:

- Require authenticated user
- Use DRF user throttle (configured by TOTP_THROTTLE_RATE)
- Return error payload as JSON with detail field on validation/service errors

### POST /api/totp/create/

Starts TOTP enrollment. Creates an encrypted secret and returns QR SVG.

Request body:

- Empty

Success response (201):

    {
      "svg": "<svg ...>...</svg>"
    }

Error examples (400):

- TOTP already exists for this user

### POST /api/totp/confirm/

Confirms enrollment using a valid code from authenticator app and returns backup codes.

Request body:

    {
      "input_code": "123456"
    }

Success response (200):

    {
      "backup_codes": ["code1", "code2", "..."]
    }

Error examples (400):

- User does not have an associated TOTP secret
- Invalid TOTP code

### POST /api/totp/disable/

Disables TOTP and deletes associated backup codes.

Request body:

- Empty

Success response:

- 204 No Content

Error examples (400):

- User does not have an associated TOTP secret

### POST /api/totp/rotate_backup_codes/

Replaces all existing backup codes with a new set.

Request body:

- Empty

Success response (200):

    {
      "backup_codes": ["new1", "new2", "..."]
    }

## Integrating 2FA Into Login Flow

Typical 2-step login flow:

1. Validate username/password
2. If user has TOTP enabled, issue short-lived signed challenge token
3. Ask user for TOTP code (or backup code)
4. Verify code
5. Issue final session/JWT only after successful 2FA verification

> Helper functions are available in django_totp.auth and django_totp.totp.

Compatibility note:

- If your project uses a custom AUTH_USER_MODEL, prefer implementing your own token-to-user resolver with django.contrib.auth.get_user_model() rather than directly using get_user_from_challenge_token.

Example DRF views (reference pattern):

```python
from django.contrib.auth import authenticate
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status

from django_totp.auth import (
    generate_challenge_token,
    get_user_from_challenge_token,
    is_totp_enabled,
)
from django_totp.totp import verify_totp_code
from django_totp.backup_code_utils import verify_backup_code


@api_view(["POST"])
@permission_classes([AllowAny])
def login_password_step(request):
    user = authenticate(
        request,
        username=request.data.get("username"),
        password=request.data.get("password"),
    )
    if not user:
        return Response({"detail": "Invalid credentials."}, status=401)

    if not is_totp_enabled(user):
        # Issue your final auth token/session here
        return Response({"requires_2fa": False}, status=200)

    challenge_token = generate_challenge_token(user)
    return Response(
        {
            "requires_2fa": True,
            "totp_challenge_token": challenge_token,
        },
        status=200,
    )


@api_view(["POST"])
@permission_classes([AllowAny])
def login_totp_step(request):
    challenge_token = request.data.get("totp_challenge_token")
    otp_code = request.data.get("otp_code")
    backup_code = request.data.get("backup_code")

    if not challenge_token:
        return Response({"detail": "Missing challenge token."}, status=400)

    try:
        user = get_user_from_challenge_token(challenge_token)
    except Exception:
        return Response({"detail": "Invalid or expired token."}, status=400)

    ok = False
    if otp_code:
        ok = verify_totp_code(user, otp_code)
    elif backup_code:
        ok = verify_backup_code(user, backup_code)

    if not ok:
        return Response({"detail": "Invalid 2FA code."}, status=400)

    # Issue your final auth token/session here
    return Response({"authenticated": True}, status=200)
```

## Security and Production Checklist

- Set TOTP_ENCRYPTION_KEY from secure secret manager or environment
- Rotate application secrets using planned migration strategy
- Enforce HTTPS everywhere (especially authentication APIs)
- Use strict throttling for login and TOTP verification endpoints
- Store backup codes only in secure client context right after generation
- Never log plaintext OTP or backup codes
- Add audit logging for enrollment, disable, and backup code rotation events
- Add monitoring for brute-force patterns and unusual failure rates
- Keep Django and cryptography dependency versions current

## Troubleshooting

### ImproperlyConfigured: TOTP_ENCRYPTION_KEY must be set

Cause:

- Missing or invalid Fernet key

Fix:

1. Generate a valid Fernet key
2. Set TOTP_ENCRYPTION_KEY in environment
3. Restart app processes

### Confirm endpoint always returns Invalid TOTP code

Cause candidates:

- Device clock drift
- Wrong issuer/account scanned
- Code copied late/expired

Fixes:

- Ensure server time is synchronized (NTP)
- Re-run enrollment create and rescan QR
- Submit current active code from authenticator app

### Backup code rejected

Cause:

- Backup code already used (one-time)
- Input mismatch due to copy/paste/whitespace issues

Fix:

- Rotate backup codes and securely redistribute

## Data Model

django_totp creates two models:

- Totp
    - user (one-to-one with AUTH_USER_MODEL)
    - secret_key (encrypted)
    - created_at
- BackupCode
    - totp (foreign key)
    - code (encrypted)
    - is_used
    - created_at

## Public Python API

Useful helpers you can import directly:

- django_totp.auth
    - is_totp_enabled(user)
    - generate_challenge_token(user)
    - verify_challenge_token(token)
    - get_user_from_challenge_token(token)
- django_totp.totp
    - generate_totp_secret()
    - verify_totp_code(user, input_code)
    - create_totp_setup(user)
    - confirm_totp_setup(user, input_code)
    - disable_totp(user)
- django_totp.backup_code_utils
    - store_backup_codes(user, codes)
    - verify_backup_code(user, input_code)
    - rotate_backup_codes(user)
- django_totp.encryption
    - generate_fernet_key()
    - resolve_fernet_key(default=None)
    - encrypt(value)
    - decrypt(value)

## Contributing

Contributions are welcome! Please open issues for bugs or feature requests, and submit pull requests for any improvements.

## Maintainers

- Kumar Sahil
    - GitHub: [@krsahil8825](https://github.com/krsahil8825)
    - Email: [krsahil8825@gmail.com](mailto:krsahil8825@gmail.com)

## License

MIT License.
