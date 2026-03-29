"""
Export all per-store menu JSON files into a single culvers_full.json.

Previously this script pulled from MongoDB. Now it reads the local
data/menus/*.json files written by master_hydrator.py.
"""

import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
MENU_DIR = DATA_DIR / "menus"


def export_full_database():
    if not MENU_DIR.exists():
        print("No menu data found. Run master_hydrator.py first.")
        return

    all_data = []
    for path in sorted(MENU_DIR.glob("*.json")):
        try:
            with open(path, "r", encoding="utf-8") as f:
                all_data.append(json.load(f))
        except (json.JSONDecodeError, OSError) as e:
            print(f"Skipping {path.name}: {e}")

    output_file = DATA_DIR / "culvers_full.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(all_data, f, indent=2, default=str)

    print(f"Exported {len(all_data)} stores to {output_file}")


if __name__ == "__main__":
    export_full_database()
