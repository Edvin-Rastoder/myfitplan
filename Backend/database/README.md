# myfitplan database

The project uses SQLite with Python’s built-in `sqlite3` module

- `schema.sql` defines the tables
- `db.py` creates the database and manages connections
- `demo.py` is a current sample run to check that the db is working with sample data

## Set up the database

From the repository root, run:

```sh
python3 Backend/database/db.py init
```

This creates `Backend/database/myfitplan.db`. The database file is ignored by Git. Running the command again will not erase existing data.

To use a different location, pass `--db-path`:

```sh
python3 Backend/database/db.py init --db-path /path/to/myfitplan.db
```

You can also set `MYFITPLAN_DB_PATH`. If you use both, `--db-path` takes priority.

## Connect from Python

When running Python from the `Backend/` folder:

```python
from database.db import connect

with connect() as conn:
    goals = conn.execute("SELECT * FROM fitness_goals").fetchall()
```

`connect()` enables foreign keys, saves successful changes, rolls back changes if an error occurs, and closes the connection afterward.

## Check the database

From the repository root, run:

```sh
python3 Backend/database/demo.py
```

The demo uses `db.init_db()` and `db.connect()` on a temporary SQLite file. It saves one placeholder user, one fitness goal, one available weekday, a plan with one scheduled day and one prescribed exercise, and one completed workout with one logged set. It then reads them back on a new connection, checks the key values and that the records are linked correctly, and confirms that a workout day pointing at a plan that doesn't exist is rejected by a foreign key. The temporary file is deleted when it finishes.

This checks SQLite and `db.py` only. It does not test the Flask app.

If you run it from another folder, use the absolute path to `demo.py`. A successful run prints `All checks passed.`. A failed check prints `FAIL:` with the expected and actual values and exits with code 1.