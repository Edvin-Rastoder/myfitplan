# Integration test: the Flask routes in Backend/app.py together with SQLite.
# Requests go through Flask's test client; results are checked on a separate
# SQLite connection. Uses a temporary database file, never the repo's myfitplan.db.

import contextlib
import importlib
import io
import os
import sys
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))  # app.py imports database.db from Backend/

from database.db import DB_PATH_ENV_VAR, DEFAULT_DB_PATH, connect, get_db_path, init_db 
from werkzeug.security import check_password_hash

PASSWORD = "integration-test-password"
WORKOUT_REQUEST = {"goal": "muscle_gain", "experience": "beginner", "days": 3, "duration": 30}
NOT_LOGGED_IN_ERROR = "You must be logged in to generate a workout"


def local_db_state():
    return DEFAULT_DB_PATH.stat().st_mtime_ns if DEFAULT_DB_PATH.exists() else None


def restore_db_env(old_value):
    if old_value is None:
        os.environ.pop(DB_PATH_ENV_VAR, None)
    else:
        os.environ[DB_PATH_ENV_VAR] = old_value


class FlaskSQLiteIntegrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.local_db_before = local_db_state()
        temp_dir = tempfile.TemporaryDirectory(prefix="myfitplan-integration-")
        cls.addClassCleanup(temp_dir.cleanup)
        cls.addClassCleanup(restore_db_env, os.environ.get(DB_PATH_ENV_VAR))

        # The env var must point at the temporary file before the app is imported.
        cls.db_path = Path(temp_dir.name) / "integration.db"
        os.environ[DB_PATH_ENV_VAR] = str(cls.db_path)
        with contextlib.redirect_stdout(io.StringIO()):  # app.py prints debug lines on import
            cls.app = importlib.import_module("app").app
        cls.app.config["TESTING"] = True

        init_db(cls.db_path)
        if get_db_path() != cls.db_path:
            raise RuntimeError(f"app would use {get_db_path()}, not the temporary database")

    @classmethod
    def tearDownClass(cls):
        if local_db_state() != cls.local_db_before:
            raise AssertionError(f"the test created or modified {DEFAULT_DB_PATH}")

    # helpers

    def query(self, sql, params=()):
        with connect(self.db_path) as conn:  # a separate connection from the app's own
            return conn.execute(sql, params).fetchall()

    def plan_ids(self):
        return {row["plan_id"] for row in self.query("SELECT plan_id FROM workout_plans")}

    def create_user(self, client, email):
        response = client.post("/create-user", json={"email": email, "password_hash": PASSWORD})
        self.assertEqual(response.status_code, 201, response.get_json())
        user_id = response.get_json()["user_id"]
        self.assertIsInstance(user_id, int)
        cookie = client.get_cookie("session_token")
        self.assertIsNotNone(cookie, "signup did not set a session_token cookie")

        users = self.query(
            "SELECT email, phone, password_hash, sms_reminders_enabled FROM users WHERE user_id = ?",
            (user_id,),
        )
        self.assertEqual(len(users), 1)
        self.assertEqual(users[0]["email"], email)
        self.assertIsNone(users[0]["phone"])
        self.assertEqual(users[0]["sms_reminders_enabled"], 0)
        self.assertNotEqual(users[0]["password_hash"], PASSWORD, "password stored in plain text")
        self.assertTrue(check_password_hash(users[0]["password_hash"], PASSWORD))

        sessions = self.query(
            "SELECT session_token, created_at, expires_at FROM sessions WHERE user_id = ?", (user_id,)
        )
        self.assertEqual([row["session_token"] for row in sessions], [cookie.value])
        self.assertGreater(sessions[0]["expires_at"], sessions[0]["created_at"])
        return user_id, cookie.value

    def generate(self, client):
        with contextlib.redirect_stdout(io.StringIO()):  # the route prints debug lines
            return client.post("/generate-workout", json=WORKOUT_REQUEST)

    def assert_not_logged_in(self, response):
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.get_json(), {"error": NOT_LOGGED_IN_ERROR})

    # tests

    def test_signup_generate_plan_and_logout(self):
        client = self.app.test_client()
        user_id, token = self.create_user(client, "flow@example.com")

        plans_before = self.plan_ids()
        response = self.generate(client)
        self.assertEqual(response.status_code, 200, response.get_json())
        body = response.get_json()
        self.assertEqual(body["workout_plan"], ["Full Body", "Full Body", "Full Body"])
        self.assertEqual(body["workout_type"], "Strength Training")
        self.assertEqual(body["workout_level"], "Beginner Level")
        self.assertEqual(len(body["weekly_workouts"]), 3)
        for generated_day in body["weekly_workouts"]:
            self.assertEqual(len(generated_day["exercises"]), 3)  # 30 minutes -> 3 exercises

        # Exactly one new plan, owned by this user.
        new_plan_ids = self.plan_ids() - plans_before
        self.assertEqual(len(new_plan_ids), 1)
        plan = self.query(
            "SELECT plan_id, user_id, start_date, end_date FROM workout_plans WHERE plan_id = ?",
            (new_plan_ids.pop(),),
        )[0]
        self.assertEqual(plan["user_id"], user_id)
        start = date.fromisoformat(plan["start_date"])
        self.assertEqual(date.fromisoformat(plan["end_date"]) - start, timedelta(days=6))

        # Three workout days on consecutive weekdays from the start date.
        days = self.query(
            "SELECT workout_day_id, weekday FROM workout_days WHERE plan_id = ? ORDER BY workout_day_id",
            (plan["plan_id"],),
        )
        self.assertEqual([day["weekday"] for day in days],
                         [(start + timedelta(days=offset)).isoweekday() for offset in range(3)])

        # Each day's prescribed exercises match what the route returned for that day.
        for day, generated_day in zip(days, body["weekly_workouts"]):
            exercises = self.query(
                "SELECT exercise_name, sets_count, repetitions_count FROM workout_exercises"
                " WHERE workout_day_id = ? ORDER BY workout_exercise_id",
                (day["workout_day_id"],),
            )
            self.assertEqual([row["exercise_name"] for row in exercises],
                             [exercise["name"] for exercise in generated_day["exercises"]])
            for row in exercises:
                self.assertEqual((row["sets_count"], row["repetitions_count"]), (3, 10))

        # Logging out deletes the session and stops plan generation.
        response = client.post("/logout")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"message": "Logged out"})
        self.assertIsNone(client.get_cookie("session_token"))
        self.assertEqual(self.query("SELECT * FROM sessions WHERE session_token = ?", (token,)), [])
        self.assert_not_logged_in(self.generate(client))

        # The old token is rejected by the server, not just dropped by the client.
        stale_client = self.app.test_client()
        stale_client.set_cookie("session_token", token)
        self.assert_not_logged_in(self.generate(stale_client))
        self.assertEqual(len(self.query("SELECT plan_id FROM workout_plans WHERE user_id = ?", (user_id,))), 1)

    def test_generate_without_session_is_rejected(self):
        user_id, _ = self.create_user(self.app.test_client(), "owner@example.com")

        plans_before = self.plan_ids()
        anonymous_client = self.app.test_client()
        self.assert_not_logged_in(self.generate(anonymous_client))
        self.assertEqual(self.plan_ids(), plans_before)
        self.assertEqual(self.query("SELECT plan_id FROM workout_plans WHERE user_id = ?", (user_id,)), [])

    def test_login_with_fresh_client_authorizes_generation(self):
        user_id, signup_token = self.create_user(self.app.test_client(), "login@example.com")

        login_client = self.app.test_client()
        response = login_client.post("/login", json={"email": "login@example.com", "password_hash": PASSWORD})
        self.assertEqual(response.status_code, 200, response.get_json())
        self.assertEqual(response.get_json(), {"user_id": user_id})
        cookie = login_client.get_cookie("session_token")
        self.assertIsNotNone(cookie, "login did not set a session_token cookie")
        self.assertNotEqual(cookie.value, signup_token)
        tokens = {row["session_token"] for row in self.query(
            "SELECT session_token FROM sessions WHERE user_id = ?", (user_id,))}
        self.assertEqual(tokens, {signup_token, cookie.value})

        response = self.generate(login_client)
        self.assertEqual(response.status_code, 200, response.get_json())
        plans = self.query("SELECT user_id FROM workout_plans WHERE user_id = ?", (user_id,))
        self.assertEqual(len(plans), 1)


if __name__ == "__main__":
    unittest.main()
