import requests
import pandas as pd

def get_category_items(oloId, category_slug, build_id):
    url = f"https://www.culvers.com/_next/data/{build_id}/menu/{category_slug}.json?oloId={oloId}"
    response = requests.get(url)

    pageProps = response.json()['pageProps']
    category = pageProps['category']
    items = category['items']

    data = []
    for item in items:
        id = item['id']
        chainId = item['chainId']
        name = item['name']
        description = item['description']
        cost = item['cost']
        baseCalories = item['baseCalories']
        image = item['image']
        fallbackImage = item['fallbackImage']
        nutritionUrl = item['nutritionUrl']
        slug = item['slug']

        item_data = {
            'itemId': id,
            'itemChainId': chainId,
            'itemName': name,
            'itemDescription': description,
            'itemCost': cost,
            'itemBaseCalories': baseCalories,
            'itemImage': image,
            'itemFallbackImage': fallbackImage,
            'itemNutritionUrl': nutritionUrl,
            'itemSlug': slug
        }

        data.append(item_data)


    return data



if __name__ == "__main__":
    oloId = 126252
    category_slug = 'butterburgers'
    data = get_category_items(oloId, category_slug)
    print(data)