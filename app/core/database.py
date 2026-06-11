import sqlite3
import os
import logging
from contextlib import contextmanager
from typing import Generator
from app.core.config import settings

logger = logging.getLogger(__name__)

def configure_connection(conn: sqlite3.Connection) -> None:
    """Configures the sqlite3 connection with required PRAGMAs."""
    conn.row_factory = sqlite3.Row
    
    # Enable PRAGMAs
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA busy_timeout = 20000;")
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA temp_store = MEMORY;")

def seed_admin_user(conn: sqlite3.Connection) -> None:
    """Seeds the default admin user if the usuarios table is empty."""
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT COUNT(*) FROM usuarios;")
        count = cursor.fetchone()[0]
        if count == 0:
            logger.info("No users found in database. Seeding default administrator user...")
            import uuid
            from datetime import datetime, timezone
            import bcrypt
            
            admin_id = uuid.uuid4().hex
            admin_username = settings.DEFAULT_ADMIN_USERNAME
            admin_password = settings.DEFAULT_ADMIN_PASSWORD
            
            # Hash password
            salt = bcrypt.gensalt()
            hashed = bcrypt.hashpw(admin_password.encode('utf-8'), salt).decode('utf-8')
            
            cursor.execute(
                """
                INSERT INTO usuarios (id, nombre, username, password_hash, rol, activo, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    admin_id,
                    "Administrador",
                    admin_username,
                    hashed,
                    "ADMINISTRADOR",
                    1,
                    datetime.now(timezone.utc).isoformat()
                )
            )
            conn.commit()
            logger.warning(
                f"Seeded default administrator user '{admin_username}' with role 'ADMINISTRADOR'. "
                "IMPORTANT: Please change the default password in production!"
            )
    except Exception as e:
        logger.error(f"Error seeding admin user: {e}", exc_info=True)
        raise e

def init_db() -> None:
    """
    Initializes the database.
    Creates tables via schema.sql if the database file does not exist,
    or if it exists but is uninitialized (missing key tables).
    Also seeds the default admin user if no users are registered.
    """
    db_file = settings.DB_URL
    schema_file = settings.SCHEMA_PATH
    
    # Ensure database directory exists
    db_dir = os.path.dirname(db_file)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)
        
    db_exists = os.path.exists(db_file)
    needs_schema = not db_exists
    
    if db_exists:
        # Check if database is empty or missing key tables
        try:
            with sqlite3.connect(db_file) as conn:
                configure_connection(conn)
                conn.execute("SELECT 1 FROM usuarios LIMIT 1;").fetchone()
            logger.info(f"Database already exists at {db_file} and schema is valid.")
        except sqlite3.OperationalError:
            logger.warning(f"Database at {db_file} exists but lacks required tables. Re-initializing schema...")
            needs_schema = True
            
    if needs_schema:
        if not os.path.exists(schema_file):
            raise FileNotFoundError(f"Schema file not found at: {schema_file}")
            
        logger.info(f"Applying schema.sql to {db_file}...")
        with sqlite3.connect(db_file) as conn:
            configure_connection(conn)
            with open(schema_file, "r", encoding="utf-8") as f:
                schema_sql = f.read()
            conn.executescript(schema_sql)
            conn.commit()
        logger.info("Database initialized successfully with schema.sql.")
        
    # Seed the admin user if table is empty
    with sqlite3.connect(db_file) as conn:
        configure_connection(conn)
        seed_admin_user(conn)

@contextmanager
def get_db_conn() -> Generator[sqlite3.Connection, None, None]:
    """
    Context manager for database connections.
    Enforces transactional boundaries. Commits on success, rolls back on exception.
    """
    conn = sqlite3.connect(settings.DB_URL)
    configure_connection(conn)
    try:
        yield conn
        # Check if there is an active transaction to commit
        if conn.in_transaction:
            conn.commit()
    except Exception as e:
        logger.error(f"Database exception occurred: {e}. Rolling back transaction.")
        try:
            conn.rollback()
        except sqlite3.ProgrammingError:
            # Connection might be closed or invalid
            pass
        raise e
    finally:
        conn.close()

# Dependency for FastAPI endpoints
def get_db() -> Generator[sqlite3.Connection, None, None]:
    """FastAPI Dependency for database connection."""
    with get_db_conn() as conn:
        yield conn
