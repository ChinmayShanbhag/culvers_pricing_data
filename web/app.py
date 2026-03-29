import os
import re
import json
import ast
from pathlib import Path
from typing import Optional

import httpx
import pandas as pd
from fastapi import FastAPI, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
MENU_DIR = DATA_DIR / "menus"

app = FastAPI(title="Culver's Store Explorer")
app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")

_build_id_cache: dict = {"id": None}


def load_stores() -> pd.DataFrame:
    stores_path = DATA_DIR / "stores.csv"
    details_path = DATA_DIR / "store_details.csv"

    if not stores_path.exists():
        return pd.DataFrame()

    df_locations = pd.read_csv(stores_path)

    if details_path.exists():
        df_details = pd.read_csv(details_path)
        df = pd.merge(df_locations, df_details, on="oloId", how="left")
    else:
        df = df_locations

    df = df.where(pd.notnull(df), None)
    return df


def parse_hours(raw: Optional[str]) -> Optional[dict]:
    if not raw or pd.isna(raw):
        return None
    try:
        return json.loads(raw.replace("'", '"'))
    except (json.JSONDecodeError, TypeError):
        try:
            return ast.literal_eval(raw)
        except (ValueError, SyntaxError):
            return None


def row_to_store(row: pd.Series) -> dict:
    store = {}
    for col in row.index:
        val = row[col]
        if pd.isna(val) if isinstance(val, float) else val is None:
            store[col] = None
        elif isinstance(val, (int, float)):
            store[col] = val
        else:
            store[col] = str(val)

    for hours_field in ("dineInHours", "driveThruHours", "curbsideHours"):
        store[hours_field] = parse_hours(store.get(hours_field))

    return store


@app.get("/", response_class=HTMLResponse)
async def index():
    html_path = Path(__file__).parent / "templates" / "index.html"
    return HTMLResponse(content=html_path.read_text(encoding="utf-8"))


