# Laker API

FastAPI backend for the Laker platform — members, claims, pharmacies, prescribers, drugs, and prior authorizations — backed by Oracle, Redis, and a layered service/repository architecture.

## Stack

| Layer | Choice |
|---|---|
| Framework | FastAPI (async) |
| Database | Oracle (via `oracledb`, SQLAlchemy async, Alembic migrations) |
| Cache / OTP / rate-limit store | Redis |
| Auth | JWT access tokens + rotating opaque refresh tokens, optional email-OTP 2FA |
| Tests | pytest + pytest-asyncio, SQLite in-memory + fakeredis (no external services needed) |

## Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| Python | 3.11 | 3.12.x |
| Docker + Docker Compose | 20.10 / 1.29 | Latest |
| Oracle DB | — | `container-registry.oracle.com/database/free:latest` (via Docker Compose) |
| Redis | 6.0 | 7-alpine |

## Quick start

Copy-paste command list to get the server running. `.env` must exist first (see [Environment variables](#environment-variables)) — copy an existing one or fill in the variable list below.

**With Docker** (Redis + Oracle + API, migrations run automatically):

```bash
cd Laker-Backend
docker compose up --build
# → API live at http://localhost:8000 once Uvicorn logs "Application startup complete"
```

**Without Docker** (requires a reachable Oracle instance and Redis already running):

```bash
cd Laker-Backend
python -m venv .venv
source .venv/bin/activate        # .venv\Scripts\activate on Windows
pip install -r requirements.txt

# point .env at your DB/Redis (DB_HOST=localhost, REDIS_HOST=localhost), then:
alembic upgrade head
uvicorn app.main:app --reload
# → API live at http://localhost:8000
```

Optional, either path — seed sample data after the server (or at least migrations) is up:

```bash
python -m app.scripts.seed_users
python -m app.scripts.seed_members
python -m app.scripts.seed_lookups
python -m app.scripts.seed_pharmacies
python -m app.scripts.seed_zip_codes
python -m app.scripts.seed_claims
python -m app.scripts.seed_eligibility
```

Full details and DBeaver/Oracle connection notes: [Setup & running](#setup--running).

## Project structure

```text
app/
├── main.py               # App factory, middleware registration, lifespan
├── api/
│   ├── router.py         # Mounts every v1 router
│   └── v1/                # auth, claims, members, pharmacies, prescribers, drugs, prior_auth, users, health
├── core/                  # config (Settings), constants, exceptions + handlers, security (JWT/hashing), rbac, mailer
├── database/              # SQLAlchemy base + async session/engine
├── dependencies/          # FastAPI DI: auth, mailer
├── middleware/             # correlation id, rate limit, request context, access logging, security headers
├── cache/                 # Redis client + cache_service wrapper
├── models/                 # SQLAlchemy ORM models (one per domain)
├── repositories/            # Data-access layer, one per domain
├── services/                # Business logic layer, one per domain
├── schemas/                 # Pydantic request/response models
├── observability/            # Prometheus metrics, /internal/metrics, tracing stubs
└── scripts/                  # seed_users / seed_members / seed_lookups / seed_pharmacies / seed_zip_codes / seed_claims / seed_eligibility (run manually, see below)

alembic/                   # DB migrations (script_location = alembic)
tests/
├── integration/            # Full HTTP-layer tests per module (SQLite + fakeredis)
└── unit/                   # Service/schema/repository-level tests
```

**Architecture**: `api/` (routing + auth only) → `services/` (business logic, raises `AppException` subclasses) → `repositories/` (SQL only) → `models/`. Exceptions are mapped to HTTP responses by global handlers in `main.py`, never inside a route.

### Middleware stack (outermost → innermost)

```text
CORS → CorrelationId → RateLimit → RequestContext → Logging → SecurityHeaders → Router
```

## Environment variables

All configuration is read from `.env` via `app/core/config.py` (`pydantic-settings`). Variable names are case-insensitive. Fields with no default below are **required**.

| Variable | Default | Notes |
|---|---|---|
| **Application** | | |
| `APP_ENV` | `development` | `production` disables `/docs`, `/redoc`, `/openapi.json` |
| `APP_DEBUG` | `false` | |
| `APP_VERSION` | `1.0.0` | |
| `RECENT_CLAIMS_WINDOW_DAYS` | `90` | Trailing window used by the claims "recent" search |
| **Database (Oracle)** | | |
| `DB_DRIVER` | *required* | e.g. `oracle+oracledb` |
| `DB_USER` | *required* | |
| `DB_PASSWORD` | *required* | |
| `DB_USER_PASSWORD` | *required* | App-user password used inside the Oracle connection string |
| `DB_HOST` | *required* | `oracle-db` in Docker Compose, `localhost` for local Oracle |
| `DB_PORT` | *required* | `1521` |
| `DB_NAME` | *required* | Oracle service name, e.g. `FREEPDB1` |
| **Redis / Cache** | | |
| `REDIS_HOST` | `redis` | `localhost` outside Docker |
| `REDIS_PORT` | `6379` | |
| `REDIS_DB` | `0` | |
| `CACHE_ENABLED` | `true` | |
| `CACHE_DEFAULT_TTL_SECONDS` | `300` | |
| **Auth / JWT** | | |
| `JWT_SECRET_KEY` | *required* | HMAC signing key for access tokens |
| `OTP_ENABLED` | `false` | Enforces email-OTP 2FA on login when true |
| `OTP_SECRET` | `default-secret` | Must be overridden — startup refuses known-insecure values (`default-secret`, `changeme`, `secret`, empty) |
| **Rate limiting** | | |
| `RATE_LIMIT_ENABLED` | `false` | |
| `RATE_LIMIT_REQUESTS` | `100` | Requests per window, per IP |
| `RATE_LIMIT_WINDOW_SECONDS` | `60` | |
| **SSHost integration** | | |
| `SSHOST_HOST` | — | Optional external credential-verification host. On timeout/unreachable, login falls back to local password verification |
| `SSHOST_PORT` | `9000` | |
| `SSHOST_CONNECT_TIMEOUT_SECONDS` | `5.0` | |
| `SSHOST_RESPONSE_TIMEOUT_SECONDS` | `5.0` | |
| **SMTP (OTP delivery)** | | |
| `SMTP_HOST` | `smtp.gmail.com` | |
| `SMTP_PORT` | `587` | |
| `SMTP_USERNAME` | `""` | |
| `SMTP_PASSWORD` | `""` | |
| `SMTP_USE_TLS` | `true` | |
| `SMTP_USE_SSL` | `false` | |
| `SMTP_FROM_EMAIL` | `no-reply@yourapp.com` | |
| `SMTP_FROM_NAME` | `YourApp` | |

No `.env.example` currently ships in the repo — copy the variable list above, or an existing teammate's `.env`, to get started. `.env` itself is git-ignored.

## Setup & running

### Option 1: Docker (recommended)

```bash
docker compose up --build      # starts Redis, Oracle, and the API
```

- Migrations run automatically on container start (`docker-entrypoint.sh` runs `alembic upgrade head` before `uvicorn`).
- API: `http://localhost:8000` · Swagger: `/docs` · ReDoc: `/redoc`

```bash
docker compose logs -f laker-api
docker compose down            # stop
docker compose down -v         # stop + wipe DB volume
```

**Connecting a DB client (e.g. DBeaver)** to the Dockerized Oracle instance: host `localhost`, port from `DB_PORT` (`.env`), service name from `DB_NAME`, user/password from `DB_USER`/`DB_PASSWORD`.

### Option 2: Local (no Docker)

```bash
python -m venv .venv && source .venv/bin/activate   # .venv\Scripts\activate on Windows
pip install -r requirements.txt
```

Point `.env` at a reachable Oracle instance and Redis (`DB_HOST=localhost`, `REDIS_HOST=localhost`), then:

```bash
alembic upgrade head            # apply migrations
uvicorn app.main:app --reload   # http://localhost:8000
```

### Seeding sample data

Seed scripts are idempotent (safe to re-run) but **not** run automatically — invoke them manually after migrations.

**With Docker** (run inside the running `api` container):

```bash
docker compose exec api python -m app.scripts.seed_users        # test users + permission grants
docker compose exec api python -m app.scripts.seed_members      # plans, members, addresses
docker compose exec api python -m app.scripts.seed_lookups      # drugs, prescribers
docker compose exec api python -m app.scripts.seed_pharmacies   # pharmacies
docker compose exec api python -m app.scripts.seed_zip_codes    # ZIPCODES reference table (pharmacy radius search)
docker compose exec api python -m app.scripts.seed_claims       # claims (references seeded members)
docker compose exec api python -m app.scripts.seed_eligibility  # SUBSCRIBER + group/COB/subgroup eligibility (references seeded members)
```

**Without Docker** (from your activated `.venv`):

```bash
python -m app.scripts.seed_users        # test users + permission grants
python -m app.scripts.seed_members      # plans, members, addresses
python -m app.scripts.seed_lookups      # drugs, prescribers
python -m app.scripts.seed_pharmacies   # pharmacies
python -m app.scripts.seed_zip_codes    # ZIPCODES reference table (pharmacy radius search)
python -m app.scripts.seed_claims       # claims (references seeded members)
python -m app.scripts.seed_eligibility  # SUBSCRIBER + group/COB/subgroup eligibility (references seeded members)
```

### Database migrations

```bash
alembic upgrade head                         # apply all pending migrations
alembic revision -m "add foo column"         # create a new migration
alembic downgrade -1                         # roll back one revision
```

## Running tests

Tests need no external services — they run against an in-memory SQLite DB and `fakeredis`.

```bash
pytest                              # full suite
pytest -v
pytest tests/unit/test_security.py  # single file
pytest --cov=app                    # with coverage
```

## Auth flow

| Endpoint | Method | Auth required |
|---|---|---|
| `/api/v1/auth/login` | POST | No |
| `/api/v1/auth/verify-otp` | POST | No (`loginSessionId` from `/login`) |
| `/api/v1/auth/resend-otp` | POST | No (`loginSessionId` from `/login`) |
| `/api/v1/auth/refresh` | POST | No (refresh token in body) |
| `/api/v1/auth/logout` | POST | Bearer token |
| `/api/v1/auth/me` | GET | Bearer token |

- **Tokens**: rotating refresh tokens — each `/refresh` consumes the old token and issues a new pair; reusing a consumed token revokes the entire token family.
- **OTP (when `OTP_ENABLED=true`)**: `/login` returns a `loginSessionId` + challenge instead of tokens. `/verify-otp` allows 3 attempts before the session is locked out (429); `/resend-otp` allows 3 resends (429 past that) plus a 2-minute cooldown between sends. Both surface `otpVerificationAttemptsRemaining` / `otpResendAttemptsRemaining` so the frontend can show a live counter.
- **Login lockout**: 3 failed attempts per email *and* per IP within a 15-minute window returns 429.

## API modules

| Module | Base path | Purpose |
|---|---|---|
| Auth | `/api/v1/auth` | Login, OTP, refresh, logout, profile |
| Members | `/api/v1/members` | Member search, detail, eligibility, family |
| Claims | `/api/v1/claims`, `/api/v1/members/{id}/claims`, … | Claim search/detail, scoped by member/pharmacy/prescriber/drug |
| Pharmacies | `/api/v1/pharmacies` | Lookup by NABP/NPI/ZIP radius, search |
| Prescribers | `/api/v1/prescribers` | Lookup, search |
| Drugs | `/api/v1/drugs` | Lookup by NDC/GPI, search |
| Prior Authorizations | `/api/v1/prior-auth`, `/api/v1/members/{id}/prior-auth` | CRUD + search |
| Health | `/api/v1/health` | Liveness (`/`) and readiness (`/ready`, checks DB + cache) |

Full request/response shapes: Swagger UI at `/docs` (source of truth — this table is intentionally not exhaustive).

---

## WSL setup (Windows only)

Follow this before the quick start above if developing on Windows via WSL2.

### 1. Install Ubuntu 24.04 on WSL2

```powershell
# PowerShell as Administrator
wsl --install -d Ubuntu-24.04
wsl --set-default Ubuntu-24.04
wsl --set-default-version 2
```

Verify:

```bash
lsb_release -a   # expect: Ubuntu 24.04 LTS (Noble Numbat)
```

Then update packages inside WSL: `sudo apt-get update && sudo apt-get upgrade -y`

### 2. Enable WSL interop (only if WSL isn't starting correctly)

```bash
cat /proc/sys/fs/binfmt_misc/WSLInterop   # check if active
# if missing:
sudo mount -t binfmt_misc none /proc/sys/fs/binfmt_misc
echo ':WSLInterop:M::MZ::/init:PF' | sudo tee /proc/sys/fs/binfmt_misc/register
```

Make it permanent — add to `/etc/wsl.conf`:

```ini
[interop]
enabled=true
appendWindowsPath=true
```

Then `wsl --shutdown` from PowerShell and reopen.

### 3. Connect VS Code to WSL

Don't run `code .` from the WSL terminal directly. Instead: install the **WSL** extension in VS Code (Windows side), `Ctrl+Shift+P` → **WSL: Open Folder in WSL**, navigate to the repo.

### 4. Docker Desktop WSL integration

Docker Desktop → **Settings → Resources → WSL Integration** → enable your Ubuntu distro → **Apply & Restart**. Verify with `docker ps` from the WSL terminal.
