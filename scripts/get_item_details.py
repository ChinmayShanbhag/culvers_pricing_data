import requests
import json

def get_item_details(oloId, category_slug, item_slug, build_id):
    # Note: If this URL returns 404, the build ID 'h9DkZVoSWXYTzy8Ax-etC' has likely changed.
    url = f"https://www.culvers.com/_next/data/{build_id}/menu/{category_slug}/{item_slug}.json?oloId={oloId}"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        full_json = response.json()
        item = full_json.get('pageProps', {}).get('menuItem', {})
    except Exception as e:
        print(f"Error fetching {item_slug}: {e}")
        return None

    def process_options(options_list):
        """Recursively captures every attribute for every option."""
        if not options_list: return []
        results = []
        for opt in options_list:
            clean_opt = {
                "name": opt.get("name"),
                "cost": opt.get("cost"),
                "calories": opt.get("baseCalories"),
                "isDefault": opt.get("isDefault"),
                "isExclusive": opt.get("isExclusive"),
                "isRemoval": opt.get("isRemoval"),
                "image": opt.get("image"),
                "chainId": opt.get("chainId"),
                "nutritionUrl": None,
                "metadata": opt.get("metaData", []), # Captures hidden attributes
                "nested_size_options": process_options(opt.get("sizeOptions", []))
            }
            # Extract nutrition URL if hidden in metadata
            if clean_opt["metadata"]:
                for entry in clean_opt["metadata"]:
                    if entry.get("key") == "nutritionUrl":
                        clean_opt["nutritionUrl"] = entry.get("value")
            results.append(clean_opt)
        return results

    def process_modifier_group(mod):
        """Captures the rules and options for a modifier group."""
        if not mod: return None
        return {
            "title": mod.get("sectionTitle"),
            "description": mod.get("description"),
            "isMandatory": mod.get("isMandatory"),
            "maxQuantity": mod.get("maxAggregateQuantity"),
            "minQuantity": mod.get("minAggregateQuantity"),
            "totalQuantity": mod.get("totalQuantity"),
            "chainId": mod.get("chainId"),
            "options": process_options(mod.get("options", []))
        }

    # Build the final comprehensive document
    product_document = {
        "info": {
            "name": item.get("name"),
            "slug": item.get("slug"),
            "description": item.get("description"),
            "base_cost": item.get("cost"),
            "base_calories": item.get("baseCalories"),
            "image": item.get("image"),
            "category": item.get("categoryName"),
            "categoryId": item.get("categoryId")
        },
        "system_ids": {
            "oloId": oloId,
            "restaurantId": item.get("restaurantId"),
            "chainId": item.get("chainId")
        },
        "nutrition": {
            "main_nutrition_url": item.get("nutritionUrl")
        },
        "customizations": {
            "primary": process_modifier_group(item.get("primaryModifier")),
            "additional": [process_modifier_group(m) for m in item.get("modifiers", [])]
        }
    }

    return product_document

if __name__ == "__main__":
    # Test cases
    oloId = 126252
    
    # Example 1: Standard Burger
    res = get_item_details(oloId, 'butterburgers', 'mushroom--swiss')
    
    print(json.dumps(res, indent=2))