import requests
import pandas as pd

def get_categories(oloId, build_id):

    url = f"https://www.culvers.com/_next/data/{build_id}/menu.json?oloId={oloId}"

    response = requests.get(url)
    pageProps = response.json()['pageProps']
    categories = pageProps['categories']

    data = []

    for category in categories:
        # id = category['id']
        name = category['name']
        description = category['description']
        # featured = category['featured']
        # restaurantId = category['restaurantId']
        categoryId = category['categoryId']
        image = category['image']
        fallbackImage = category['fallbackImage']
        # locationString = category['locationString']
        # sortOrder = category['sortOrder']
        slug = category['slug']
        category_data = {
            'categoryId': categoryId,
            'categoryName': name,
            'categoryDescription': description,
            'categoryImage': image,
            'categoryFallbackImage': fallbackImage,
            'categorySlug': slug
        }
        data.append(category_data)
    

    return data

if __name__ == "__main__":
    oloId = 126252
    categories = get_categories(oloId)

    df = pd.DataFrame(categories)
    df.to_csv('data/categories.csv', index=False)
    