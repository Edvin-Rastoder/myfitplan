# Tests for recording a completed workout with POST /complete-workout and reading it
# back through GET /workout-history. Uses a temporary SQLite file, never the repo's myfitplan.db.

import contextlib
import io
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # Backend/

from database.db import DB_PATH_ENV_VAR, init_db


class WorkoutHistoryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        temp_dir = tempfile.TemporaryDirectory()
        cls.addClassCleanup(temp_dir.cleanup)
        db_path = Path(temp_dir.name) / "test.db"

        # point the app at the temporary database before importing it
        env = patch.dict(os.environ, {DB_PATH_ENV_VAR: str(db_path)})
        env.start()
        cls.addClassCleanup(env.stop)

        init_db(db_path)
        with contextlib.redirect_stdout(io.StringIO()):  # app.py prints debug lines
            from app import app
        cls.app = app

    # helpers

    def signup(self, email):
        client = self.app.test_client()
        response = client.post("/create-user", json={"email": email, "password_hash": "test-password"})
        self.assertEqual(response.status_code, 201)
        return client

    def first_workout(self, client):
        """Generate a plan and return its first workout day with exercises, from /my-workouts."""
        request = {"goal": "muscle_gain", "experience": "beginner", "days": 3, "duration": 30}
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(client.post("/generate-workout", json=request).status_code, 200)
        response = client.get("/my-workouts")
        self.assertEqual(response.status_code, 200)
        return next(day for day in response.get_json()["workouts"] if day["exercises"])

    def history(self, client):
        response = client.get("/workout-history")
        self.assertEqual(response.status_code, 200)
        return response.get_json()["history"]

    # tests

    def test_completed_workout_is_read_back_in_history(self):
        client = self.signup("logger@example.com")
        workout = self.first_workout(client)
        exercises = workout["exercises"][:2]
        sets = [
            {"set_number": 1, "repetitions": 10, "weight": 95.5},
            {"set_number": 2, "repetitions": 8, "weight": None},
        ]

        response = client.post("/complete-workout", json={
            "workout_day_id": workout["workout_day_id"],
            "duration_seconds": 1800,
            "exercises": [{"workout_exercise_id": e["workout_exercise_id"], "sets": sets} for e in exercises],
        })
        self.assertEqual(response.status_code, 201, response.get_json())
        workout_log_id = response.get_json()["workout_log_id"]

        [entry] = self.history(client)
        self.assertEqual(
            (entry["workout_log_id"], entry["workout_day_id"], entry["duration_seconds"]),
            (workout_log_id, workout["workout_day_id"], 1800),
        )
        self.assertEqual(
            entry["exercises"],
            [{"exercise_name": e["exercise_name"], "sets": sets} for e in exercises],
        )
        # 2 exercises x 2 sets; only the weighted sets count: 2 x (10 reps x 95.5 lb)
        self.assertEqual((entry["total_sets"], entry["total_weight"]), (4, 1910.0))

    def test_users_cannot_complete_someone_elses_workout(self):
        owner = self.signup("owner@example.com")
        owner_workout = self.first_workout(owner)
        other = self.signup("other@example.com")
        exercise_id = owner_workout["exercises"][0]["workout_exercise_id"]
        one_set = [{"set_number": 1, "repetitions": 5, "weight": 50}]

        # another user's workout day is not found for this user
        response = other.post("/complete-workout", json={
            "workout_day_id": owner_workout["workout_day_id"],
            "duration_seconds": 600,
            "exercises": [{"workout_exercise_id": exercise_id, "sets": one_set}],
        })
        self.assertEqual((response.status_code, response.get_json()), (404, {"error": "Workout not found"}))

        # another user's exercise cannot be logged against their own workout day
        other_workout = self.first_workout(other)
        response = other.post("/complete-workout", json={
            "workout_day_id": other_workout["workout_day_id"],
            "duration_seconds": 600,
            "exercises": [{"workout_exercise_id": exercise_id, "sets": one_set}],
        })
        self.assertEqual((response.status_code, response.get_json()),
                         (400, {"error": "Exercise does not belong to this workout"}))

        self.assertEqual(self.history(other), [])
        self.assertEqual(self.history(owner), [])

    def test_routes_require_a_session(self):
        anonymous = self.app.test_client()
        self.assertEqual(anonymous.post("/complete-workout", json={}).status_code, 401)
        self.assertEqual(anonymous.get("/workout-history").status_code, 401)


if __name__ == "__main__":
    unittest.main()
