# Tests for the saved-plan schedule: workout types and dates in GET /my-workouts, and
# moving workouts with POST /update-schedule. Uses a temporary SQLite file, never the repo's myfitplan.db.

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


def weekday_after(start, offset):
    """ISO weekday (1 = Monday) of the date `offset` days after `start`."""
    return (start + timedelta(days=offset)).isoweekday()


class ScheduleTest(unittest.TestCase):
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

    def generate(self, client, goal="muscle_gain", days=3):
        request = {"goal": goal, "experience": "beginner", "days": days, "duration": 30}
        with contextlib.redirect_stdout(io.StringIO()):
            response = client.post("/generate-workout", json=request)
        self.assertEqual(response.status_code, 200)
        return response.get_json()

    def my_workouts(self, client):
        response = client.get("/my-workouts")
        self.assertEqual(response.status_code, 200)
        return response.get_json()

    def by_day_id(self, client):
        """The latest plan's days in generation order (workout_day_id)."""
        return sorted(self.my_workouts(client)["workouts"], key=lambda day: day["workout_day_id"])

    def update(self, client, weekdays):
        return client.post("/update-schedule", json={"weekdays": weekdays})

    # tests

    def test_my_workouts_includes_workout_types_and_dates(self):
        client, _ = self.signup("expanded@example.com")
        generated = self.generate(client)
        data = self.my_workouts(client)

        # existing fields are still there, and days are still ordered by weekday
        self.assertTrue({"plan_id", "start_date", "end_date", "duration_minutes", "workouts"} <= set(data))
        self.assertEqual(data["duration_minutes"], 30)
        weekdays = [day["weekday"] for day in data["workouts"]]
        self.assertEqual(weekdays, sorted(weekdays))

        # each day has its saved type and its real date within the plan, in generation order by date
        start = date.fromisoformat(data["start_date"])
        days = sorted(data["workouts"], key=lambda day: day["date"])
        self.assertEqual(
            [(day["date"], day["weekday"], day["workout_type"]) for day in days],
            [((start + timedelta(days=offset)).isoformat(), weekday_after(start, offset), "Full Body")
             for offset in range(3)],
        )
        self.assertTrue(all(day["date"] <= data["end_date"] for day in days))

        # exercises keep their IDs and match what the generator returned
        for day, generated_day in zip(days, generated["weekly_workouts"]):
            self.assertEqual(set(day), {"workout_day_id", "weekday", "date", "workout_type", "exercises"})
            self.assertTrue(all(isinstance(exercise["workout_exercise_id"], int) for exercise in day["exercises"]))
            self.assertEqual(
                [(exercise["exercise_name"], exercise["sets_count"], exercise["repetitions_count"]) for exercise in day["exercises"]],
                [(exercise["name"], 3, 10) for exercise in generated_day["exercises"]],
            )

        with connect(self.db_path) as conn:
            saved = conn.execute(
                "SELECT description FROM workout_days WHERE plan_id = ? ORDER BY workout_day_id", (data["plan_id"],)
            ).fetchall()
        self.assertEqual([row["description"] for row in saved], ["Full Body"] * 3)

    def test_users_only_see_and_change_their_own_plan(self):
        client_a, user_a = self.signup("user.a@example.com")
        client_b, user_b = self.signup("user.b@example.com")
        self.generate(client_a)

        # B has no plan yet and must not receive A's plan
        self.assertEqual(self.my_workouts(client_b), {"workouts": []})

        self.generate(client_b)
        plan_a = self.my_workouts(client_a)
        plan_b = self.my_workouts(client_b)
        with connect(self.db_path) as conn:
            owners = dict(conn.execute("SELECT plan_id, user_id FROM workout_plans").fetchall())
        self.assertEqual((owners[plan_a["plan_id"]], owners[plan_b["plan_id"]]), (user_a, user_b))

        # B moving their workouts leaves A's schedule alone
        b_weekdays = [day["weekday"] % 7 + 1 for day in plan_b["workouts"]]
        self.assertEqual(self.update(client_b, b_weekdays).status_code, 200)
        self.assertEqual(self.my_workouts(client_a), plan_a)

    def test_older_plan_without_types(self):
        client, user_id = self.signup("older@example.com")
        with connect(self.db_path) as conn:
            plan_id = conn.execute(  # 2026-11-18 is a Wednesday
                "INSERT INTO workout_plans (user_id, start_date, end_date) VALUES (?, '2026-11-18', '2026-11-24')",
                (user_id,),
            ).lastrowid
            monday = conn.execute("INSERT INTO workout_days (plan_id, weekday) VALUES (?, 1)", (plan_id,)).lastrowid
            conn.execute("INSERT INTO workout_days (plan_id, weekday) VALUES (?, 5)", (plan_id,))  # Friday
            conn.execute(
                "INSERT INTO workout_exercises (workout_day_id, exercise_name, sets_count, repetitions_count)"
                " VALUES (?, 'Push-up', 3, 10)", (monday,))

        data = self.my_workouts(client)
        self.assertEqual(data["plan_id"], plan_id)
        self.assertEqual(
            [(day["weekday"], day["date"], day["workout_type"], len(day["exercises"])) for day in data["workouts"]],
            [(1, "2026-11-23", None, 1), (5, "2026-11-20", None, 0)],
        )

    def test_update_schedule_moves_workouts_onto_overlapping_days(self):
        client, _ = self.signup("overlap@example.com")
        self.generate(client)
        before = self.by_day_id(client)
        start = date.fromisoformat(self.my_workouts(client)["start_date"])

        # move every workout one day later: two of the three new days are already taken
        new_weekdays = [weekday_after(start, offset) for offset in (1, 2, 3)]
        response = self.update(client, sorted(new_weekdays))
        self.assertEqual((response.status_code, response.get_json()), (200, {"message": "Schedule updated successfully"}))

        # the workouts keep their order and exercises; only their weekdays change
        after = self.by_day_id(client)
        self.assertEqual([day["weekday"] for day in after], new_weekdays)
        self.assertEqual([[e["workout_exercise_id"] for e in day["exercises"]] for day in after],
                         [[e["workout_exercise_id"] for e in day["exercises"]] for day in before])
        self.assertEqual([day["date"] for day in after],
                         [(start + timedelta(days=offset)).isoformat() for offset in (1, 2, 3)])

        # an invalid request changes nothing
        response = self.update(client, [1])
        self.assertEqual((response.status_code, response.get_json()),
                         (400, {"error": "Please select exactly 3 workout days"}))
        self.assertEqual(self.by_day_id(client), after)

    def test_failed_update_changes_nothing(self):
        client, _ = self.signup("atomic@example.com")
        self.generate(client)
        before = self.by_day_id(client)
        plan_id = self.my_workouts(client)["plan_id"]

        # make writing any new weekday for this plan fail, after the weekdays have been cleared
        with connect(self.db_path) as conn:
            conn.execute(f"""
                CREATE TRIGGER fail_schedule_write BEFORE UPDATE OF weekday ON workout_days
                WHEN NEW.plan_id = {plan_id} AND NEW.weekday IS NOT NULL
                BEGIN SELECT RAISE(ABORT, 'simulated failure'); END
            """)

        def drop_trigger():
            with connect(self.db_path) as conn:
                conn.execute("DROP TRIGGER fail_schedule_write")
        self.addCleanup(drop_trigger)

        new_weekdays = [day["weekday"] % 7 + 1 for day in before]
        with contextlib.redirect_stdout(io.StringIO()):  # the route prints the error
            response = self.update(client, new_weekdays)
        self.assertEqual((response.status_code, response.get_json()), (500, {"error": "Failed to update schedule"}))
        # the cleared weekdays were rolled back with the failed write
        self.assertEqual(self.by_day_id(client), before)

    def test_update_schedule_for_a_seven_day_plan(self):
        client, _ = self.signup("seven@example.com")
        generated = self.generate(client, goal="weight_loss", days=7)
        self.assertEqual(generated["workout_plan"],
                         ["Upper", "Cardio", "Lower", "Cardio", "Full Body", "Active Recovery", "Rest"])
        before = self.by_day_id(client)
        start = date.fromisoformat(self.my_workouts(client)["start_date"])

        # all 7 weekdays are taken; choose 5 workout days on different dates
        chosen = [weekday_after(start, offset) for offset in (0, 2, 3, 5, 6)]
        self.assertEqual(self.update(client, sorted(chosen)).status_code, 200)

        after = self.by_day_id(client)
        # workouts take the chosen days in program order; Active Recovery and Rest fill the free days
        self.assertEqual(
            [(day["workout_type"], day["weekday"]) for day in after],
            list(zip(generated["workout_plan"], chosen + [weekday_after(start, 1), weekday_after(start, 4)])),
        )
        self.assertEqual(sorted(day["weekday"] for day in after), [1, 2, 3, 4, 5, 6, 7])
        self.assertEqual([len(day["exercises"]) == 0 for day in after], [False] * 5 + [True, True])
        self.assertEqual([[e["workout_exercise_id"] for e in day["exercises"]] for day in after],
                         [[e["workout_exercise_id"] for e in day["exercises"]] for day in before])


if __name__ == "__main__":
    unittest.main()
