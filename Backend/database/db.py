#SQLite connection helpers for myfitplan.
#Initialize a local database from schema.sql
import argparse
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

DATABASE_DIR = Path(__file__).resolve().parent
SCHEMA_PATH = DATABASE_DIR / "schema.sql"
DEFAULT_DB_PATH = DATABASE_DIR / "myfitplan.db"
DB_PATH_ENV_VAR = "MYFITPLAN_DB_PATH"


def get_db_path(db_path=None):
    if db_path is not None:
        return Path(db_path)
    return Path(os.environ.get(DB_PATH_ENV_VAR, DEFAULT_DB_PATH))


@contextmanager
def connect(db_path=None):
    #Open a connection with foreign keys enforced.
    #Commits when the block succeeds, rolls back if it raises, and always closes the connection
    conn = sqlite3.connect(get_db_path(db_path))
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.row_factory = sqlite3.Row
        yield conn
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db(db_path=None):
    # Create any missing tables and indexes from schema.sql.
    path = get_db_path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    schema = SCHEMA_PATH.read_text(encoding="utf-8")
    with connect(path) as conn:
        conn.executescript(schema)
    return path


# Columns added to schema.sql after databases had already been created
# CREATE TABLE IF NOT EXISTS skips existing tables, so init_db cannot add them; migrate_db does
MIGRATION_COLUMNS = [
    ("users", "name", "TEXT"),
    ("workout_plans", "duration_minutes", "INTEGER CHECK (duration_minutes IN (15, 30, 45, 60))"),
    ("workout_logs", "duration_seconds",
     "INTEGER CHECK (duration_seconds IS NULL OR (typeof(duration_seconds) = 'integer' AND duration_seconds >= 0))"),
    ("users", "email_reminders_enabled",
     "INTEGER NOT NULL DEFAULT 0 CHECK (email_reminders_enabled IN (0, 1)"
     " AND (email_reminders_enabled = 0 OR email IS NOT NULL))"),
]

def migrate_db(db_path=None):
    path = get_db_path(db_path)
    if not path.is_file():
        # sqlite3.connect would silently create a new, empty database here
        raise FileNotFoundError(f"No database at {path}. Use 'init' to create a new one.")

    added = []
    with connect(path) as conn:
        conn.execute("BEGIN")  # all columns are added together, or none if anything fails
        for table, column, definition in MIGRATION_COLUMNS:
            existing = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}
            if not existing:
                raise RuntimeError(f"{path} has no {table} table; is it a myfitplan database?")
            if column not in existing:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
                added.append(f"{table}.{column}")
    return added


def main():
    parser = argparse.ArgumentParser(description="myfitplan database tools")
    subcommands = parser.add_subparsers(dest="command", required=True)
    db_path_help = f"database file (default: ${DB_PATH_ENV_VAR} or {DEFAULT_DB_PATH})"
    init_parser = subcommands.add_parser("init", help="create the database from schema.sql")
    init_parser.add_argument("--db-path", help=db_path_help)
    migrate_parser = subcommands.add_parser("migrate", help="add missing columns to an existing database")
    migrate_parser.add_argument("--db-path", help=db_path_help)
    args = parser.parse_args()

    if args.command == "init":
        path = init_db(args.db_path)
        print(f"Initialized database at {path.resolve()}")

    if args.command == "migrate":
        try:
            added = migrate_db(args.db_path)
        except (FileNotFoundError, RuntimeError) as error:
            parser.exit(1, f"Migration failed: {error}\n")
        path = get_db_path(args.db_path).resolve()
        if added:
            print(f"Added columns to {path}: {', '.join(added)}")
        else:
            print(f"{path} is already up to date")


if __name__ == "__main__":
    main()
