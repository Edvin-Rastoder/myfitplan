-- myfitplan SQLite schema
PRAGMA foreign_keys = ON;

BEGIN;
-- User
CREATE TABLE IF NOT EXISTS users (
    user_id  INTEGER PRIMARY KEY, --user ID
    email TEXT UNIQUE COLLATE NOCASE  -- nullable to allow phone-only signup
        CHECK (email IS NULL OR email LIKE '%_@_%'),
    phone TEXT UNIQUE
        CHECK (phone IS NULL OR (
            phone GLOB '+[1-9]*' AND substr(phone, 2) NOT GLOB '*[^0-9]*' AND length(phone) BETWEEN 8 AND 16)),

    password_hash TEXT NOT NULL -- password, stored hashed only
                           CHECK (length(password_hash) > 0),
    sms_reminders_enabled  INTEGER NOT NULL DEFAULT 0
        CHECK (sms_reminders_enabled IN (0, 1)),
    sms_consent_at TEXT  -- when SMS consent was given
        CHECK (strftime('%Y-%m-%dT%H:%M:%SZ', sms_consent_at) IS sms_consent_at),

        CHECK (email IS NOT NULL OR phone IS NOT NULL),
    -- SMS reminders need a phone number and recorded consent
        CHECK (sms_reminders_enabled = 0 OR (phone IS NOT NULL AND sms_consent_at IS NOT NULL))
);

-- FitnessGoal
CREATE TABLE IF NOT EXISTS fitness_goals (
    goal_id INTEGER PRIMARY KEY, -- goal ID
    name TEXT NOT NULL UNIQUE COLLATE NOCASE -- goal name
        CHECK (length(trim(name)) > 0),
    description  TEXT -- goal description
);

-- User.userGoals: a user may select many goals; a goal may be selected by many users
CREATE TABLE IF NOT EXISTS user_fitness_goals (
    user_id  INTEGER NOT NULL REFERENCES users (user_id) ON DELETE CASCADE,
    goal_id  INTEGER NOT NULL REFERENCES fitness_goals (goal_id) ON DELETE CASCADE,
    PRIMARY KEY (user_id, goal_id)
);

CREATE INDEX IF NOT EXISTS idx_user_fitness_goals_goal ON user_fitness_goals (goal_id);

-- Flexible scheduling
CREATE TABLE IF NOT EXISTS user_available_weekdays (
    user_id  INTEGER NOT NULL REFERENCES users (user_id) ON DELETE CASCADE,
    weekday  INTEGER NOT NULL CHECK (weekday BETWEEN 1 AND 7),
    PRIMARY KEY (user_id, weekday)
);

-- WorkoutPlan
CREATE TABLE IF NOT EXISTS workout_plans (
    plan_id INTEGER PRIMARY KEY, -- planId
    user_id INTEGER NOT NULL REFERENCES users (user_id) ON DELETE CASCADE,  -- owner
    start_date TEXT NOT NULL CHECK (date(start_date) IS start_date), -- startDate
    end_date TEXT NOT NULL CHECK (date(end_date) IS end_date), -- endDate
    CHECK (end_date >= start_date)
);

CREATE INDEX IF NOT EXISTS idx_workout_plans_user ON workout_plans (user_id);

-- WorkoutDay
-- WorkoutPlan.workoutDays: a plan contains workout days.
CREATE TABLE IF NOT EXISTS workout_days (
    workout_day_id  INTEGER PRIMARY KEY, -- workoutDayId
    plan_id  INTEGER NOT NULL REFERENCES workout_plans (plan_id) ON DELETE CASCADE,
    description TEXT, -- description
    complexity INTEGER CHECK (complexity >= 1), -- complexity
    goal_id INTEGER REFERENCES fitness_goals (goal_id) ON DELETE SET NULL, -- goal
    weekday INTEGER CHECK (weekday BETWEEN 1 AND 7), -- NULL = not yet placed
    UNIQUE (plan_id, weekday) -- at most one workout per weekday in a plan
);

CREATE INDEX IF NOT EXISTS idx_workout_days_goal ON workout_days (goal_id);

-- WorkoutExercise (prescribed)
CREATE TABLE IF NOT EXISTS workout_exercises (
    workout_exercise_id  INTEGER PRIMARY KEY,
    workout_day_id INTEGER NOT NULL REFERENCES workout_days (workout_day_id) ON DELETE CASCADE,
    exercise_name TEXT NOT NULL COLLATE NOCASE
        CHECK (length(trim(exercise_name)) > 0),
    sets_count INTEGER NOT NULL CHECK (sets_count >= 1),
    repetitions_count INTEGER NOT NULL CHECK (repetitions_count >= 1), --repetitions
    suggested_weight REAL CHECK (suggested_weight >= 0), -- suggestedWeight, lb;
    rest_time INTEGER CHECK (rest_time >= 0) -- restTime, seconds
);

CREATE INDEX IF NOT EXISTS idx_workout_exercises_day ON workout_exercises (workout_day_id);

-- Workout history
CREATE TABLE IF NOT EXISTS workout_logs (
    workout_log_id  INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users (user_id) ON DELETE CASCADE,
    workout_day_id  INTEGER REFERENCES workout_days (workout_day_id) ON DELETE SET NULL,
    completed_on TEXT NOT NULL CHECK (date(completed_on) IS completed_on)  -- user's local date
);

CREATE INDEX IF NOT EXISTS idx_workout_logs_user_date ON workout_logs (user_id, completed_on);
CREATE INDEX IF NOT EXISTS idx_workout_logs_day ON workout_logs (workout_day_id);

-- An exercise actually performed. exercise_name is copied at log time so history still identifies the exercise if the plan changes
CREATE TABLE IF NOT EXISTS exercise_logs (
    exercise_log_id INTEGER PRIMARY KEY,
    workout_log_id INTEGER NOT NULL REFERENCES workout_logs (workout_log_id) ON DELETE CASCADE,
    workout_exercise_id INTEGER REFERENCES workout_exercises (workout_exercise_id) ON DELETE SET NULL,
    exercise_name TEXT NOT NULL COLLATE NOCASE
        CHECK (length(trim(exercise_name)) > 0)
);

CREATE INDEX IF NOT EXISTS idx_exercise_logs_workout ON exercise_logs (workout_log_id);
CREATE INDEX IF NOT EXISTS idx_exercise_logs_prescribed ON exercise_logs (workout_exercise_id);
CREATE INDEX IF NOT EXISTS idx_exercise_logs_name ON exercise_logs (exercise_name);

-- Actual sets: repetitions and weight per set
CREATE TABLE IF NOT EXISTS set_logs (
    set_log_id INTEGER PRIMARY KEY,
    exercise_log_id  INTEGER NOT NULL REFERENCES exercise_logs (exercise_log_id) ON DELETE CASCADE,
    set_number INTEGER NOT NULL CHECK (set_number >= 1),
    repetitions INTEGER NOT NULL CHECK (repetitions >= 0),
    weight REAL CHECK (weight >= 0),  -- lb; NULL = no weight recorded
    UNIQUE (exercise_log_id, set_number)
);

COMMIT;
