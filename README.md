# Laker API

Production-ready FastAPI application with a clean layered architecture.

## Structure

```
app/
├── main.py                  # App factory + middleware registration
├── core/
│   ├── config.py            # Settings (pydantic-settings + .env)
│   ├── constants.py         # App-wide constants
│   ├── exceptions.py        # Typed HTTP errors + handlers
│   ├── logging.py           # Structured logging setup
│   └── security.py          # JWT + password utilities
├── middleware/
│   ├── correlation_id.py    # X-Correlation-ID propagation
│   ├── request_context.py   # Per-request ContextVar dict
│   ├── logging.py           # Access log (request in / response out)
│   ├── rate_limit.py        # Token-bucket rate limiter per IP
│   └── security_headers.py  # Hardened HTTP response headers
├── api/
│   ├── router.py            # Mounts all v1 routers
│   └── v1/
│       ├── auth.py          # /auth  (login, logout, refresh, me)
│       ├── users.py         # /users
│       └── health.py        # /health  (liveness + readiness)
├── services/
│   └── auth_service.py      # Login / logout / refresh / profile logic
├── repositories/
│   └── auth_repository.py   # DB queries for auth entities
├── models/
│   ├── user_model.py        # SQLAlchemy UserModel
│   └── auth_model.py        # RefreshTokenModel, RevokedAccessTokenModel
├── schemas/
│   ├── auth_schema.py       # Pydantic request/response schemas
│   └── common_schema.py     # Pagination, sort, paged response generics
├── dependencies/
│   └── auth.py              # get_current_user, require_roles, shortcuts
├── database/
│   ├── base.py              # DeclarativeBase
│   └── session.py           # Engine + async session factory + get_db
└── observability/
    ├── metrics.py           # In-process counters / histograms
    ├── tracing.py           # Span stub (swap for OpenTelemetry)
    └── monitoring.py        # GET /internal/metrics
```

## Middleware stack

```
Request
  │
  ▼
CorrelationId       assigns / propagates X-Correlation-ID
  │
RateLimit           token-bucket per IP (100 req / 60 s default)
  │
RequestContext      attaches path/method/IP to ContextVar
  │
Logging             structured access log + latency header
  │
SecurityHeaders     HSTS, CSP, X-Frame-Options, …
  ▼
Response
```

## WSL setup (Windows only)

If you are developing on Windows using WSL 2, follow these steps before the quick start.

### 1. Enable WSL interop

WSL interop must be enabled for Docker Desktop and VS Code to work correctly.

```bash
# Check if interop is active
cat /proc/sys/fs/binfmt_misc/WSLInterop

# If the file does not exist, enable it
sudo mount -t binfmt_misc none /proc/sys/fs/binfmt_misc
echo ':WSLInterop:M::MZ::/init:PF' | sudo tee /proc/sys/fs/binfmt_misc/register
```

To make this permanent, add the following to `/etc/wsl.conf`:

```ini
[interop]
enabled=true
appendWindowsPath=true
```

Then restart WSL from a Windows PowerShell window:

```powershell
wsl --shutdown
```

### 2. Connect VS Code to WSL

Do not use `code .` from the WSL terminal — it will fail with an `Exec format error` because it tries to run the Windows `.exe` directly.

Instead:

1. Open VS Code on Windows.
2. Install the **WSL** extension (by Microsoft) from the Extensions panel (`Ctrl+Shift+X`).
3. Press `Ctrl+Shift+P` and run **WSL: Open Folder in WSL**.
4. Navigate to `~/Laker_Backend`.

VS Code will install a small Linux-compatible server inside WSL on first connect. All subsequent terminal sessions inside VS Code will run natively in WSL.

### 3. Enable Docker Desktop WSL integration

1. Open Docker Desktop on Windows.
2. Go to **Settings → Resources → WSL Integration**.
3. Toggle on **Enable integration with my default WSL distro** and select your Ubuntu distro.
4. Click **Apply & Restart**.
5. Reopen your WSL terminal and verify:

```bash
docker ps
```


```bash
docker compose down -v
docker compose up --build
```

## Quick start

```bash
# 1. Clone & install
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2. Start Postgres

# 3. Run
uvicorn app.main:app --reload

# Docs
open http://localhost:8000/docs
```

## Docker (full stack)

```bash
docker compose up postgres -d
docker compose up --build
```

## Tests

```bash
pip install pytest pytest-asyncio httpx aiosqlite
pytest
```

## Auth flow

| Endpoint | Method | Auth required |
|---|---|---|
| `/api/v1/auth/login` | POST | No |
| `/api/v1/auth/logout` | POST | Bearer token |
| `/api/v1/auth/refresh` | POST | No (refresh token in body) |
| `/api/v1/auth/me` | GET | Bearer token |
| `/api/v1/health` | GET | No |
| `/api/v1/health/ready` | GET | No |

Tokens use **rotating refresh tokens** — each `/refresh` call consumes the old token and issues a new pair. Reuse of a consumed token revokes the entire token family.