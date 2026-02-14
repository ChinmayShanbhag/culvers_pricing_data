import os
import re
import requests
import pandas as pd
from pymongo import MongoClient
from dotenv import load_dotenv
from tqdm import tqdm
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# Import your script functions
from get_categories import get_categories
from get_category_items import get_category_items
from get_item_details import get_item_details

load_dotenv()

def get_current_build_id():
    try:
        response = requests.get("https://www.culvers.com/menu", timeout=10)
        match = re.search(r'"buildId":"(.*?)"', response.text)
        return match.group(1) if match else "h9DkZVoSWXYTzy8Ax-etC"
    except:
        return "h9DkZVoSWXYTzy8Ax-etC"

def get_mongo_client():
    uri = os.getenv("MONGO_URI")
    try:
        client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        return client
    except:
        return None

def process_single_store(row, current_build, db_name):
    """Function to process one store entirely."""
    client = get_mongo_client()
    if not client: return False
    
    collection = client[db_name]["stores"]
    oloId = int(row['oloId'])
    current_date = datetime.now().strftime('%Y-%m-%d')

    # --- 1. SKIP LOGIC ---
    # Check if a document exists for this oloId updated TODAY
    existing = collection.find_one({
        "oloId": oloId, 
        "last_updated": {"$regex": f"^{current_date}"}
    }, {"_id": 1})
    
    if existing:
        client.close()
        return f"Skipped {oloId} (Already updated today)"

    # --- 2. SCRAPING LOGIC ---
    master_doc = {
        "oloId": oloId,
        "metadata": row.to_dict(),
        "last_updated": datetime.now().isoformat(),
        "build_id": current_build,
        "menu": []
    }

    try:
        categories = get_categories(oloId, build_id=current_build)
        for cat in categories:
            cat_node = {"categoryName": cat['categoryName'], "categorySlug": cat['categorySlug'], "items": []}
            items_list = get_category_items(oloId, cat['categorySlug'], build_id=current_build)
            
            # Parallel Item Fetching
            with ThreadPoolExecutor(max_workers=16) as item_exec:
                futures = {
                    item_exec.submit(get_item_details, oloId, cat['categorySlug'], item['itemSlug'], current_build): item 
                    for item in items_list
                }
                for future in as_completed(futures):
                    res = future.result()
                    if res: cat_node["items"].append(res)
            
            master_doc["menu"].append(cat_node)
            
        collection.update_one({"oloId": oloId}, {"$set": master_doc}, upsert=True)
        client.close()
        return f"Completed {oloId}"
    
    except Exception as e:
        client.close()
        return f"Error on {oloId}: {str(e)}"

def hydrate_store_menus():
    # Setup
    db_name = os.getenv("MONGO_DB_NAME", "culvers_db")
    df_locations = pd.read_csv('data/stores.csv')
    df_details = pd.read_csv('data/store_details.csv')
    full_info = pd.merge(df_locations, df_details, on='oloId', how='left')
    full_info = full_info.replace({pd.NA: None, float('nan'): None})

    current_build = get_current_build_id()
    
    # --- 3. PARALLEL STORE PROCESSING ---
    # We process 8 stores at a time (each store handles its own item threads)
    # Total concurrency = 8 stores * 16 items = 128 concurrent HTTP requests
    max_store_workers = 8
    
    stores_to_process = [row for _, row in full_info.iterrows()]
    
    with ThreadPoolExecutor(max_workers=max_store_workers) as store_exec:
        futures = [
            store_exec.submit(process_single_store, store, current_build, db_name) 
            for store in stores_to_process
        ]
        
        # tqdm wraps the completion of store tasks
        for future in tqdm(as_completed(futures), total=len(futures), desc="Processing Stores"):
            result = future.result()
            # Use tqdm.write so the bar stays at the bottom while logs scroll up
            if "Error" in result:
                tqdm.write(f"⚠️ {result}")

if __name__ == "__main__":
    hydrate_store_menus()