# Tests for saving a generated plan and reading it back through GET /workout-plans/latest.
# Uses a temporary SQLite file, never the repo's myfitplan.db.

import contextlib
import io
import os
import sys
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # Backend/

from database.db import DB_PATH_ENV_VAR, connect, init_db


class SavedScheduleTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        temp_dir = tempfile.TemporaryDirectory()
        cls.addClassCleanup(temp_dir.cleanup)
        cls.db_path = Path(temp_dir.name) / "test.db"

        # point the app at the temporary database before importing it
        env = patch.dict(os.environ, {DB_PATH_ENV_VAR: str(cls.db_path)})
        env.start()
        cls.addClassCleanup(env.stop)

        init_db(cls.db_path)
        with contextlib.redirect_stdout(io.StringIO()):  # app.py prints debug lines
            from app import app
        cls.app = app

    # helpers

    def signup(self, email):
        client = self.app.test_client()
        response = client.post("/create-user", json={"email": email, "password_hash": "test-password"})
        self.assertEqual(response.status_code, 201)
        return client, response.get_json()["user_id"]

    def generate(self, client, days):
        request = {"goal": "muscle_gain", "experience": "beginner", "days": days, "duration": 30}
        with contextlib.redirect_stdout(io.StringIO()):
            response = client.post("/generate-workout", json=request)
        self.assertEqual(response.status_code, 200)
        return response.get_json()

    def latest_plan(self, client):
        response = client.get("/workout-plans/latest")
        self.assertEqual(response.status_code, 200)
        return response.get_json()

    # tests

    def test_generated_plan_is_saved_and_read_back(self):
        client, _ = self.signup("reader@example.com")
        generated = self.generate(client, 3)
        plan = self.latest_plan(client)

        # three consecutive days from the start date, each saved as "Full Body"
        start = date.fromisoformat(plan["start_date"])
        self.assertEqual(
            [(day["date"], day["workout_type"]) for day in plan["days"]],
            [((start + timedelta(days=offset)).isoformat(), "Full Body") for offset in range(3)],
        )

        # each day's saved exercises match what the generator returned
        for day, generated_day in zip(plan["days"], generated["weekly_workouts"]):
            self.assertEqual(
                [(exercise["exercise_name"], exercise["sets_count"], exercise["repetitions_count"]) for exercise in day["exercises"]],
                [(exercise["name"], 3, 10) for exercise in generated_day["exercises"]],
            )

    def test_latest_route_returns_the_most_recent_plan(self):
        client, _ = self.signup("recent@example.com")
        self.generate(client, 3)
        self.assertEqual(len(self.latest_plan(client)["days"]), 3)
        seven_day = self.generate(client, 7)

        # the newer 7-day plan replaces the 3-day plan; rest and recovery days have no exercises
        plan = self.latest_plan(client)
        self.assertEqual(
            [(day["workout_type"], day["exercises"] == []) for day in plan["days"]],
            [(workout_type, workout_type in ("Rest", "Active Recovery")) for workout_type in seven_day["workout_plan"]],
        )

    def test_no_plan_returns_404_and_no_session_returns_401(self):
        client, _ = self.signup("empty@example.com")
        response = client.get("/workout-plans/latest")
        self.assertEqual((response.status_code, response.get_json()),
                         (404, {"error": "No workout plan found. Build a plan first."}))

        response = self.app.test_client().get("/workout-plans/latest")
        self.assertEqual((response.status_code, response.get_json()),
                         (401, {"error": "You must be logged in to view your schedule"}))

    def test_users_only_see_their_own_plan(self):
        client_a, _ = self.signup("user.a@example.com")
        client_b, _ = self.signup("user.b@example.com")
        self.generate(client_a, 3)

        # B has no plan yet and must not receive A's plan
        self.assertEqual(client_b.get("/workout-plans/latest").status_code, 404)

        # after B builds a 5-day plan, each user still gets only their own
        self.generate(client_b, 5)
        plan_a = self.latest_plan(client_a)
        plan_b = self.latest_plan(client_b)
        self.assertNotEqual(plan_a["plan_id"], plan_b["plan_id"])
        self.assertEqual((len(plan_a["days"]), len(plan_b["days"])), (3, 5))

    def test_older_plan_without_types_and_non_monday_start(self):
        client, user_id = self.signup("older@example.com")
        with connect(self.db_path) as conn:
            plan_id = conn.execute(  # 2026-11-18 is a Wednesday
                "INSERT INTO workout_plans (user_id, start_date, end_date) VALUES (?, '2026-11-18', '2026-11-24')",
                (user_id,),
            ).lastrowid
            conn.execute("INSERT INTO workout_days (plan_id, weekday) VALUES (?, 1)", (plan_id,))  # Monday
            conn.execute("INSERT INTO workout_days (plan_id, weekday) VALUES (?, 5)", (plan_id,))  # Friday

        # in date order, with no recorded workout type
        plan = self.latest_plan(client)
        self.assertEqual(plan["plan_id"], plan_id)
        self.assertEqual(
            [(day["date"], day["workout_type"]) for day in plan["days"]],
            [("2026-11-20", None), ("2026-11-23", None)],
        )


if __name__ == "__main__":
    unittest.main()
