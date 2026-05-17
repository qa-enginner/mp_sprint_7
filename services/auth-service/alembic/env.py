import asyncio
import re
import sys
import os
from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine
from alembic import context
from db.postgres import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Добавляем путь к src для импорта моделей
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))


target_metadata = Base.metadata


def include_object(object, name, type_, reflected, compare_to):
    """
    Exclude Django tables from Alembic autogeneration.
    """
    if type_ == "table":
        # Exclude Django tables (django_, auth_, users_user)
        if name.startswith(('django_', 'auth_', 'users_user')):
            return False
    return True


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_object=include_object,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """In this scenario we need to create an Engine
    and associate a connection with the context."""

    # Override sqlalchemy.url with environment variables if present
    section = config.get_section(config.config_ini_section)
    url = section.get("sqlalchemy.url")

    if not url:
        url = config.get_main_option("sqlalchemy.url")

    # Replace environment variables in URL
    def replace_env(match):
        var_name = match.group(1)
        return os.environ.get(var_name, match.group(0))

    if url:
        url = re.sub(r'\$\{([^}]+)\}', replace_env, url)

    connectable = create_async_engine(
        url,
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
