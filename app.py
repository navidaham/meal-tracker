import datetime as dt

import pandas as pd
import streamlit as st

import db
import foods

st.set_page_config(page_title="Meal Tracker", page_icon="🥗", layout="wide")
db.init()

MEALS = ["Breakfast", "Lunch", "Dinner", "Snack"]
MACROS = [("kcal", "Calories", "kcal"), ("protein", "Protein", "g"),
          ("carbs", "Carbs", "g"), ("fat", "Fat", "g")]


def food_label(f):
    return f["name"] + (f" ({f['brand']})" if f["brand"] else "")


# ---------- sidebar: profile, date, targets ----------

with st.sidebar:
    st.title("🥗 Meal Tracker")
    profile = st.text_input("Profile name", value="me", help="Log and plan are kept separately per profile.").strip() or "me"
    day = st.date_input("Date", value=dt.date.today())

    st.subheader("Daily targets")
    st.caption("Set these to whatever fits you. The defaults are just placeholders.")
    current = db.get_targets(profile)
    with st.form("targets"):
        new_targets = {
            key: st.number_input(f"{label} ({unit})", min_value=0.0, value=float(current[key]), step=10.0)
            for key, label, unit in MACROS
        }
        if st.form_submit_button("Save targets"):
            db.set_targets(profile, new_targets)
            st.rerun()
    targets = db.get_targets(profile)


# ---------- shared widgets ----------

def entry_form(table, key):
    saved = {f["id"]: f for f in db.list_foods()}
    if not saved:
        st.info("No foods yet. Add some in the **Foods** tab first.")
        return
    with st.form(f"{key}_form", clear_on_submit=True):
        c1, c2, c3 = st.columns([3, 2, 2])
        food_id = c1.selectbox("Food", list(saved), format_func=lambda i: food_label(saved[i]))
        meal = c2.selectbox("Meal", MEALS)
        grams = c3.number_input("Amount (g)", min_value=1.0, value=100.0, step=10.0)
        if st.form_submit_button("Add"):
            db.add_entry(table, profile, day, meal, food_id, grams)
            st.rerun()


def show_totals(rows, with_progress=True):
    totals = db.totals(rows)
    cols = st.columns(len(MACROS))
    for col, (key, label, unit) in zip(cols, MACROS):
        target = targets.get(key, 0)
        col.metric(label, f"{totals[key]:.0f} {unit}", f"of {target:.0f} {unit}", delta_color="off")
        if with_progress and target > 0:
            col.progress(min(totals[key] / target, 1.0))
    with st.expander("More nutrients"):
        st.write(
            f"Fiber **{totals['fiber']:.1f} g** · Sugar **{totals['sugar']:.1f} g** · "
            f"Sodium **{totals['sodium_mg']:.0f} mg**"
        )


def show_entries(table, rows):
    if not rows:
        st.caption("Nothing here yet.")
        return
    for meal in MEALS:
        meal_rows = [r for r in rows if r["meal"] == meal]
        if not meal_rows:
            continue
        st.markdown(f"**{meal}** · {sum(r['kcal'] for r in meal_rows):.0f} kcal")
        for r in meal_rows:
            c1, c2, c3, c4 = st.columns([4, 1.5, 2.5, 0.8])
            c1.write(food_label(r))
            c2.write(f"{r['grams']:.0f} g")
            c3.write(f"{r['kcal']:.0f} kcal · P {r['protein']:.0f} · C {r['carbs']:.0f} · F {r['fat']:.0f}")
            if c4.button("✕", key=f"del_{table}_{r['id']}", help="Remove"):
                db.delete_entry(table, profile, r["id"])
                st.rerun()


# ---------- tabs ----------

tab_log, tab_plan, tab_foods, tab_history = st.tabs(["📒 Log", "🗓️ Plan", "🍎 Foods", "📈 History"])

with tab_log:
    st.subheader(f"Eaten on {day:%A %d %B}")
    log_rows = db.entries("log", profile, day)
    show_totals(log_rows)
    st.divider()
    entry_form("log", "log")
    show_entries("log", log_rows)

with tab_plan:
    st.subheader(f"Planned for {day:%A %d %B}")
    plan_rows = db.entries("plan", profile, day)
    show_totals(plan_rows)
    st.divider()
    entry_form("plan", "plan")
    show_entries("plan", plan_rows)
    if plan_rows and st.button("Copy this plan into the log"):
        n = db.copy_plan_to_log(profile, day)
        st.success(f"Copied {n} items to the log for {day}.")

