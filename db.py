"""SQLite storage for foods, the meal log, the meal plan and per-profile targets.

All nutrient values on a food are stored per 100 g. Entries store a gram amount,
and nutrients are computed in SQL when entries are read.
"""
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path(os.environ.get("NUTRITION_DB", "nutrition.db"))

# Tables that share the same shape (a dated list of foods with gram amounts).
ENTRY_TABLES = {"log", "plan"}

NUTRIENTS = ["kcal", "protein", "carbs", "fat", "fiber", "sugar", "sodium_mg"]

# Placeholder starting points only. Each person should set their own targets.
DEFAULT_TARGETS = {"kcal": 2000.0, "protein": 100.0, "carbs": 250.0, "fat": 70.0}

SCHEMA = """
CREATE TABLE IF NOT EXISTS foods (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    brand TEXT NOT NULL DEFAULT '',
    barcode TEXT,
    kcal REAL NOT NULL DEFAULT 0,
    protein REAL NOT NULL DEFAULT 0,
    carbs REAL NOT NULL DEFAULT 0,
    fat REAL NOT NULL DEFAULT 0,
    fiber REAL NOT NULL DEFAULT 0,
    sugar REAL NOT NULL DEFAULT 0,
    sodium_mg REAL NOT NULL DEFAULT 0,
    source TEXT NOT NULL DEFAULT 'custom',
    UNIQUE(name, brand)
);

CREATE TABLE IF NOT EXISTS log (
    id INTEGER PRIMARY KEY,
    profile TEXT NOT NULL,
    day TEXT NOT NULL,
    meal TEXT NOT NULL,
    food_id INTEGER NOT NULL REFERENCES foods(id),
    grams REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS plan (
    id INTEGER PRIMARY KEY,
    profile TEXT NOT NULL,
    day TEXT NOT NULL,
    meal TEXT NOT NULL,
    food_id INTEGER NOT NULL REFERENCES foods(id),
    grams REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS targets (
    profile TEXT NOT NULL,
    nutrient TEXT NOT NULL,
    value REAL NOT NULL,
    PRIMARY KEY (profile, nutrient)
);

CREATE INDEX IF NOT EXISTS idx_log_day ON log(profile, day);
CREATE INDEX IF NOT EXISTS idx_plan_day ON plan(profile, day);
"""


@contextmanager
def connect():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys = ON")
    try:
        yield c
        c.commit()
    finally:
        c.close()


def init():
    with connect() as c:
        c.executescript(SCHEMA)


# ---------- foods ----------

def upsert_food(name, brand="", kcal=0, protein=0, carbs=0, fat=0, fiber=0,
                sugar=0, sodium_mg=0, barcode=None, source="custom"):
    """Insert a food (values per 100 g), or update it if name+brand already exist."""
    name, brand = name.strip(), (brand or "").strip()
    if not name:
        raise ValueError("A food needs a name.")
    with connect() as c:
        c.execute(
            """INSERT INTO foods (name, brand, barcode, kcal, protein, carbs, fat,
                                  fiber, sugar, sodium_mg, source)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(name, brand) DO UPDATE SET
                 barcode=excluded.barcode, kcal=excluded.kcal,
                 protein=excluded.protein, carbs=excluded.carbs, fat=excluded.fat,
                 fiber=excluded.fiber, sugar=excluded.sugar,
                 sodium_mg=excluded.sodium_mg, source=excluded.source""",
            (name, brand, barcode, kcal, protein, carbs, fat, fiber, sugar,
             sodium_mg, source),
        )
        row = c.execute("SELECT id FROM foods WHERE name=? AND brand=?",
                        (name, brand)).fetchone()
        return row["id"]


def list_foods(query=""):
    with connect() as c:
        rows = c.execute(
            "SELECT * FROM foods WHERE name LIKE ? OR brand LIKE ? ORDER BY name",
            (f"%{query}%", f"%{query}%"),
        ).fetchall()
    return [dict(r) for r in rows]


def delete_food(food_id):
    """Delete a food. Returns False if it is still used by a log or plan entry."""
    with connect() as c:
        used = c.execute(
            "SELECT (SELECT COUNT(*) FROM log WHERE food_id=?) + "
            "(SELECT COUNT(*) FROM plan WHERE food_id=?) AS n",
            (food_id, food_id),
        ).fetchone()["n"]
        if used:
            return False
        c.execute("DELETE FROM foods WHERE id=?", (food_id,))
        return True


