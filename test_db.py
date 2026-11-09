import importlib

import pytest


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setenv("NUTRITION_DB", str(tmp_path / "test.db"))
    import db as db_module
    db_module = importlib.reload(db_module)
    db_module.init()
    return db_module


def test_entry_scales_nutrients_by_grams(db):
    oats = db.upsert_food("Oats", kcal=370, protein=13, carbs=60, fat=7, fiber=10)
    db.add_entry("log", "me", "2026-10-29", "Breakfast", oats, 50)
    rows = db.entries("log", "me", "2026-10-29")
    assert len(rows) == 1
    assert rows[0]["kcal"] == pytest.approx(185)
    assert rows[0]["protein"] == pytest.approx(6.5)
    assert db.totals(rows)["fiber"] == pytest.approx(5)


def test_upsert_updates_existing_food(db):
    a = db.upsert_food("Milk", "Brand", kcal=40)
    b = db.upsert_food("Milk", "Brand", kcal=45)
    assert a == b
    assert db.list_foods("Milk")[0]["kcal"] == 45


def test_profiles_are_separate(db):
    f = db.upsert_food("Apple", kcal=52)
    db.add_entry("log", "alice", "2026-10-29", "Snack", f, 100)
    assert db.entries("log", "bob", "2026-10-29") == []
    assert len(db.entries("log", "alice", "2026-10-29")) == 1


def test_delete_entry_only_for_owner(db):
    f = db.upsert_food("Apple", kcal=52)
    db.add_entry("log", "alice", "2026-10-29", "Snack", f, 100)
    entry_id = db.entries("log", "alice", "2026-10-29")[0]["id"]
    db.delete_entry("log", "bob", entry_id)
    assert len(db.entries("log", "alice", "2026-10-29")) == 1
    db.delete_entry("log", "alice", entry_id)
    assert db.entries("log", "alice", "2026-10-29") == []


def test_cannot_delete_food_in_use(db):
    f = db.upsert_food("Apple", kcal=52)
    db.add_entry("plan", "me", "2026-10-29", "Snack", f, 100)
    assert db.delete_food(f) is False
    unused = db.upsert_food("Pear", kcal=57)
    assert db.delete_food(unused) is True


def test_copy_plan_to_log(db):
    f = db.upsert_food("Rice", kcal=130)
    db.add_entry("plan", "me", "2026-10-30", "Dinner", f, 200)
    assert db.copy_plan_to_log("me", "2026-10-30") == 1
    assert db.entries("log", "me", "2026-10-30")[0]["kcal"] == pytest.approx(260)


def test_daily_totals_and_targets(db):
    f = db.upsert_food("Rice", kcal=130, protein=2.7, carbs=28, fat=0.3)
    db.add_entry("log", "me", "2026-10-28", "Lunch", f, 100)
    db.add_entry("log", "me", "2026-10-29", "Lunch", f, 200)
    rows = db.daily_totals("log", "me", "2026-10-28", "2026-10-29")
    assert [r["day"] for r in rows] == ["2026-10-28", "2026-10-29"]
    assert rows[1]["kcal"] == pytest.approx(260)

    assert db.get_targets("me")["kcal"] == db.DEFAULT_TARGETS["kcal"]
    db.set_targets("me", {"kcal": 2300})
    assert db.get_targets("me")["kcal"] == 2300


def test_invalid_input(db):
    with pytest.raises(ValueError):
        db.upsert_food("  ")
    f = db.upsert_food("Apple", kcal=52)
    with pytest.raises(ValueError):
        db.add_entry("log", "me", "2026-10-29", "Snack", f, 0)
    with pytest.raises(ValueError):
        db.entries("foods; DROP TABLE foods", "me", "2026-10-29")


def test_parse_open_food_facts_product():
    import foods
    product = {
        "code": "123",
        "product_name": "Skyr",
        "brands": "Tine, Other",
        "nutriments": {"energy-kcal_100g": 63, "proteins_100g": 11,
                       "carbohydrates_100g": 4, "fat_100g": 0.2, "sodium_100g": 0.05},
    }
    f = foods.parse_product(product)
    assert f["brand"] == "Tine"
    assert f["sodium_mg"] == pytest.approx(50)
    assert foods.parse_product({"product_name": "No energy", "nutriments": {}}) is None
    assert foods.parse_product({"nutriments": {"energy-kcal_100g": 1}}) is None