with tab_foods:
    st.subheader("Search Open Food Facts")
    with st.form("search_form"):
        q = st.text_input("Search for a food or product", placeholder="e.g. oats, skyr, tine melk")
        searched = st.form_submit_button("Search")
    if searched:
        with st.spinner("Searching..."):
            results, error = foods.search(q)
        st.session_state["results"] = results
        st.session_state["search_error"] = error
        st.session_state["search_q"] = q

    if st.session_state.get("search_error"):
        st.warning(st.session_state["search_error"])
    elif "results" in st.session_state and not st.session_state["results"]:
        st.info("No usable results (products need at least calories listed).")

    for i, f in enumerate(st.session_state.get("results", [])):
        c1, c2, c3 = st.columns([4, 4, 1.2])
        c1.write(food_label(f))
        c2.caption(f"per 100 g: {f['kcal']:.0f} kcal · P {f['protein']:.1f} · C {f['carbs']:.1f} · F {f['fat']:.1f}")
        if c3.button("Save", key=f"save_{i}_{f['barcode']}"):
            db.upsert_food(**f)
            st.toast(f"Saved {f['name']}")

    st.divider()
    st.subheader("Add a custom food")
    st.caption("Values per 100 g (check the nutrition label).")
    with st.form("custom_food", clear_on_submit=True):
        c1, c2 = st.columns(2)
        name = c1.text_input("Name")
        brand = c2.text_input("Brand (optional)")
        a, b, c, d = st.columns(4)
        kcal = a.number_input("kcal", min_value=0.0, step=1.0)
        protein = b.number_input("Protein (g)", min_value=0.0, step=0.1)
        carbs = c.number_input("Carbs (g)", min_value=0.0, step=0.1)
        fat = d.number_input("Fat (g)", min_value=0.0, step=0.1)
        e, f_, g = st.columns(3)
        fiber = e.number_input("Fiber (g)", min_value=0.0, step=0.1)
        sugar = f_.number_input("Sugar (g)", min_value=0.0, step=0.1)
        sodium = g.number_input("Sodium (mg)", min_value=0.0, step=10.0)
        if st.form_submit_button("Save food"):
            if not name.strip():
                st.error("Give the food a name.")
            else:
                db.upsert_food(name, brand, kcal, protein, carbs, fat, fiber, sugar, sodium)
                st.toast(f"Saved {name}")
                st.rerun()

    st.divider()
    st.subheader("Your saved foods")
    saved_foods = db.list_foods()
    if not saved_foods:
        st.caption("Nothing saved yet.")
    for f in saved_foods:
        c1, c2, c3 = st.columns([4, 4, 1.2])
        c1.write(food_label(f))
        c2.caption(f"per 100 g: {f['kcal']:.0f} kcal · P {f['protein']:.1f} · C {f['carbs']:.1f} · F {f['fat']:.1f}")
        if c3.button("Delete", key=f"delfood_{f['id']}"):
            if db.delete_food(f["id"]):
                st.rerun()
            else:
                st.warning("That food is used in your log or plan, so it can't be deleted.")

with tab_history:
    st.subheader("History")
    days_back = st.select_slider("Range", options=[7, 14, 30, 90], value=14, format_func=lambda n: f"Last {n} days")
    end = dt.date.today()
    start = end - dt.timedelta(days=days_back - 1)
    rows = db.daily_totals("log", profile, start, end)
    if not rows:
        st.info("Nothing logged in this range yet.")
    else:
        df = pd.DataFrame(rows)
        df["day"] = pd.to_datetime(df["day"])
        df = df.set_index("day").reindex(pd.date_range(start, end)).fillna(0)
        st.caption("Calories per day")
        st.bar_chart(df[["kcal"]])
        st.caption("Macros per day (g)")
        st.line_chart(df[["protein", "carbs", "fat"]])
        logged = df[df["kcal"] > 0]
        st.write(
            f"Average on logged days: **{logged['kcal'].mean():.0f} kcal**, "
            f"P {logged['protein'].mean():.0f} g, C {logged['carbs'].mean():.0f} g, F {logged['fat'].mean():.0f} g "
            f"({len(logged)} days logged)"
        )

    export = db.export_log(profile)
    if export:
        st.download_button("Download full log (CSV)", pd.DataFrame(export).to_csv(index=False),
                           file_name=f"meal_log_{profile}.csv", mime="text/csv")
