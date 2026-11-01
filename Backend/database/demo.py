# Small check that schema.sql and db.py work together, using a temporary SQLite file.
# Run from the repository root: python3 Backend/database/demo.py

import sqlite3
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True  # importing db must not leave __pycache__/ in the repo
import db  # noqa: E402


class DemoCheckFailed(Exception):
    pass


def check_equal(label, actual, expected):
    if actual != expected:
        raise DemoCheckFailed(f"{label}: expected {expected!r}, got {actual!r}")


def run(path):
    db.init_db(path)

    # Save one sample of each record.
    with db.connect(path) as conn:
        user_id = conn.execute(
            "INSERT INTO users (email, password_hash) VALUES ('demo.user@example.com', 'placeholder-hash')"
        ).lastrowid
        goal_id = conn.execute("INSERT INTO fitness_goals (name) VALUES ('Strength')").lastrowid
        conn.execute("INSERT INTO user_fitness_goals (user_id, goal_id) VALUES (?, ?)", (user_id, goal_id))
        conn.execute("INSERT INTO user_available_weekdays (user_id, weekday) VALUES (?, 2)", (user_id,))  # Tuesday

        plan_id = conn.execute(
            "INSERT INTO workout_plans (user_id, start_date, end_date) VALUES (?, '2026-11-02', '2026-12-27')",
            (user_id,),
        ).lastrowid
        day_id = conn.execute(
            "INSERT INTO workout_days (plan_id, goal_id, weekday) VALUES (?, ?, 2)", (plan_id, goal_id)
        ).lastrowid
        exercise_id = conn.execute(
            "INSERT INTO workout_exercises (workout_day_id, exercise_name, sets_count, repetitions_count,"
            " suggested_weight) VALUES (?, 'Bench Press', 3, 8, 95)",  # weight in lb
            (day_id,),
        ).lastrowid

        log_id = conn.execute(
            "INSERT INTO workout_logs (user_id, workout_day_id, completed_on) VALUES (?, ?, '2026-11-03')",
            (user_id, day_id),
        ).lastrowid
        exercise_log_id = conn.execute(
            "INSERT INTO exercise_logs (workout_log_id, workout_exercise_id, exercise_name)"
            " VALUES (?, ?, 'Bench Press')",
            (log_id, exercise_id),
        ).lastrowid
        conn.execute(
            "INSERT INTO set_logs (exercise_log_id, set_number, repetitions, weight) VALUES (?, 1, 6, 95)",
            (exercise_log_id,),
        )

    # Read it back on a new connection. Each JOIN follows one link, so a broken
    # link returns no row at all.
    with db.connect(path) as conn:
        rows = conn.execute(
            """
            SELECT u.email, g.name AS goal, a.weekday AS available_weekday,
                   p.start_date, p.end_date, d.weekday AS planned_weekday,
                   e.exercise_name, e.sets_count, e.repetitions_count, e.suggested_weight,
                   l.completed_on, s.set_number, s.repetitions, s.weight
            FROM users u
            JOIN user_fitness_goals ug ON ug.user_id = u.user_id
            JOIN fitness_goals g ON g.goal_id = ug.goal_id
            JOIN user_available_weekdays a ON a.user_id = u.user_id
            JOIN workout_plans p ON p.user_id = u.user_id
            JOIN workout_days d ON d.plan_id = p.plan_id AND d.goal_id = g.goal_id
            JOIN workout_exercises e ON e.workout_day_id = d.workout_day_id
            JOIN workout_logs l ON l.workout_day_id = d.workout_day_id AND l.user_id = u.user_id
            JOIN exercise_logs el ON el.workout_log_id = l.workout_log_id
                                 AND el.workout_exercise_id = e.workout_exercise_id
            JOIN set_logs s ON s.exercise_log_id = el.exercise_log_id
            """
        ).fetchall()
    check_equal("rows linking user, plan and workout history (0 means a link is broken)", len(rows), 1)
    expected = {
        "email": "demo.user@example.com",
        "goal": "Strength",
        "available_weekday": 2,
        "start_date": "2026-11-02",
        "end_date": "2026-12-27",
        "planned_weekday": 2,
        "exercise_name": "Bench Press",
        "sets_count": 3,
        "repetitions_count": 8,
        "suggested_weight": 95.0,
        "completed_on": "2026-11-03",
        "set_number": 1,
        "repetitions": 6,
        "weight": 95.0,
    }
    for column, value in expected.items():
        check_equal(column, rows[0][column], value)

    # A workout day that points at a plan that doesn't exist must be rejected.
    with db.connect(path) as conn:
        try:
            conn.execute("INSERT INTO workout_days (plan_id) VALUES (999)")
        except sqlite3.IntegrityError as error:
            check_equal("error for a workout day with a missing plan", str(error), "FOREIGN KEY constraint failed")
        else:
            raise DemoCheckFailed("a workout day with plan_id 999 was accepted, but that plan doesn't exist")


def main():
    # The temporary folder and database are deleted automatically, even if a check fails.
    with tempfile.TemporaryDirectory(prefix="myfitplan-demo-") as temp_dir:
        try:
            run(Path(temp_dir) / "demo.db")
        except DemoCheckFailed as failure:
            print(f"FAIL: {failure}", file=sys.stderr)
            return 1
    print("All checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
