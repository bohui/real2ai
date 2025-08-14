# Token Management & RLS Authentication

This document describes how Real2.AI manages authentication tokens across the backend, database (RLS), and middleware. It reflects the current implementation as of August 2025.

## Overview

- Supabase Auth issues user access tokens (JWT). In our environment, these are HS256-signed.
- The backend may issue a short-lived backend token to clients. On each request, the backend exchanges the backend token for the Supabase access token and uses the Supabase token for database (RLS) operations only.
- Database connections verify the Supabase token signature and set session GUCs so Row Level Security (RLS) policies work correctly.

## Components

- `app.middleware.auth_middleware.AuthContextMiddleware`
  - Extracts `Authorization: Bearer <token>` from requests
  - If the token is a backend token, exchanges it for the Supabase access token via `BackendTokenService.ensure_supabase_access_token`
  - Sets `AuthContext` with the Supabase token and user identity

- `app.services.backend_token_service.BackendTokenService`
  - Issues backend JWTs and stores a mapping to Supabase access/refresh tokens
  - Can refresh Supabase sessions and reissue backend tokens in coordination
  - Note: If `JWT_SECRET_KEY` is unset, it defaults to `SUPABASE_ANON_KEY` for signing backend tokens

- `app.database.connection._setup_user_session`
  - Verifies Supabase access tokens with HS256 using `SUPABASE_JWT_SECRET`
  - Audience verification is disabled (Supabase tokens may not set an audience matching this backend)
  - On success, sets session GUCs:
    - `request.jwt.claims` to the verified JWT claims
    - `role` to `authenticated`
    - `request.jwt.claim.sub` to the user id
  - RS256/JWKS fallback is not used (HS256-only)

## Required Environment

- `SUPABASE_URL`: Supabase project URL
- `SUPABASE_ANON_KEY`: Supabase anon key
- `SUPABASE_SERVICE_KEY`: Supabase service role key
- `SUPABASE_JWT_SECRET`: Supabase JWT secret used to verify HS256 tokens in the DB layer
  - Required in production; recommended in development
- `JWT_SECRET_KEY`: Backend token signing secret (for our own backend-issued JWTs)
  - Recommended to set explicitly; otherwise defaults to `SUPABASE_ANON_KEY`

See `docs/development/ENVIRONMENT_VARIABLES.md` for full details and defaults.

## Middleware Flow

1. Client sends `Authorization: Bearer <token>`
2. Middleware detects token type:
   - Backend token: Exchange for Supabase access token; set `AuthContext` with Supabase token
   - Supabase token: Use directly; set `AuthContext`
3. DB calls use `get_user_connection(...)` which verifies the token and sets RLS session GUCs

## Security Notes

- HS256 verification only; RS256/JWKS fallback has been removed for simplicity and to avoid misconfiguration risks
- Audience claim is not verified. Consider adding custom checks for `iss`/`sub` if needed:
  - `iss` should match `${SUPABASE_URL}/auth/v1` (or begin with it)
  - `sub` must match the user id used for the connection
- Avoid logging tokens. The system logs non-sensitive diagnostics (token length, secret fingerprint prefix) for troubleshooting
- Ensure Docker Compose passes env vars into the backend container so `get_settings()` loads the intended values

## Troubleshooting

- "Signature verification failed"
  - Ensure `SUPABASE_JWT_SECRET` in backend matches your Supabase project’s JWT secret (Project Settings → API → JWT)
  - Confirm logs show `header_alg: HS256`
  - Verify container sees the variable: `printenv SUPABASE_JWT_SECRET | wc -c`

- "Invalid audience" during HS256 decode
  - Audience checks are disabled in code; if you still see this, restart the backend to load the latest code

- RLS access denied
  - Check that `AuthContext` has a user token
  - Confirm `_setup_user_session` logs show “Token verified with HS256” and GUCs being set

---

This document should be kept updated when:
- Token algorithms or verification strategy change
- RS256/JWKS support is introduced
- Middleware or exchange logic changes
