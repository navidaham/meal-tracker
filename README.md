# Meal Tracker

A small Streamlit app to log meals, plan meals, and see calories and macros against your own daily targets.

- **Log**: record what you ate per meal, with live totals and progress bars
- **Plan**: plan a day ahead, then copy the plan into the log with one click
- **Foods**: search [Open Food Facts](https://world.openfoodfacts.org) (free, no API key) or add your own foods
- **History**: calories and macros over the last 7 to 90 days, plus CSV export
- Separate **profiles** (just a name in the sidebar) so more than one person can use the same instance

Stack: Python, Streamlit, SQLite, pandas.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```


URL: https://meal-tracker-onq9pzsapawkruldr4bzis.streamlit.app/ 


