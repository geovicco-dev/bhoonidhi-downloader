import requests
from datetime import datetime, timedelta
from bhoonidhi_downloader.constants import BASE_URL

def get_satellite_sensor(satellite="ResourceSat-1", sensor="LISS3"):
    if satellite == 'ResourceSat-1' and sensor == 'LISS3':
        return "ResourceSat-1_LISS3"
    elif satellite == 'ResourceSat-1' and sensor == 'LISS4':
        return "ResourceSat-1_LISS4(MONO)"
    elif satellite == 'ResourceSat-2' and sensor == 'LISS3':
        return ["ResourceSat-2_LISS3", "ResourceSat-2_LISS3_BOA", "ResourceSat-2_LISS3_L2"]
    elif satellite == 'ResourceSat-2' and sensor == 'LISS4':
        return ["ResourceSat-2_LISS4(MX23)", "ResourceSat-2_LISS4(MX70)", "ResourceSat-2_LISS4(MX70)_L2"]
    elif satellite == 'ResourceSat-2A' and sensor == 'LISS3':
        return ["ResourceSat-2A_LISS3", "ResourceSat-2A_LISS3_BOA", "ResourceSat-2A_LISS3_L2"]
    elif satellite == 'ResourceSat-2A' and sensor == 'LISS4':
        return ["ResourceSat-2A_LISS4(MX23)", "ResourceSat-2A_LISS4(MX70)", "ResourceSat-2A_LISS4(MX70)_L2"]
    elif satellite == 'Sentinel-2A' and sensor == 'MSI':
        return ["Sentinel-2A_MSI_Level-1C", "Sentinel-2A_MSI_Level-2A"]
    elif satellite == 'Sentinel-2B' and sensor == 'MSI':
        return ["Sentinel-2B_MSI_Level-1C", "Sentinel-2B_MSI_Level-2A"]
    elif satellite == 'IRS-1C' and sensor == 'PAN':
        return ["IRS-1C_PAN"]
    elif satellite == 'IRS-1D' and sensor == 'PAN':
        return ["IRS-1D_PAN"]
    elif satellite == 'IRS-1D' and sensor == 'LISS3':
        return ["IRS-1D_LISS3"]
    else:
        print('Invalid selection. Please try again.')

def create_payload(gdf, satelite=None, sensor=None, start_date=None, end_date=None, product="Standard", user_id=None):
    # Ensure the GeoDataFrame is in EPSG:4326 (lat/lon)
    gdf = gdf.to_crs(epsg=4326)
    
    # Get the bounding box
    bounds = gdf.total_bounds
    tllon, brlat, brlon, tllat = bounds
    
    # Set default dates if not provided
    if not start_date:
        start_date = datetime.now() - timedelta(days=30)
    if not end_date:
        end_date = datetime.now()
    
    # Format dates
    sdate = start_date.strftime("%b%%2F%d%%2F%Y").upper()
    edate = end_date.strftime("%b%%2F%d%%2F%Y").upper()
    
    sat_sen = get_satellite_sensor(satellite=satelite, sensor=sensor)

    if isinstance(sat_sen, list):
        sat_sen = "%2C".join(sat_sen)
    else:
        sat_sen = sat_sen

    payload = {
        "userId": user_id,
        "prod": product,
        "selSats": sat_sen,
        "offset": "0",
        "sdate": sdate,
        "edate": edate,
        "query": "area",
        "queryType": "polygon",
        "isMX": "No",
        "tllat": tllat,
        "tllon": tllon,
        "brlat": brlat,
        "brlon": brlon,
        "filters": "%7B%7D"
    }
    return payload

def search_for_scenes(gdf, satellite, sensor, start_date, end_date, session):
    payload = create_payload(gdf, satelite=satellite, sensor=sensor, start_date=start_date,end_date=end_date, user_id=session.get("userId"))
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "token": session.get("jwt")
    }

    url = f"{BASE_URL}/bhoonidhi/ProductSearch"
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 200:
        data = response.json()
        results = data["Results"]
        return results
    else:
        print("Request failed. Status code:", response.status_code)