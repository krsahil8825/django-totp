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
- JWT Authentication
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

```bash
pip install django-totp
```

## Quick Start

### 1. Add apps

In Django settings:

```python
# settings.py
INSTALLED_APPS = [
    # Django apps...
    "rest_framework",
    "django_totp",
]
```

### 2. Set encryption key (required)

Generate a Fernet key once:

```bash
python -c "from django_totp.encryption import generate_fernet_key; print(generate_fernet_key())"
```

Add it as an environment variable:

```txt
# .env
TOTP_ENCRYPTION_KEY=your-generated-key
```

And load in settings:

```python
# settings.py
import os
TOTP_ENCRYPTION_KEY = os.environ["TOTP_ENCRYPTION_KEY"]
```

Important:

- Do not generate a new key on each start in production
- Changing this key later makes previously encrypted TOTP data unreadable

### 3. Include URLs

In your project URL configuration:

```python
# urls.py
from django.urls import include, path

urlpatterns = [
    # your routes...
    path("api/", include("django_totp.urls")),
    path("api/", include("django_totp.urls.jwt"))
]
```

### 4. Run migrations

```bash
python manage.py migrate
```

### 5. Call endpoints as authenticated user

TOTP management endpoints:

- Enrollment create: `POST /api/totp/create/`
- Confirm enrollment: `POST /api/totp/confirm/`
- Disable TOTP: `POST /api/totp/disable/`
- Rotate backup codes: `POST /api/totp/rotate_backup_codes/`

JWT Authentication endpoints (if using JWT):

- Create: `POST /api/jwt/create/`
- TOTP Verify: `POST /api/jwt/totp/verify/`
- Refresh: `POST /api/jwt/refresh/`
- Verify: `POST /api/jwt/verify/`

## Configuration Reference

All settings below are read from Django settings.

> Note: Configure Your Secrets in Environment Variables! Do not hardcode sensitive values in settings.py.

### TOTP_ENCRYPTION_KEY

- Required: Yes
- Type: string (valid Fernet key)
- Purpose: Encrypts TOTP secrets and backup codes at rest

If missing or invalid, django-totp raises ImproperlyConfigured.

```python
# settings.py
TOTP_ENCRYPTION_KEY = "your-generated-key"
# generate with: python -c from django_totp.encryption import generate_fernet_key; print(generate_fernet_key())
```

### TOTP_ISSUER

- Required: No
- Default: MyApp
- Type: string
- Purpose: Issuer label shown in authenticator apps

```python
# settings.py
TOTP_ISSUER = "XYZ Platform"
```

### TOTP_MAX_BACKUP_CODES

- Required: No
- Default: 10
- Type: integer
- Purpose: Number of backup codes generated per user set

```python
# settings.py
TOTP_MAX_BACKUP_CODES = 12
```

### TOTP_THROTTLE_RATE

- Required: No
- Default: 10/minute
- Type: DRF throttle rate string
- Purpose: Rate limit for all django-totp endpoint actions

```python
# settings.py
TOTP_THROTTLE_RATE = "5/minute"
```

### TOTP_TOKEN_SALT

- Required: No
- Default: django-totp-token-salt
- Type: string
- Purpose: Salt used for signed temporary token helpers

```python
# settings.py
TOTP_TOKEN_SALT = "django-totp-token-salt"
```

### TOTP_TOKEN_MAX_AGE

- Required: No
- Default: 120
- Type: integer (seconds)
- Purpose: Token expiry for signed temporary token helpers

```python
# settings.py
TOTP_TOKEN_MAX_AGE = 120
```

### REST_FRAMEWORK JWT Authentication

- Required: No (only if using JWT integration)
- Purpose: Configure DRF to use JWTAuthentication for protected endpoints

```python
# settings.py
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
}
```

### SIMPLE_JWT Settings

- Required: No (only if using JWT integration)
- Purpose: Configure JWT behavior, token lifetimes, rotation, etc.
- Docs: https://django-rest-framework-simplejwt.readthedocs.io/en/latest/settings.html

