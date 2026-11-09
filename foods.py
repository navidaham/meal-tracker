"""Food lookup through Open Food Facts (free, no API key).

Nutrient values are returned per 100 g, matching how foods are stored in db.py.
"""
import requests

SEARCH_URL = "https://world.openfoodfacts.org/cgi/search.pl"
HEADERS = {"User-Agent": "MealTracker/0.1 (student project)"}


def _num(nutriments, key):
    try:
        return float(nutriments.get(key) or 0)
    except (TypeError, ValueError):
        return 0.0


def parse_product(product):
    """Turn one Open Food Facts product into a food dict, or None if unusable."""
    name = (product.get("product_name") or "").strip()
    n = product.get("nutriments") or {}
    if not name or "energy-kcal_100g" not in n:
        return None
    return {
        "name": name,
        "brand": (product.get("brands") or "").split(",")[0].strip(),
        "barcode": product.get("code"),
        "kcal": _num(n, "energy-kcal_100g"),
        "protein": _num(n, "proteins_100g"),
        "carbs": _num(n, "carbohydrates_100g"),
        "fat": _num(n, "fat_100g"),
        "fiber": _num(n, "fiber_100g"),
        "sugar": _num(n, "sugars_100g"),
        # Open Food Facts reports sodium in grams per 100 g.
        "sodium_mg": _num(n, "sodium_100g") * 1000,
        "source": "openfoodfacts",
    }


def search(query, limit=10):
    """Search by text. Returns (foods, error_message). One of them is empty."""
    query = query.strip()
    if not query:
        return [], ""
    params = {
        "search_terms": query,
        "search_simple": 1,
        "action": "process",
        "json": 1,
        "page_size": 25,
        "fields": "code,product_name,brands,nutriments",
    }
    try:
        r = requests.get(SEARCH_URL, params=params, headers=HEADERS, timeout=10)
        r.raise_for_status()
        products = r.json().get("products", [])
    except (requests.RequestException, ValueError) as e:
        return [], f"Could not reach Open Food Facts ({type(e).__name__}). Try again, or add the food manually."
    foods = [f for f in (parse_product(p) for p in products) if f]
    return foods[:limit], ""
