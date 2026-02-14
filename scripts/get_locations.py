import requests
import pandas as pd

us_states = [
    'AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA',
    'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD',
    'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ',
    'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC',
    'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY'
]

us_states.append('Carbondale,%20IL')
us_states.append('Chicago,%20IL')

us_states.append('Tallahassee,%20FL')
us_states.append('Miami,%20FL')

us_states.append('Milwaukee,%20WI')
us_states.append('Superior,%20WI')

us_states.append('Traverse%20City,%20MI')
us_states.append('Detroit,%20MI')


def get_locations():

    stores = []
    count = 0
    for state in us_states:
        print(f"progress: {count}/{len(us_states)}")
        if '%' in state:
            url = f"https://www.culvers.com/api/locator/getLocations?location={state}%20US&radius=600000&limit=0&layer="
        else:
            url = f"https://www.culvers.com/api/locator/getLocations?location={state}%20US&radius=600000&limit=0&layer=state"
        response = requests.get(url)
        data = response.json()

        
        geofences = data['data']['geofences']

        for geofence in geofences:
            
            try:
                _id = geofence['_id']
            except:
                _id = None
            try:
                live = geofence['live']
            except:
                live = None
            try:
                description = geofence['description']
            except:
                description = None

            metadata = geofence['metadata']

            try:
                oloId = metadata['oloId']
                if oloId == '' or oloId is None:
                    oloId = None
                else:
                    oloId = int(oloId)
            except:
                oloId = None
            try:
                slug = metadata['slug']
            except:
                slug = None

            try:
                openDate = metadata['openDate']
            except:
                openDate = None
            try:
                isTemporarilyClosed = metadata['isTemporarilyClosed']
            except:
                isTemporarilyClosed = None

            try:
                street = metadata['street']
            except:
                street = None
            try:
                state = metadata['state']
            except:
                state = None
            try:
                city = metadata['city']
            except:
                city = None
            try:
                postalCode = metadata['postalCode']
                if postalCode == '' or postalCode is None:
                    postalCode = None
                else:
                    postalCode = int(postalCode)
            except:
                postalCode = None

            
            try:
                dineInHours = metadata['dineInHours']
            except:
                dineInHours = None
            try:
                driveThruHours = metadata['driveThruHours']
            except:
                driveThruHours = None
            try:
                curbsideHours = metadata['curbsideHours']
            except:
                curbsideHours = None

            try:
                flavorOfDayName = metadata['flavorOfDayName']
            except:
                flavorOfDayName = None
            try:
                flavorOfTheDayDescription = metadata['flavorOfTheDayDescription']
            except:
                flavorOfTheDayDescription = None
            try:
                handoffOptions = metadata['handoffOptions']
            except:
                handoffOptions = None

            store_data = {
                '_id': _id,
                'live': live,
                'description': description,
                'oloId': oloId,
                'slug': slug,
                'openDate': openDate,
                'isTemporarilyClosed': isTemporarilyClosed,
                'street': street,
                'state': state,
                'city': city,
                'postalCode': postalCode,
                'flavorOfDayName': flavorOfDayName,
                'flavorOfTheDayDescription': flavorOfTheDayDescription,
                'handoffOptions': handoffOptions,
                'dineInHours': dineInHours,
                'driveThruHours': driveThruHours,
                'curbsideHours': curbsideHours,
            }

            stores.append(store_data)
        count += 1

    return stores
        

if __name__ == "__main__":
    stores = get_locations()
    df = pd.DataFrame(stores)
    df['oloId'] = df['oloId'].astype('Int64')
    df['postalCode'] = df['postalCode'].astype('Int64')
    df = df[df['oloId'].fillna(-1) != 128582]
    df = df.drop_duplicates()
    df = df.sort_values(by=['state', 'oloId', 'openDate'])
    df.to_csv('data/stores.csv', index=False)

