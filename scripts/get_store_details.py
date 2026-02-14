import requests
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm


def get_store_details(oloId):
    url = f"https://www.culvers.com/api/restaurants/getDetails?oloID={oloId}"
    response = requests.get(url)
    data = response.json()
    
    # Check if response has the expected structure
    if not data or 'data' not in data:
        print(f"Warning: Invalid response for oloId {oloId}, creating empty record")
        # Return a minimal record with just the oloId
        return {
            'oloId': oloId,
            'name': None,
            'restaurantId': None,
            'restaurantNumber': None,
            'ownerMessage': None,
            'ownerFriendlyName': None,
            'telephone': None,
            'latitude': None,
            'longitude': None,
            'curbsideInstructions': None,
            'carryoutInstructions': None,
            'driveThruInstructions': None,
            'customerFacingMessage': None,
            'openTime': None,
            'closeTime': None,
            'upcomingEvents': None,
            'onlineOrderStatus': None,
            'isDiningRoomClosed': None,
            'isLobbyClosed': None,
            'isDriveThruClosed': None,
            'isCurbsideUnavailable': None,
        }
    
    if 'restaurant' not in data['data'] or 'getRestaurantDetails' not in data['data']['restaurant']:
        print(f"Warning: Missing restaurant details for oloId {oloId}, creating empty record")
        # Return a minimal record with just the oloId
        return {
            'oloId': oloId,
            'name': None,
            'restaurantId': None,
            'restaurantNumber': None,
            'ownerMessage': None,
            'ownerFriendlyName': None,
            'telephone': None,
            'latitude': None,
            'longitude': None,
            'curbsideInstructions': None,
            'carryoutInstructions': None,
            'driveThruInstructions': None,
            'customerFacingMessage': None,
            'openTime': None,
            'closeTime': None,
            'upcomingEvents': None,
            'onlineOrderStatus': None,
            'isDiningRoomClosed': None,
            'isLobbyClosed': None,
            'isDriveThruClosed': None,
            'isCurbsideUnavailable': None,
        }
    
    data = data['data']['restaurant']['getRestaurantDetails']
    

    try:
        name = data['name']
    except:
        name = None

    try:
        restaurantId = data['restaurantId']
    except:
        restaurantId = None

    try:
        restaurantNumber = data['restaurantNumber']
    except:
        restaurantNumber = None

    try:
        ownerMessage = data['ownerMessage']
    except:
        ownerMessage = None

    try:
        ownerFriendlyName = data['ownerFriendlyName']
    except:
        ownerFriendlyName = None

    try:
        telephone = data['telephone']
    except:
        telephone = None

    try:
        latitude = data['latitude']
    except:
        latitude = None

    try:
        longitude = data['longitude']
    except:
        longitude = None

    # Initialize instruction variables
    curbsideInstructions = None
    dineInInstructions = None
    driveThruInstructions = None
    carryoutInstructions = None
    
    try:
        # labels is an array of objects with 'key' and 'value' properties
        for label in data['labels']:
            key = label.get('key', '').upper()
            value = label.get('value')
            
            if 'CURDSIDE' in key or 'CURBSIDE' in key:
                curbsideInstructions = value
            elif 'CARRYOUT' in key:
                carryoutInstructions = value
            elif 'DRIVETHRU' in key:
                driveThruInstructions = value
    except:
        pass
    
    try:
        customerFacingMessage = data['customerFacingMessage']
    except:
        customerFacingMessage = None
    
    try:
        openTime = data['openTime']
    except:
        openTime = None
    
    try:
        closeTime = data['closeTime']
    except:
        closeTime = None
    
    try:
        upcomingEvents = data['upcomingEvents']
    except:
        upcomingEvents = None

    try:
        onlineOrderStatus = data['onlineOrderStatus']
    except:
        onlineOrderStatus = None
    
    try:
        isDiningRoomClosed = data['isDiningRoomClosed']
    except:
        isDiningRoomClosed = None

    try:
        isLobbyClosed = data['isLobbyClosed']
    except:
        isLobbyClosed = None
    
    try:
        isDriveThruClosed = data['isDriveThruClosed']
    except:
        isDriveThruClosed = None
    
    try:
        isCurbsideUnavailable = data['isCurdsideUnavailable']
    except:
        isCurbsideUnavailable = None
    

    details = {
        'oloId': oloId,
        'name': name,
        'restaurantId': restaurantId,
        'restaurantNumber': restaurantNumber,
        'ownerMessage': ownerMessage,
        'ownerFriendlyName': ownerFriendlyName,
        'telephone': telephone,
        'latitude': latitude,
        'longitude': longitude,
        'curbsideInstructions': curbsideInstructions,
        'carryoutInstructions': carryoutInstructions,
        'driveThruInstructions': driveThruInstructions,
        'customerFacingMessage': customerFacingMessage,
        'openTime': openTime,
        'closeTime': closeTime,
        'upcomingEvents': upcomingEvents,
        'onlineOrderStatus': onlineOrderStatus,
        'isDiningRoomClosed': isDiningRoomClosed,
        'isLobbyClosed': isLobbyClosed,
        'isDriveThruClosed': isDriveThruClosed,
        'isCurbsideUnavailable': isCurbsideUnavailable,
    }

    return details


