import os
import json
from pymongo import MongoClient
from dotenv import load_dotenv
from bson import json_util

load_dotenv()

def download_full_database():
    uri = os.getenv("MONGO_URI")
    db_name = os.getenv("MONGO_DB_NAME", "culvers_db")
    
    print(f"Connecting to {db_name}...")
    client = MongoClient(uri)
    db = client[db_name]
    collection = db["stores"]

    # Fetch all documents
    cursor = collection.find({})
    
    # MongoDB documents contain special types (like ObjectIDs)
    # json_util ensures these are converted to readable strings
    all_data = list(cursor)
    
    output_file = "data/culvers_full.json"
    
    with open(output_file, "w", encoding="utf-8") as f:
        # indent=2 makes the file human-readable
        json.dump(all_data, f, default=json_util.default, indent=2)

    print(f"✅ Success! Exported {len(all_data)} stores to {output_file}")
    client.close()

if __name__ == "__main__":
    download_full_database()