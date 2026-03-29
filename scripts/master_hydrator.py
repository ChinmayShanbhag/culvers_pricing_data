import os
import re
import json
import requests
import pandas as pd
from tqdm import tqdm
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from get_categories import get_categories
from get_category_items import get_category_items
from get_item_details import get_item_details

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
MENU_DIR = DATA_DIR / "menus"


def get_current_build_id():
    try:
        response = requests.get("https://www.culvers.com/menu", timeout=10)
        match = re.search(r'"buildId":"(.*?)"', response.text)
        return match.group(1) if match else "h9DkZVoSWXYTzy8Ax-etC"
    except Exception:
        return "h9DkZVoSWXYTzy8Ax-etC"


def load_existing_store(olo_id: int) -> dict | None:
    path = MENU_DIR / f"{olo_id}.json"
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def save_store(doc: dict):
    MENU_DIR.mkdir(parents=True, exist_ok=True)
    path = MENU_DIR / f"{doc['oloId']}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=2, default=str)


def process_single_store(row, current_build: str) -> str:
    olo_id = int(row["oloId"])
    current_date = datetime.now().strftime("%Y-%m-%d")

    existing = load_existing_store(olo_id)
    if existing and existing.get("last_updated", "").startswith(current_date):
        return f"Skipped {olo_id} (Already updated today)"

    master_doc = {
        "oloId": olo_id,
        "metadata": row.to_dict(),
        "last_updated": datetime.now().isoformat(),
        "build_id": current_build,
        "menu": [],
    }

    try:
        categories = get_categories(olo_id, build_id=current_build)
        for cat in categories:
            cat_node = {
                "categoryName": cat["categoryName"],
                "categorySlug": cat["categorySlug"],
                "items": [],
            }
            items_list = get_category_items(olo_id, cat["categorySlug"], build_id=current_build)

            with ThreadPoolExecutor(max_workers=16) as item_exec:
                futures = {
                    item_exec.submit(
                        get_item_details, olo_id, cat["categorySlug"], item["itemSlug"], current_build
                    ): item
                    for item in items_list
                }
                for future in as_completed(futures):
                    res = future.result()
                    if res:
                        cat_node["items"].append(res)

            master_doc["menu"].append(cat_node)

        save_store(master_doc)
        return f"Completed {olo_id}"

    except Exception as e:
        return f"Error on {olo_id}: {str(e)}"


def hydrate_store_menus():
    df_locations = pd.read_csv(DATA_DIR / "stores.csv")
    df_details = pd.read_csv(DATA_DIR / "store_details.csv")
    full_info = pd.merge(df_locations, df_details, on="oloId", how="left")
    full_info = full_info.replace({pd.NA: None, float("nan"): None})

    current_build = get_current_build_id()
    max_store_workers = 8

    stores_to_process = [row for _, row in full_info.iterrows()]

    with ThreadPoolExecutor(max_workers=max_store_workers) as store_exec:
        futures = [
            store_exec.submit(process_single_store, store, current_build)
            for store in stores_to_process
        ]

        for future in tqdm(as_completed(futures), total=len(futures), desc="Processing Stores"):
            result = future.result()
            if "Error" in result:
                tqdm.write(f"  {result}")


if __name__ == "__main__":
    hydrate_store_menus()