if __name__ == "__main__":
    df = pd.read_csv('data/stores.csv')
    olo_ids = df['oloId'].dropna().tolist()
    
    # Use ThreadPoolExecutor for parallel API calls
    store_details_list = []
    max_workers = 16  # Number of parallel threads (adjust as needed)
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_oloid = {executor.submit(get_store_details, olo_id): olo_id for olo_id in olo_ids}
        
        # Process completed tasks with progress bar
        for future in tqdm(as_completed(future_to_oloid), total=len(olo_ids), desc="Fetching store details"):
            try:
                store_details = future.result()
                # Always append the result (even if it has None values)
                if store_details is not None:
                    store_details_list.append(store_details)
                else:
                    # If None was returned unexpectedly, create a minimal record
                    olo_id = future_to_oloid[future]
                    print(f"Warning: No data returned for oloId {olo_id}, creating empty record")
                    store_details_list.append({
                        'oloId': olo_id,
                        'name': None,
                        'restaurantId': None,
                        'restaurantNumber': None,
                        'ownerMessage': None,
                        'ownerFriendlyName': None,
                        'telephone': None,
                        'latitude': None,
                        'longitude': None,
                        'curbsideInstructions': None,
                        'carryoutInstructions': None,
                        'driveThruInstructions': None,
                        'customerFacingMessage': None,
                        'openTime': None,
                        'closeTime': None,
                        'upcomingEvents': None,
                        'onlineOrderStatus': None,
                        'isDiningRoomClosed': None,
                        'isLobbyClosed': None,
                        'isDriveThruClosed': None,
                        'isCurbsideUnavailable': None,
                    })
            except Exception as exc:
                olo_id = future_to_oloid[future]
                print(f"oloId {olo_id} generated an exception: {exc}")
                # Create a record with the oloId even if there was an exception
                store_details_list.append({
                    'oloId': olo_id,
                    'name': None,
                    'restaurantId': None,
                    'restaurantNumber': None,
                    'ownerMessage': None,
                    'ownerFriendlyName': None,
                    'telephone': None,
                    'latitude': None,
                    'longitude': None,
                    'curbsideInstructions': None,
                    'carryoutInstructions': None,
                    'driveThruInstructions': None,
                    'customerFacingMessage': None,
                    'openTime': None,
                    'closeTime': None,
                    'upcomingEvents': None,
                    'onlineOrderStatus': None,
                    'isDiningRoomClosed': None,
                    'isLobbyClosed': None,
                    'isDriveThruClosed': None,
                    'isCurbsideUnavailable': None,
                })
    
    detail_df = pd.DataFrame(store_details_list)
    
    detail_df['oloId'] = detail_df['oloId'].astype('Int64')
    detail_df['restaurantId'] = detail_df['restaurantId'].astype('Int64')
    detail_df['restaurantNumber'] = detail_df['restaurantNumber'].astype('Int64')
    detail_df['onlineOrderStatus'] = detail_df['onlineOrderStatus'].astype('Int64')

    detail_df.to_csv('data/store_details.csv', index=False)