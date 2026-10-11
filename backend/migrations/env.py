"""
Prop AI - Alembic migration environment.

Connects Alembic to our SQLAlchemy models (what the schema should be)
and to the database URL from .env (where to apply it).
"""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.config import get_settings
from app.models import Base

config = context.config

# Set up logging from alembic.ini.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Read the database URL from our validated settings instead of alembic.ini,
# so the password stays in .env. ConfigParser treats '%' specially, so escape it.
config.set_main_option("sqlalchemy.url", get_settings().database_url.replace("%", "%%"))

# The models' metadata: Alembic compares this with the real database.
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Generate SQL scripts without connecting to a database."""
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Connect to the database and apply migrations directly."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,  # also detect column type changes
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()