# Tests for saving a generated plan and reading it back through GET /workout-plans/latest.
# Each test uses a fresh temporary SQLite file, never the repo's myfitplan.db.
#
# Run from the repository root:
#     python3 -m unittest discover -s Backend/tests -v

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

from database.db import DB_PATH_ENV_VAR, DEFAULT_DB_PATH, connect, get_db_path, init_db  # noqa: E402

PASSWORD = "schedule-test-password"
LATEST_PLAN_URL = "/workout-plans/latest"


def local_db_state():
    return DEFAULT_DB_PATH.stat().st_mtime_ns if DEFAULT_DB_PATH.exists() else None


def restore_db_env(old_value):
    if old_value is None:
        os.environ.pop(DB_PATH_ENV_VAR, None)
    else:
        os.environ[DB_PATH_ENV_VAR] = old_value


class SavedScheduleTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.local_db_before = local_db_state()
        temp_dir = tempfile.TemporaryDirectory(prefix="myfitplan-schedule-")
        cls.addClassCleanup(temp_dir.cleanup)
        cls.addClassCleanup(restore_db_env, os.environ.get(DB_PATH_ENV_VAR))
        cls.temp_path = Path(temp_dir.name)

        # The env var must point at a temporary file before the app is imported.
        os.environ[DB_PATH_ENV_VAR] = str(cls.temp_path / "import.db")
        with contextlib.redirect_stdout(io.StringIO()):  # app.py prints debug lines on import
            cls.app = importlib.import_module("app").app
        cls.app.config["TESTING"] = True

    @classmethod
    def tearDownClass(cls):
        if local_db_state() != cls.local_db_before:
            raise AssertionError(f"the tests created or modified {DEFAULT_DB_PATH}")

    def setUp(self):
        # a fresh database for every test
        self.db_path = self.temp_path / f"{self.id().rsplit('.', 1)[-1]}.db"
        os.environ[DB_PATH_ENV_VAR] = str(self.db_path)
        init_db(self.db_path)
        self.assertEqual(get_db_path(), self.db_path)

    # helpers

    def query(self, sql, params=()):
        with connect(self.db_path) as conn:  # a separate connection from the app's own
            return conn.execute(sql, params).fetchall()

    def signup(self, email):
        client = self.app.test_client()
        response = client.post("/create-user", json={"email": email, "password_hash": PASSWORD})
        self.assertEqual(response.status_code, 201, response.get_json())
        return client, response.get_json()["user_id"]

    def generate(self, client, days):
        request = {"goal": "muscle_gain", "experience": "beginner", "days": days, "duration": 30}
        with contextlib.redirect_stdout(io.StringIO()):  # the route prints debug lines
            response = client.post("/generate-workout", json=request)
        self.assertEqual(response.status_code, 200, response.get_json())
        return response.get_json()

    def latest_plan(self, client):
        response = client.get(LATEST_PLAN_URL)
        self.assertEqual(response.status_code, 200, response.get_json())
        return response.get_json()

    def plan_ids_for(self, user_id):
        rows = self.query("SELECT plan_id FROM workout_plans WHERE user_id = ? ORDER BY plan_id", (user_id,))
        return [row["plan_id"] for row in rows]

    # tests

    def test_generated_plan_saves_workout_types_and_reads_back(self):
        client, user_id = self.signup("reader@example.com")
        generated = self.generate(client, 3)

        # the generate response keeps its existing shape
        self.assertEqual(set(generated), {"message", "workout_plan", "weekly_workouts", "workout_type", "workout_level"})
        self.assertEqual(generated["workout_plan"], ["Full Body", "Full Body", "Full Body"])

        [plan_id] = self.plan_ids_for(user_id)
        saved_types = self.query(
            "SELECT description FROM workout_days WHERE plan_id = ? ORDER BY workout_day_id", (plan_id,))
        self.assertEqual([row["description"] for row in saved_types], ["Full Body", "Full Body", "Full Body"])

        plan = self.latest_plan(client)
        saved = self.query("SELECT start_date, end_date FROM workout_plans WHERE plan_id = ?", (plan_id,))[0]
        self.assertEqual(plan["plan_id"], plan_id)
        self.assertEqual((plan["start_date"], plan["end_date"]), (saved["start_date"], saved["end_date"]))

        start = date.fromisoformat(plan["start_date"])
        expected_dates = [start + timedelta(days=offset) for offset in range(3)]
        self.assertEqual([day["date"] for day in plan["days"]], [d.isoformat() for d in expected_dates])
        self.assertEqual([day["weekday"] for day in plan["days"]], [d.isoweekday() for d in expected_dates])
        self.assertEqual([day["workout_type"] for day in plan["days"]], ["Full Body", "Full Body", "Full Body"])

        for day, generated_day in zip(plan["days"], generated["weekly_workouts"]):
            self.assertEqual([exercise["exercise_name"] for exercise in day["exercises"]],
                             [exercise["name"] for exercise in generated_day["exercises"]])
            for exercise in day["exercises"]:
                self.assertEqual((exercise["sets_count"], exercise["repetitions_count"]), (3, 10))

    def test_latest_route_returns_the_most_recent_plan(self):
        client, user_id = self.signup("recent@example.com")
        self.generate(client, 3)
        seven_day = self.generate(client, 7)

        plan = self.latest_plan(client)
        first_id, second_id = self.plan_ids_for(user_id)
        self.assertEqual(plan["plan_id"], second_id)
        self.assertNotEqual(plan["plan_id"], first_id)
        self.assertEqual([day["workout_type"] for day in plan["days"]], seven_day["workout_plan"])

        # rest and recovery days are saved with their type and no exercises
        rest_days = [day for day in plan["days"] if day["workout_type"] in ("Rest", "Active Recovery")]
        self.assertEqual(len(rest_days), 3)
        for day in rest_days:
            self.assertEqual(day["exercises"], [])

    def test_no_plan_returns_404_and_no_session_returns_401(self):
        client, _ = self.signup("empty@example.com")
        response = client.get(LATEST_PLAN_URL)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.get_json(), {"error": "No workout plan found. Build a plan first."})

        response = self.app.test_client().get(LATEST_PLAN_URL)
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.get_json(), {"error": "You must be logged in to view your schedule"})

    def test_users_only_see_their_own_plan(self):
        client_a, user_a = self.signup("user.a@example.com")
        client_b, user_b = self.signup("user.b@example.com")
        self.generate(client_a, 3)

        # B has no plan yet and must not receive A's plan
        response = client_b.get(LATEST_PLAN_URL)
        self.assertEqual(response.status_code, 404)

        self.generate(client_b, 5)
        [plan_a] = self.plan_ids_for(user_a)
        [plan_b] = self.plan_ids_for(user_b)
        self.assertEqual(self.latest_plan(client_a)["plan_id"], plan_a)
        self.assertEqual(self.latest_plan(client_b)["plan_id"], plan_b)
        self.assertEqual(len(self.latest_plan(client_a)["days"]), 3)
        self.assertEqual(len(self.latest_plan(client_b)["days"]), 5)

    def test_older_plan_without_types_and_non_monday_start(self):
        client, user_id = self.signup("older@example.com")
        with connect(self.db_path) as conn:
            plan_id = conn.execute(
                "INSERT INTO workout_plans (user_id, start_date, end_date) VALUES (?, '2026-11-18', '2026-11-24')",
                (user_id,),
            ).lastrowid  # 2026-11-18 is a Wednesday
            monday = conn.execute(
                "INSERT INTO workout_days (plan_id, weekday) VALUES (?, 1)", (plan_id,)).lastrowid
            friday = conn.execute(
                "INSERT INTO workout_days (plan_id, weekday) VALUES (?, 5)", (plan_id,)).lastrowid

        plan = self.latest_plan(client)
        self.assertEqual(plan["plan_id"], plan_id)
        # in date order: Friday 20th comes before the following Monday 23rd
        self.assertEqual([(day["workout_day_id"], day["date"]) for day in plan["days"]],
                         [(friday, "2026-11-20"), (monday, "2026-11-23")])
        self.assertEqual([day["workout_type"] for day in plan["days"]], [None, None])


if __name__ == "__main__":
    unittest.main()
