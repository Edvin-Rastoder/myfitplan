#Small unit tests for the SQLite connection helper

import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from database import db 


class TestDatabaseHelper(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.db_path = Path(self.temp_dir.name) / "test.db"

    def test_explicit_path_takes_priority_over_environment(self):
        # arrange: set a different database path in the environment
        with patch.dict(os.environ, {"MYFITPLAN_DB_PATH": "environment.db"}):
            # action: request a connection path explicitly.
            result = db.get_db_path(self.db_path)

        # assert: the explicit path
        self.assertEqual(result, self.db_path)

    def test_init_can_run_twice_without_erasing_data(self):
        # arrange: initialize the database and save one user
        db.init_db(self.db_path)
        with db.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO users (email, password_hash) VALUES (?, ?)",
                ("student@example.com", "placeholder-hash"),
            )

        # action: initialize the same db
        db.init_db(self.db_path)
        with db.connect(self.db_path) as conn:
            user = conn.execute(
                "SELECT email FROM users WHERE email = ?", ("student@example.com",)
            ).fetchone()

        # assert: existing records remain in the db
        self.assertIsNotNone(user)
        self.assertEqual(user["email"], "student@example.com")

    def test_connection_enforces_foreign_keys_and_closes(self):
        # arrange: create the tables & open a connection through db.connect()
        db.init_db(self.db_path)

        # action: check the setting and try to save a day for a missing plan
        with db.connect(self.db_path) as conn:
            foreign_keys_enabled = conn.execute("PRAGMA foreign_keys").fetchone()[0]
            with self.assertRaises(sqlite3.IntegrityError):
                conn.execute("INSERT INTO workout_days (plan_id) VALUES (?)", (999,))

        # assert: the invalid row was rejected & the connection was closed
        self.assertEqual(foreign_keys_enabled, 1)
        with self.assertRaises(sqlite3.ProgrammingError):
            conn.execute("SELECT 1")

    def test_connection_rolls_back_after_an_error(self):
        # arrange: create a fresh db.
        db.init_db(self.db_path)

        # action: write a row and then raise an error
        with self.assertRaisesRegex(ValueError, "cancel this change"):
            with db.connect(self.db_path) as conn:
                conn.execute(
                    "INSERT INTO users (email, password_hash) VALUES (?, ?)",
                    ("rollback@example.com", "placeholder-hash"),
                )
                raise ValueError("cancel this change")

        # assert: the row was not saved & the connection was closed
        with db.connect(self.db_path) as check_conn:
            count = check_conn.execute(
                "SELECT COUNT(*) FROM users WHERE email = ?", ("rollback@example.com",)
            ).fetchone()[0]
        self.assertEqual(count, 0)
        with self.assertRaises(sqlite3.ProgrammingError):
            conn.execute("SELECT 1")


if __name__ == "__main__":
    unittest.main()
