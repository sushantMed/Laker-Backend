# Laker API

Production-ready FastAPI application with a clean layered architecture.

## Project Structure

```
Laker-Backend/
├── app/                           # Application source code
│   ├── __init__.py
│   ├── main.py                    # App factory + middleware registration + lifespan
│   ├── api/                       # API routes
│   │   ├── __init__.py
│   │   ├── router.py              # Main router - mounts all v1 routers
│   │   └── v1/                    # API v1 endpoints
│   │       ├── __init__.py
│   │       ├── auth.py            # POST /auth/login, /logout, /refresh; GET /me
│   │       ├── health.py          # GET /health, /health/ready
│   │       ├── members.py         # GET /members (search, details)
│   │       └── users.py           # User management endpoints
│   ├── cache/                     # Redis caching
│   │   ├── cache_service.py       # Cache operations wrapper
│   │   └── redis_client.py        # Redis connection management
│   ├── core/                      # Core configuration & utilities
│   │   ├── __init__.py
│   │   ├── config.py              # Settings (pydantic-settings + .env)
│   │   ├── constants.py           # App-wide constants
│   │   ├── exceptions.py          # Custom exceptions + error handlers
│   │   ├── logging.py             # Structured logging setup
│   │   └── security.py            # JWT creation/validation + password hashing
│   ├── database/                  # Database configuration
│   │   ├── __init__.py
│   │   ├── base.py                # SQLAlchemy DeclarativeBase
│   │   └── session.py             # Engine + async session factory
│   ├── dependencies/              # FastAPI dependencies
│   │   ├── __init__.py
│   │   └── auth.py                # get_current_user, require_roles
│   ├── middleware/                # Custom ASGI middleware
│   │   ├── __init__.py
│   │   ├── correlation_id.py      # X-Correlation-ID propagation
│   │   ├── logging.py             # Access log (request in/out + latency)
│   │   ├── rate_limit.py          # Token-bucket rate limiter per IP
│   │   ├── request_context.py     # Per-request ContextVar context
│   │   └── security_headers.py    # Hardened HTTP response headers (HSTS, CSP, etc)
│   ├── models/                    # SQLAlchemy ORM models
│   │   ├── __init__.py
│   │   ├── auth_model.py          # RefreshTokenModel, RevokedAccessTokenModel
│   │   ├── member_model.py        # MemberModel (insurance members)
│   │   ├── member_address_model.py # MemberAddressModel (1-to-1 with Member)
│   │   ├── plan_model.py          # PlanModel (insurance plans)
│   │   └── user_model.py          # UserModel (system users)
│   ├── observability/             # Monitoring & observability
│   │   ├── __init__.py
│   │   ├── metrics.py             # Prometheus metrics + counters
│   │   ├── monitoring.py          # GET /internal/metrics endpoint
│   │   └── tracing.py             # Tracing stubs (ready for OpenTelemetry)
│   ├── repositories/              # Data access layer
│   │   ├── __init__.py
│   │   ├── auth_repository.py     # Auth entity queries
│   │   ├── base_repository.py     # Base repository with common CRUD
│   │   ├── member_repository.py   # Member queries + search
│   │   └── plan_repository.py     # Plan queries
│   ├── schemas/                   # Pydantic request/response schemas
│   │   ├── __init__.py
│   │   ├── auth_schema.py         # Login, Refresh, UserProfile, ApiResponse
│   │   ├── common_schema.py       # Pagination, search, generic response
│   │   └── member_schema.py       # Member request/response schemas
│   ├── services/                  # Business logic layer
│   │   ├── __init__.py
│   │   ├── auth_service.py        # Auth: login, logout, refresh, profile
│   │   └── member_service.py      # Member search, detail, family logic
│   ├── utils/                     # Utility functions & enums
│   │   ├── enums.py               # Gender, CoverageType, FamilyRole, etc
│   │   └── pagination.py          # Pagination utilities + models
│   └── scripts/                   # Database seeding scripts
│       ├── seed_members.py        # Seed members from members.json
│       ├── seed_users.py          # Seed test users
│       ├── members.json           # Sample member data
│       └── users.json             # Sample user data
├── tests/                         # Test suite
│   ├── __init__.py
│   ├── integration/               # Integration tests
│   │   ├── __init__.py
│   │   └── test_auth_endpoints.py # Auth endpoint tests
│   └── unit/                      # Unit tests
│       ├── __init__.py
│       └── test_security.py       # Security utilities tests
├── Dockerfile                     # Docker image configuration
├── docker-compose.yml             # Docker Compose services (API, Postgres, Redis)
├── .env                          # Environment variables (git-ignored)
├── .env.example                  # Example .env template
├── .gitignore                    # Git ignore patterns
├── pytest.ini                    # Pytest configuration
├── requirements.txt              # Python dependencies
└── README.md                     # This file
```

