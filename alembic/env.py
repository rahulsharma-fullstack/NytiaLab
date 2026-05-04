"""Alembic migration environment.

Configured to use the application's Settings and Base metadata so that
`alembic revision --autogenerate` detects model changes.
"""

from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context
from app.config import settings
from app.database import Base

# Import all models so Base.metadata knows about every table.
# The noqa disables "imported but unused" lint warnings — the side effect is the point.
from app.models import (  # noqa: F401
    Employee,
    HealthRecord,
    Product,
    ProductCondition,
    ProductFactor,
    Recommendation,
)

# Alembic config from alembic.ini
config = context.config

# Override the sqlalchemy.url in alembic.ini with our app's URL.
config.set_main_option("sqlalchemy.url", settings.database_url)

# Python logging config from alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Target metadata for 'autogenerate' support — this is what Alembic compares
# against the live database to detect what needs to change.
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode — generate SQL scripts without DB connection."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode — execute against the live DB."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,  # Detect column type changes
            compare_server_default=True,  # Detect default value changes
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
