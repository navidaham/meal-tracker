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

The database is created automatically as `nutrition.db` next to the app.
Set `NUTRITION_DB=/some/path/nutrition.db` to put it elsewhere.

## Run tests

```bash
pip install pytest
pytest
```

## Deploy

**Important: SQLite and free hosts.** Free hosts (Streamlit Community Cloud, Hugging Face Spaces free tier)
have temporary disks, so your data can disappear when the app restarts or redeploys. That is fine for a demo.
For real use, either mount a persistent volume (option 3) or switch the storage layer to a hosted Postgres
(see "Next steps").

### 1. Streamlit Community Cloud (quickest for a CV demo)
1. Push this folder to a public GitHub repo.
2. Go to share.streamlit.io, sign in with GitHub, click **New app**, pick the repo, set the main file to `app.py`.
3. Deploy. You get a public URL to put on your CV.

### 2. Hugging Face Spaces
1. Create a new Space, choose the **Streamlit** SDK (or **Docker** and use the included Dockerfile).
2. Push the files. It builds and serves automatically.

### 3. Docker anywhere (Render, Fly.io, Railway, your own server)
```bash
docker build -t meal-tracker .
docker run -p 8501:8501 -v mealdata:/data meal-tracker
```
On Render/Fly/Railway, attach a persistent disk or volume mounted at `/data`.

**Public deployments have no login.** Anyone with the link can type any profile name and see that profile's
entries. For a portfolio demo, tell visitors to use a throwaway profile name. Before storing anything
personal, add authentication.

## Next steps (good CV material)
- Swap SQLite for Postgres (Supabase or Neon have free tiers) and add real user accounts
- Barcode lookup through the Open Food Facts product endpoint
- Reusable recipes: combine several foods into one saved meal
- Weekly plan view and an auto-generated shopping list
- Micronutrients (vitamins and minerals) from the USDA FoodData Central API
- Unit tests in CI (GitHub Actions) and a Docker image published on every push
