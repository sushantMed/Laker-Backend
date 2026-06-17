# Database Migrations

Alembic manages the schema. PostgreSQL runs in Docker (`docker-compose.yml`).

## Prerequisites

```bash
docker compose up -d postgres
```

A populated `.env` is required (`db_driver`, `db_user`, `db_password`, `db_host`, `db_port`, `db_name`).

For local commands against the Docker database, set `db_host=localhost`.

## Generate a migration

```bash
alembic revision --autogenerate -m "describe change"
```

## Create an empty migration

```bash
alembic revision -m "describe change"
```

## Apply migrations

```bash
alembic upgrade head
```

```bash
alembic upgrade +1
```

## Roll back

```bash
alembic downgrade -1
```

```bash
alembic downgrade base
```

## Inspect state

```bash
alembic current
```

```bash
alembic history --verbose
```

```bash
alembic heads
```

## Run inside the API container

```bash
docker compose exec api alembic upgrade head
```

```bash
docker compose exec api alembic revision --autogenerate -m "describe change"
```

The `api` service runs `alembic upgrade head` automatically on startup.

## Seed data

Seeding does not run on application startup. Run it manually after migrating.

```bash
python -m app.scripts.seed_users
```

```bash
python -m app.scripts.seed_members
```

```bash
docker compose exec api python -m app.scripts.seed_users
```

```bash
docker compose exec api python -m app.scripts.seed_members
```