```python
# settings.py
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

## API Endpoints

Base path assumes you include `django_totp.urls` at /api/. For JWT endpoints, include `django_totp.urls.jwt` at the same base path.

All endpoints:

- Use DRF user throttle (configured by TOTP_THROTTLE_RATE)
- Return error payload as JSON with detail field on validation/service errors

### TOTP Setup Endpoints

When a user wants to enable TOTP, they should first call the create endpoint to get the QR code, then confirm with a valid OTP to finalize enrollment and receive backup codes.

#### POST /api/totp/create/

Starts TOTP enrollment. Creates an encrypted secret and returns QR SVG.

Request body:

- Empty

Success response (201):

```json
{
    "svg": "<svg ...>...</svg>"
}
```

Error examples (400):

- TOTP already exists for this user

#### POST /api/totp/confirm/

Confirms enrollment using a valid code from authenticator app and returns backup codes.

Request body:

```json
{
    "input_code": "123456"
}
```

Success response (200):

```json
{
    "backup_codes": ["code1", "code2", "..."]
}
```

Error examples (400):

- User does not have an associated TOTP secret
- Invalid TOTP code

#### POST /api/totp/disable/

Disables TOTP and deletes associated backup codes.

Request body:

- Empty

Success response:

- 204 No Content

Error examples (400):

- User does not have an associated TOTP secret

#### POST /api/totp/rotate_backup_codes/

Replaces all existing backup codes with a new set.

Request body:

- Empty

Success response (200):

```python
{
    "backup_codes": ["new1", "new2", "..."]
}
```

### JWT Authentication Endpoints

When django_totp is integrated with JWT authentication, use these endpoints for 2FA-aware token issuance.

#### POST /api/jwt/create/

Initiate login with username and password. Returns JWT tokens if user has no TOTP enabled, or a challenge token if 2FA is required.

Request body:

```json
{
    "username": "user@example.com",
    "password": "secure_password"
}
```

Success response (200) — No TOTP enabled:

```json
{
    "is_totp_enabled": false,
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc...",
    "access": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

Success response (200) — TOTP enabled:

```json
{
    "is_totp_enabled": true,
    "totp_challenge_token": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

Error examples (400/401):

- Invalid username/password combination
- User account inactive or disabled

#### POST /api/jwt/totp/verify/

Verify TOTP code or backup code and receive JWT tokens. Must be called after `/api/jwt/create/` when TOTP is enabled.

Request body (TOTP code):

```json
{
    "totp_challenge_token": "...",
    "otp_code": "123456"
}
```

Request body (backup code):

```json
{
    "totp_challenge_token": "...",
    "backup_code": "BACKUP-CODE-1"
}
```

Success response (200):

```json
{
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc...",
    "access": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

Error examples (400):

- Invalid or expired challenge token
- Invalid TOTP code
- Invalid backup code
- TOTP not enabled for user (fallback check)

#### POST /api/jwt/refresh/

Refresh an expired access token using a valid refresh token.

Request body:

```json
{
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

Success response (200):

```json
{
    "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..." // New refresh token if rotation enabled
}
```

#### POST /api/jwt/verify/

Verify the validity of an access or refresh token.

Request body:

```json
{
    "token": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

Success response (200):

```json
{} // Empty response indicates valid token
```

Error examples (401):

- Token expired
- Token blacklisted (if using token blacklist)
- Invalid token signature

## Integrating 2FA Into Login Flow

Typical 2-step login flow:

1. Validate username/password
2. If user has TOTP enabled, issue short-lived signed challenge token
3. Ask user for TOTP code (or backup code)
4. Verify code
5. Issue final session/JWT only after successful 2FA verification

## Security and Production Checklist

### Configure Encryption Key Correctly

`TOTP_ENCRYPTION_KEY` is used to encrypt stored TOTP secrets and backup codes.

Recommendations:

- Store the key in environment variables or a secure secret manager.
- Generate the key once and reuse it across deployments.
- Never hardcode the key in source code or commit it to Git.

Generate a Fernet key:

```bash
python -c "from django_totp.encryption import generate_fernet_key; print(generate_fernet_key())"
```

Important:

- Do NOT generate a new key on every application start.
- Do NOT change the key after users have enrolled in TOTP unless you intentionally want to invalidate existing encrypted TOTP data.
- Changing the key later makes previously encrypted TOTP secrets and backup codes unreadable.

### Use HTTPS in Production

Always serve authentication endpoints over HTTPS.

This includes:

- TOTP setup endpoints
- JWT authentication endpoints
- TOTP verification endpoints

Never expose OTP codes, challenge tokens, or JWT tokens over plain HTTP connections.

### Configure Throttling

Enable strict throttling for authentication-related endpoints to reduce brute-force attempts.

Recommended endpoints:

- Login endpoints
- TOTP verification endpoints
- Backup code verification endpoints

Example:

```python
TOTP_THROTTLE_RATE = "5/minute"
```

### Handle Backup Codes Securely

Backup codes are recovery credentials and should be treated like passwords.

Recommendations:

- Show backup codes only once during generation or rotation.
- Ask users to securely store backup codes.
- Never log plaintext backup codes.
- Never expose backup codes in debug responses or monitoring systems.

### Handle OTP Codes Securely

Recommendations:

- Never log OTP codes.
- Never store submitted OTP codes.
- Avoid exposing OTP values in debugging tools, logs, or error traces.

### Configure Challenge Token Expiry Carefully

`TOTP_TOKEN_MAX_AGE` controls how long temporary challenge tokens remain valid during the 2FA login flow.

Default:

```python
TOTP_TOKEN_MAX_AGE = 120
```

Recommendations:

- Keep expiration times short in production.
- Avoid excessively large expiration windows.

### Configure Token Salt Before Production

`TOTP_TOKEN_SALT` is used when generating signed temporary challenge tokens.

Default:

```python
TOTP_TOKEN_SALT = "django-totp-token-salt"
```

Recommendations:

- Change the default value before production deployment.
- Keep the value stable after deployment.
- Don't hardcode the salt in source code if possible.

Important:

- Changing the salt later invalidates previously issued challenge tokens.

### Keep Dependencies Updated

Keep authentication and security-related dependencies updated regularly.

Recommended packages to monitor:

- Django
- cryptography
- pyotp
- djangorestframework
- djangorestframework-simplejwt

Apply security updates regularly in production environments.

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

## Interactive Helper Tools

The following utilities are available for development, debugging, and response inspection:

- **SVG Viewer**  
  Render and inspect SVG payloads returned by TOTP enrollment (create) endpoints.

- **JSON to TXT Converter**  
  Convert backup code JSON responses into plain-text downloadable format.

Tool URL:

https://django-totp-helper.pages.dev/

## Contributing

Contributions are welcome! Please open issues for bugs or feature requests, and submit pull requests for any improvements.

## Maintainers

- Kumar Sahil
    - GitHub: [@krsahil8825](https://github.com/krsahil8825)
    - Email: [krsahil8825@gmail.com](mailto:krsahil8825@gmail.com)

## License

MIT License.