@app.get("/api/stores")
async def get_stores(
    state: Optional[str] = Query(None, description="Filter by state abbreviation"),
    city: Optional[str] = Query(None, description="Filter by city name"),
    search: Optional[str] = Query(None, description="Search store name/description"),
    open_only: bool = Query(False, description="Only show non-temporarily-closed stores"),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=500),
):
    df = load_stores()
    if df.empty:
        return {"stores": [], "total": 0, "page": 1, "pages": 0}

    if state:
        df = df[df["state"].str.upper() == state.upper()]
    if city:
        df = df[df["city"].str.lower().str.contains(city.lower(), na=False)]
    if search:
        mask = (
            df["description"].str.lower().str.contains(search.lower(), na=False)
            | df.get("name", pd.Series(dtype=str)).str.lower().str.contains(search.lower(), na=False)
        )
        df = df[mask]
    if open_only:
        df = df[df["isTemporarilyClosed"] != True]

    total = len(df)
    pages = max(1, (total + per_page - 1) // per_page)
    page = min(page, pages)
    start = (page - 1) * per_page
    page_df = df.iloc[start : start + per_page]

    stores = [row_to_store(row) for _, row in page_df.iterrows()]

    return {"stores": stores, "total": total, "page": page, "pages": pages}


@app.get("/api/stores/{olo_id}")
async def get_store(olo_id: int):
    df = load_stores()
    match = df[df["oloId"] == olo_id]
    if match.empty:
        return JSONResponse(status_code=404, content={"error": "Store not found"})
    return row_to_store(match.iloc[0])


@app.get("/api/stats")
async def get_stats():
    df = load_stores()
    if df.empty:
        return {"total_stores": 0, "states": [], "flavor_counts": {}}

    states = sorted(df["state"].dropna().unique().tolist())
    stores_per_state = df.groupby("state").size().to_dict()

    flavor_counts = {}
    if "flavorOfDayName" in df.columns:
        flavor_counts = (
            df["flavorOfDayName"]
            .dropna()
            .value_counts()
            .head(20)
            .to_dict()
        )

    temporarily_closed = int(df["isTemporarilyClosed"].sum()) if "isTemporarilyClosed" in df.columns else 0

    return {
        "total_stores": len(df),
        "total_states": len(states),
        "states": states,
        "stores_per_state": stores_per_state,
        "top_flavors": flavor_counts,
        "temporarily_closed": temporarily_closed,
    }


@app.get("/api/map-data")
async def get_map_data():
    df = load_stores()
    if df.empty:
        return []

    required = ["latitude", "longitude"]
    if not all(c in df.columns for c in required):
        return []

    df_map = df.dropna(subset=["latitude", "longitude"])

    points = []
    for _, row in df_map.iterrows():
        points.append({
            "oloId": int(row["oloId"]) if pd.notna(row.get("oloId")) else None,
            "lat": float(row["latitude"]),
            "lng": float(row["longitude"]),
            "name": str(row.get("name") or row.get("description") or ""),
            "city": str(row.get("city") or ""),
            "state": str(row.get("state") or ""),
            "flavor": str(row.get("flavorOfDayName") or ""),
            "telephone": str(row.get("telephone") or ""),
        })

    return points


# ── Menu API (live proxy to Culver's Next.js data routes) ──

async def _get_build_id() -> str:
    if _build_id_cache["id"]:
        return _build_id_cache["id"]
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get("https://www.culvers.com/menu")
            match = re.search(r'"buildId":"(.*?)"', resp.text)
            if match:
                _build_id_cache["id"] = match.group(1)
                return _build_id_cache["id"]
    except Exception:
        pass
    return "h9DkZVoSWXYTzy8Ax-etC"


def _load_cached_menu(olo_id: int) -> Optional[dict]:
    path = MENU_DIR / f"{olo_id}.json"
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


@app.get("/api/menu/{olo_id}/categories")
async def get_menu_categories(olo_id: int):
    cached = _load_cached_menu(olo_id)
    if cached and cached.get("menu"):
        return [
            {"categoryName": c["categoryName"], "categorySlug": c["categorySlug"]}
            for c in cached["menu"]
        ]

    build_id = await _get_build_id()
    url = f"https://www.culvers.com/_next/data/{build_id}/menu.json?oloId={olo_id}"
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            categories = resp.json()["pageProps"]["categories"]
            return [
                {
                    "categoryId": c.get("categoryId"),
                    "categoryName": c["name"],
                    "categorySlug": c["slug"],
                    "categoryImage": c.get("image"),
                }
                for c in categories
            ]
    except Exception as e:
        return JSONResponse(status_code=502, content={"error": f"Failed to fetch categories: {e}"})


@app.get("/api/menu/{olo_id}/category/{category_slug}")
async def get_category_items(olo_id: int, category_slug: str):
    cached = _load_cached_menu(olo_id)
    if cached and cached.get("menu"):
        for cat in cached["menu"]:
            if cat.get("categorySlug") == category_slug:
                return cat.get("items", [])

    build_id = await _get_build_id()
    url = f"https://www.culvers.com/_next/data/{build_id}/menu/{category_slug}.json?oloId={olo_id}"
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            items = resp.json()["pageProps"]["category"]["items"]
            return [
                {
                    "info": {
                        "name": it["name"],
                        "slug": it["slug"],
                        "description": it.get("description"),
                        "base_cost": it.get("cost"),
                        "base_calories": it.get("baseCalories"),
                        "image": it.get("image"),
                    }
                }
                for it in items
            ]
    except Exception as e:
        return JSONResponse(status_code=502, content={"error": f"Failed to fetch items: {e}"})


def _process_options(options_list: list) -> list:
    if not options_list:
        return []
    results = []
    for opt in options_list:
        clean = {
            "name": opt.get("name"),
            "cost": opt.get("cost"),
            "calories": opt.get("baseCalories"),
            "isDefault": opt.get("isDefault"),
            "isExclusive": opt.get("isExclusive"),
            "isRemoval": opt.get("isRemoval"),
            "image": opt.get("image"),
            "nested_size_options": _process_options(opt.get("sizeOptions", [])),
        }
        results.append(clean)
    return results


def _process_modifier(mod: dict) -> Optional[dict]:
    if not mod:
        return None
    return {
        "title": mod.get("sectionTitle"),
        "description": mod.get("description"),
        "isMandatory": mod.get("isMandatory"),
        "maxQuantity": mod.get("maxAggregateQuantity"),
        "minQuantity": mod.get("minAggregateQuantity"),
        "options": _process_options(mod.get("options", [])),
    }


@app.get("/api/menu/{olo_id}/item/{category_slug}/{item_slug}")
async def get_item_detail(olo_id: int, category_slug: str, item_slug: str):
    cached = _load_cached_menu(olo_id)
    if cached and cached.get("menu"):
        for cat in cached["menu"]:
            if cat.get("categorySlug") == category_slug:
                for item in cat.get("items", []):
                    slug = item.get("info", {}).get("slug") or item.get("slug", "")
                    if slug == item_slug:
                        return item

    build_id = await _get_build_id()
    url = f"https://www.culvers.com/_next/data/{build_id}/menu/{category_slug}/{item_slug}.json?oloId={olo_id}"
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            item = resp.json()["pageProps"]["menuItem"]
            return {
                "info": {
                    "name": item.get("name"),
                    "slug": item.get("slug"),
                    "description": item.get("description"),
                    "base_cost": item.get("cost"),
                    "base_calories": item.get("baseCalories"),
                    "image": item.get("image"),
                    "category": item.get("categoryName"),
                },
                "nutrition": {
                    "main_nutrition_url": item.get("nutritionUrl"),
                },
                "customizations": {
                    "primary": _process_modifier(item.get("primaryModifier")),
                    "additional": [_process_modifier(m) for m in item.get("modifiers", [])],
                },
            }
    except Exception as e:
        return JSONResponse(status_code=502, content={"error": f"Failed to fetch item: {e}"})
