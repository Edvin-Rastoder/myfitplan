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
    #Commits when the block succeeds, rolls back if it raises, and always
    #closes the connection
    conn = sqlite3.connect(get_db_path(db_path))
    try:
        # SQLite leaves foreign keys off unless each connection turns them on.
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
    #Create any missing tables and indexes from schema.sql.
    path = get_db_path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    schema = SCHEMA_PATH.read_text(encoding="utf-8")
    with connect(path) as conn:
        conn.executescript(schema)
    return path


def main():
    parser = argparse.ArgumentParser(description="myfitplan database tools")
    subcommands = parser.add_subparsers(dest="command", required=True)
    init_parser = subcommands.add_parser("init", help="create the database from schema.sql")
    init_parser.add_argument(
        "--db-path",
        help=f"database file (default: ${DB_PATH_ENV_VAR} or {DEFAULT_DB_PATH})",
    )
    args = parser.parse_args()

    if args.command == "init":
        path = init_db(args.db_path)
        print(f"Initialized database at {path.resolve()}")


if __name__ == "__main__":
    main()