### Key Architecture Layers

1. **API Layer** (`api/`) — FastAPI route handlers, request validation
2. **Service Layer** (`services/`) — Business logic, orchestration
3. **Repository Layer** (`repositories/`) — Data access, database queries
4. **Model Layer** (`models/`) — SQLAlchemy ORM definitions
5. **Schema Layer** (`schemas/`) — Pydantic validation models
6. **Core Layer** (`core/`) — Config, security, exceptions, logging
7. **Middleware** (`middleware/`) — Cross-cutting concerns (auth, rate limiting, logging)
8. **Cache** (`cache/`) — Redis integration for session/data caching
9. **Dependencies** (`dependencies/`) — FastAPI dependency injection
10. **Observability** (`observability/`) — Metrics, tracing, monitoring

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

## Setup & Running

### Option 1: Docker Setup (Recommended)

#### Prerequisites
- Docker and Docker Compose installed
- `.env` file configured with database credentials

#### Quick Start with Docker

```bash
# Start all services (PostgreSQL, Redis, API)
docker compose up --build

# The API will be available at http://localhost:8000

# View logs
docker compose logs -f laker-api

# Stop all services
docker compose down

# Stop and remove volumes (reset database)
docker compose down -v
```

#### Connect to PostgreSQL in DBeaver

1. Open DBeaver → **Database → New Database Connection**
2. Select **PostgreSQL** and click **Next**
3. Enter connection details:
   - **Server Host**: `localhost`
   - **Port**: `5432`
   - **Database**: `laker_db` (from `.env`)
   - **Username**: `your_db_user` (from `.env`)
   - **Password**: `your_db_password` (from `.env`)
4. Click **Test Connection** and **Finish**

#### API Documentation

Once running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

### Option 2: Local Setup (Without Docker)

#### Prerequisites

- Python 3.12+
- PostgreSQL 16+ (installed locally)
- Redis (optional, for caching)

#### Step 1: Setup Python Environment

```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
# On macOS/Linux:
source .venv/bin/activate
# On Windows:
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

#### Step 2: Setup PostgreSQL

**Option A: Using Homebrew (macOS)**
```bash
brew install postgresql
brew services start postgresql
psql postgres
```

**Option B: Using apt (Linux)**
```bash
sudo apt-get update
sudo apt-get install postgresql postgresql-contrib
sudo service postgresql start
psql -U postgres
```

**Option C: Windows**
- Download PostgreSQL installer from [postgresql.org](https://www.postgresql.org/download/windows/)
- Follow the installation wizard
- Remember the superuser password you set

#### Step 3: Create Database

```bash
# Connect to PostgreSQL
psql -U postgres

# Create database and user
CREATE DATABASE laker_db;
CREATE USER your_db_user WITH PASSWORD 'your_db_password';
ALTER ROLE your_db_user SET client_encoding TO 'utf8';
ALTER ROLE your_db_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE your_db_user SET default_transaction_deferrable TO on;
ALTER ROLE your_db_user SET default_transaction_level TO 'read committed';
ALTER USER your_db_user CREATEDB;

# Exit psql
\q
```

#### Step 4: Configure Environment

Copy or update your `.env` file:

```env
APP_ENV=development
APP_DEBUG=true

DB_DRIVER=postgresql+asyncpg
DB_USER=your_db_user
DB_PASSWORD=your_db_password
DB_HOST=localhost
DB_PORT=5432
DB_NAME=laker_db

JWT_SECRET_KEY=your_jwt_secret_key_here

RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS=50
RATE_LIMIT_WINDOW_SECONDS=60

REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
CACHE_ENABLED=true
CACHE_DEFAULT_TTL_SECONDS=300
```

**Key differences from Docker:**
- `DB_HOST=localhost` (not `postgres`)
- `REDIS_HOST=localhost` (not `redis`)

#### Step 5: Run the API

```bash
# Start the development server with auto-reload
uvicorn app.main:app --reload

# Server will be available at http://localhost:8000
```

#### Step 6: Verify Setup

Visit in your browser:
- **Swagger UI**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/api/v1/health
- **ReDoc**: http://localhost:8000/redoc

---

## Running Tests

```bash
# Install test dependencies (if not already installed)
pip install pytest pytest-asyncio httpx

# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/unit/test_security.py

# Run with coverage
pytest --cov=app
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