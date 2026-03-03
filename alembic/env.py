import sys
import os
from pathlib import Path

# Load .env file before importing app modules
from dotenv import load_dotenv

# Find the .env file in the project root (parent of alembic directory)
env_path = Path(__file__).parent.parent / '.env'
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    # Try loading from current directory as fallback
    load_dotenv()

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Set database URL from environment variable - use same config as app
try:
    from app.core.config import settings
    database_url = settings.DATABASE_URL
    config.set_main_option("sqlalchemy.url", database_url)
except Exception as e:
    # Fallback to environment variable (now loaded from .env file) or default
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        config.set_main_option("sqlalchemy.url", database_url)
    print(f"[INFO] Using fallback database URL configuration: {e}")

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
from app.core.database import Base

# Dynamically import all model modules so their tables are registered in Base.metadata
import importlib
import pkgutil
import app.models as models_pkg

for _finder, module_name, _ispkg in pkgutil.iter_modules(models_pkg.__path__):
    importlib.import_module(f"{models_pkg.__name__}.{module_name}")

target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


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
    
    # Configure context for offline mode
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        as_sql=True,
        dialect_opts={"paramstyle": "named"},
        transaction_per_migration=True,
        compare_type=True,
        compare_server_default=True,
        render_as_batch=True,
    )

    # In offline mode, we don't need a transaction context
    # since we're just generating SQL scripts
    try:
        context.run_migrations()
    except Exception as e:
        # Handle specific cases where offline mode might fail
        if "Target database is not up to date" in str(e):
            print("[INFO] Cannot check database status in offline mode")
            print("[INFO] Use 'alembic current' to see migration status")
            return
        else:
            raise e


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = None
    connection_successful = False
    
    try:
        connectable = engine_from_config(
            config.get_section(config.config_ini_section, {}),
            prefix="sqlalchemy.",
            poolclass=pool.NullPool,
        )
        
        # Test connection
        with connectable.connect() as test_conn:
            connection_successful = True
        
    except Exception as e:
        # Connection error - try offline mode
        print(f"[WARNING] Database connection failed: {e}")
        print("[INFO] Falling back to offline mode...")
        run_migrations_offline()
        return
    
    # If connection successful, run migrations
    def include_object(object, name, type_, reflected, compare_to):
        if type_ == "table" and reflected and compare_to is None:
            return False
        return True

    with connectable.connect() as connection:
        context.configure(
            connection=connection, 
            target_metadata=target_metadata,
            transaction_per_migration=True,
            compare_type=True,
            compare_server_default=True,
            include_object=include_object,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
