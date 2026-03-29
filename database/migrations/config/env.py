from logging.config import fileConfig

from sqlalchemy import MetaData
from alembic import context
import os
import sqlite3

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
# Guard: when invoked programmatically (e.g. run_auto_migrations), the caller
# sets configure_logger=False to prevent Alembic wiping our tiered log setup.
if config.config_file_name is not None and config.attributes.get('configure_logger', True):
    fileConfig(config.config_file_name)

# Config DB doesn't use SQLAlchemy models right now.
# We will just pass empty metadata and a raw connection if needed,
# or we can define a minimal metadata object for schema diffs if we wanted.
# For now, just allow raw DDL scripts to run.
target_metadata = MetaData()

from core.settings import config_manager
from sqlalchemy import create_engine
engine = create_engine(f"sqlite:///{config_manager.database_path}")

def run_migrations_offline() -> None:
    context.configure(
        url=str(engine.url),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata,
            render_as_batch=True
        )

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
