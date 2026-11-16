# Tests for db.migrate_db, which adds newer columns to existing databases.
# Each test uses a temporary SQLite file, never the repo's myfitplan.db.

import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # Backend/
from database import db

NEW_COLUMNS = ["users.name", "workout_plans.duration_minutes", "workout_logs.duration_seconds",
               "users.email_reminders_enabled"]

# The affected tables as they were before name, duration_minutes and duration_seconds existed
OLD_SCHEMA = """
CREATE TABLE users (
    user_id INTEGER PRIMARY KEY,
    email TEXT UNIQUE,
    password_hash TEXT NOT NULL
);
CREATE TABLE workout_plans (
    plan_id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users (user_id),
    start_date TEXT NOT NULL,
    end_date TEXT NOT NULL
);
CREATE TABLE workout_days (
    workout_day_id INTEGER PRIMARY KEY,
    plan_id INTEGER NOT NULL REFERENCES workout_plans (plan_id),
    weekday INTEGER
);
CREATE TABLE workout_logs (
    workout_log_id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users (user_id),
    workout_day_id INTEGER REFERENCES workout_days (workout_day_id),
    completed_on TEXT NOT NULL
);
INSERT INTO users VALUES (1, 'old.user@example.com', 'old-hash');
INSERT INTO workout_plans VALUES (1, 1, '2026-11-02', '2026-11-08');
INSERT INTO workout_days VALUES (1, 1, 2);
INSERT INTO workout_logs VALUES (1, 1, 1, '2026-11-03');
"""


def columns(path, table):
    with db.connect(path) as conn:
        return [row["name"] for row in conn.execute(f"PRAGMA table_info({table})")]


def snapshot(path):
    """Every table's definition and rows, to compare a database before and after."""
    with db.connect(path) as conn:
        entries = conn.execute("SELECT type, name, sql FROM sqlite_master ORDER BY name").fetchall()
        return {
            name: (sql, [tuple(row) for row in conn.execute(f"SELECT * FROM {name}")] if kind == "table" else None)
            for kind, name, sql in entries
        }


class MigrationTest(unittest.TestCase):
    def setUp(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        self.db_path = Path(temp_dir.name) / "test.db"

    def make_old_database(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript(OLD_SCHEMA)
        conn.close()

    def test_fresh_database_already_has_the_new_columns(self):
        db.init_db(self.db_path)
        self.assertIn("name", columns(self.db_path, "users"))
        self.assertIn("duration_minutes", columns(self.db_path, "workout_plans"))
        self.assertIn("duration_seconds", columns(self.db_path, "workout_logs"))
        self.assertEqual(db.migrate_db(self.db_path), [])

    def test_migration_adds_columns_and_keeps_existing_rows(self):
        self.make_old_database()

        self.assertEqual(db.migrate_db(self.db_path), NEW_COLUMNS)

        with db.connect(self.db_path) as conn:
            user = conn.execute("SELECT user_id, email, password_hash, name FROM users").fetchone()
            plan = conn.execute("SELECT plan_id, start_date, end_date, duration_minutes FROM workout_plans").fetchone()
            log = conn.execute("SELECT workout_log_id, completed_on, duration_seconds FROM workout_logs").fetchone()
        self.assertEqual(tuple(user), (1, "old.user@example.com", "old-hash", None))
        self.assertEqual(tuple(plan), (1, "2026-11-02", "2026-11-08", None))
        self.assertEqual(tuple(log), (1, "2026-11-03", None))

        # new logs can store a duration; negative durations are rejected
        with db.connect(self.db_path) as conn:
            conn.execute("UPDATE workout_logs SET duration_seconds = 1800 WHERE workout_log_id = 1")
            with self.assertRaises(sqlite3.IntegrityError):
                conn.execute("UPDATE workout_logs SET duration_seconds = -1 WHERE workout_log_id = 1")

    def test_second_migration_changes_nothing(self):
        self.make_old_database()
        db.migrate_db(self.db_path)
        before = snapshot(self.db_path)

        self.assertEqual(db.migrate_db(self.db_path), [])
        self.assertEqual(snapshot(self.db_path), before)

    def test_missing_database_is_not_created(self):
        with self.assertRaises(FileNotFoundError):
            db.migrate_db(self.db_path)
        self.assertFalse(self.db_path.exists())


if __name__ == "__main__":
    unittest.main()
