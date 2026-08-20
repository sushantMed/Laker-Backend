import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

# Import the package, not the modules one by one: target_metadata must hold
# every table, or autogenerate reads a missing model as a table to drop.
import app.models  # noqa: F401
from alembic import context
from app.core.config import settings
from app.database.base import Base

config = context.config
# Escape '%' so ConfigParser doesn't treat URL-encoded credentials
# (e.g. '%23' from a '#' in the password) as interpolation syntax.
config.set_main_option("sqlalchemy.url", settings.database_url.replace("%", "%%"))

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def include_object(_object, name, type_, _reflected, _compare_to) -> bool:
    """Keep autogenerate to the tables the models declare.

    The app shares its Oracle schema with tables it does not own -- Oracle's
    own HELP and SCHEDULER_* among them. Without this filter every one of them
    reflects as a table no model declares, i.e. as a table to drop.
    """
    if type_ == "table":
        return name in target_metadata.tables
    return True


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        include_object=include_object,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        include_object=include_object,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    engine_args: dict = {"poolclass": pool.NullPool}
    # The app's tables sit in the SYSTEM tablespace, which the Oracle dialect
    # hides from reflection by default -- autogenerate would then read every
    # table that already exists as one still to be created. Oracle-only
    # argument, so it is passed only for an Oracle URL.
    if config.get_main_option("sqlalchemy.url").startswith("oracle"):
        engine_args["exclude_tablespaces"] = []

    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        **engine_args,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