# ---------- log / plan entries ----------

def _check(table):
    if table not in ENTRY_TABLES:
        raise ValueError(f"Unknown table: {table}")


def add_entry(table, profile, day, meal, food_id, grams):
    _check(table)
    if grams <= 0:
        raise ValueError("Amount must be positive.")
    with connect() as c:
        c.execute(
            f"INSERT INTO {table} (profile, day, meal, food_id, grams) VALUES (?,?,?,?,?)",
            (profile, str(day), meal, food_id, grams),
        )


def delete_entry(table, profile, entry_id):
    _check(table)
    with connect() as c:
        c.execute(f"DELETE FROM {table} WHERE id=? AND profile=?", (entry_id, profile))


def entries(table, profile, day):
    """Entries for one day, with nutrients already scaled to the eaten amount."""
    _check(table)
    sql = f"""
        SELECT t.id, t.meal, f.name, f.brand, t.grams,
               f.kcal * t.grams / 100.0      AS kcal,
               f.protein * t.grams / 100.0   AS protein,
               f.carbs * t.grams / 100.0     AS carbs,
               f.fat * t.grams / 100.0       AS fat,
               f.fiber * t.grams / 100.0     AS fiber,
               f.sugar * t.grams / 100.0     AS sugar,
               f.sodium_mg * t.grams / 100.0 AS sodium_mg
        FROM {table} t JOIN foods f ON f.id = t.food_id
        WHERE t.profile = ? AND t.day = ?
        ORDER BY t.id
    """
    with connect() as c:
        return [dict(r) for r in c.execute(sql, (profile, str(day))).fetchall()]


def totals(rows):
    return {n: sum(r[n] for r in rows) for n in NUTRIENTS}


def daily_totals(table, profile, start, end):
    """One row per day with data between start and end (inclusive)."""
    _check(table)
    sql = f"""
        SELECT t.day,
               SUM(f.kcal * t.grams / 100.0)    AS kcal,
               SUM(f.protein * t.grams / 100.0) AS protein,
               SUM(f.carbs * t.grams / 100.0)   AS carbs,
               SUM(f.fat * t.grams / 100.0)     AS fat
        FROM {table} t JOIN foods f ON f.id = t.food_id
        WHERE t.profile = ? AND t.day BETWEEN ? AND ?
        GROUP BY t.day ORDER BY t.day
    """
    with connect() as c:
        return [dict(r) for r in c.execute(sql, (profile, str(start), str(end))).fetchall()]


def export_log(profile):
    with connect() as c:
        rows = c.execute(
            """SELECT t.day, t.meal, f.name, f.brand, t.grams,
                      ROUND(f.kcal * t.grams / 100.0, 1)    AS kcal,
                      ROUND(f.protein * t.grams / 100.0, 1) AS protein,
                      ROUND(f.carbs * t.grams / 100.0, 1)   AS carbs,
                      ROUND(f.fat * t.grams / 100.0, 1)     AS fat
               FROM log t JOIN foods f ON f.id = t.food_id
               WHERE t.profile = ? ORDER BY t.day, t.id""",
            (profile,),
        ).fetchall()
    return [dict(r) for r in rows]


def copy_plan_to_log(profile, day):
    """Copy a day's planned items into the log. Returns how many were copied."""
    with connect() as c:
        cur = c.execute(
            """INSERT INTO log (profile, day, meal, food_id, grams)
               SELECT profile, day, meal, food_id, grams FROM plan
               WHERE profile = ? AND day = ?""",
            (profile, str(day)),
        )
        return cur.rowcount


# ---------- targets ----------

def get_targets(profile):
    targets = dict(DEFAULT_TARGETS)
    with connect() as c:
        for r in c.execute("SELECT nutrient, value FROM targets WHERE profile=?", (profile,)):
            targets[r["nutrient"]] = r["value"]
    return targets


def set_targets(profile, values):
    with connect() as c:
        for nutrient, value in values.items():
            c.execute(
                """INSERT INTO targets (profile, nutrient, value) VALUES (?,?,?)
                   ON CONFLICT(profile, nutrient) DO UPDATE SET value=excluded.value""",
                (profile, nutrient, float(value)),
            )
