import requests
from datetime import datetime, timedelta
from bhoonidhi_downloader.constants import BASE_URL
from bhoonidhi_downloader.utils import flatten_dict_to_1d
from bhoonidhi_downloader.constants import satellite_sensor_map, supported_satellites
from rich.progress import Progress

def get_satellite_sensor(satellite=None, sensor=None):
    if satellite == 'ResourceSat-1' and sensor == 'LISS3':
        return satellite_sensor_map.get('RS1').get('LISS3')
    elif satellite == 'ResourceSat-1' and sensor == 'LISS4':
        return satellite_sensor_map.get('RS1').get('LISS4')
    elif satellite == 'ResourceSat-1' and sensor is None:
        return flatten_dict_to_1d(satellite_sensor_map.get('RS1'))
    
    elif satellite == 'ResourceSat-2' and sensor == 'LISS3':
        return satellite_sensor_map.get('RS2').get('LISS3')
    elif satellite == 'ResourceSat-2' and sensor == 'LISS4':
        return satellite_sensor_map.get('RS2').get('LISS4')
    elif satellite == 'ResourceSat-2' and sensor == 'AWIFS':
        return satellite_sensor_map.get('RS2').get('AWIFS')
    elif satellite == 'ResourceSat-2' and sensor is None:
        return flatten_dict_to_1d(satellite_sensor_map.get('RS2'))
    
    elif satellite == 'ResourceSat-2A' and sensor == 'LISS3':
        return satellite_sensor_map.get('RS2A').get('LISS3')
    elif satellite == 'ResourceSat-2A' and sensor == 'LISS4':
        return satellite_sensor_map.get('RS2A').get('LISS4')
    elif satellite == 'ResourceSat-2A' and sensor == 'AWIFS':
        return satellite_sensor_map.get('RS2A').get('AWIFS')
    elif satellite == 'ResourceSat-2A' and sensor is None:
        return flatten_dict_to_1d(satellite_sensor_map.get('RS2A'))
    
    elif satellite == 'Sentinel-2A':
        sensor = None
        return satellite_sensor_map.get('S2A').get('MSI')
    
    elif satellite == 'Sentinel-2B':
        sensor = None
        return satellite_sensor_map.get('S2B').get('MSI')
    
    elif satellite == 'IRS-1A' and sensor == 'LISS1':
        return satellite_sensor_map.get('IRS-1A').get('LISS1')
    elif satellite == 'IRS-1A' and sensor == 'LISS2':
        return satellite_sensor_map.get('IRS-1A').get('LISS2')
    elif satellite == 'IRS-1A' and sensor is None:
        return flatten_dict_to_1d(satellite_sensor_map.get('IRS-1A'))
    
    elif satellite == 'IRS-1B' and sensor == 'LISS1':
        return satellite_sensor_map.get('IRS-1B').get('LISS1')
    elif satellite == 'IRS-1B' and sensor == 'LISS2':
        return satellite_sensor_map.get('IRS-1B').get('LISS2')
    elif satellite == 'IRS-1B' and sensor is None:
        return flatten_dict_to_1d(satellite_sensor_map.get('IRS-1B'))
    
    elif satellite == 'IRS-1C' and sensor == 'PAN':
        return satellite_sensor_map.get('IRS1C').get('PAN')
    elif satellite == 'IRS-1C' and sensor == 'WIFS':
        return satellite_sensor_map.get('IRS1C').get('WIFS')
    elif satellite == 'IRS-1C' and sensor is None:
        return flatten_dict_to_1d(satellite_sensor_map.get('IRS1C'))
    
    elif satellite == 'IRS-1D' and sensor == 'PAN':
        return satellite_sensor_map.get('IRS1D').get('PAN')
    elif satellite == 'IRS-1D' and sensor == 'LISS3':
        return satellite_sensor_map.get('IRS1D').get('LISS3')
    elif satellite == 'IRS-1D' and sensor == 'WIFS':
        return satellite_sensor_map.get('IRS1D').get('WIFS')
    elif satellite == 'IRS-1D' and sensor is None:
        return flatten_dict_to_1d(satellite_sensor_map.get('IRS1D'))
    
    elif satellite == 'Sentinel-1A':
        sensor = None
        return satellite_sensor_map.get('S1A').get('SAR')
    
    elif satellite == 'Sentinel-1B':
        sensor = None
        return satellite_sensor_map.get('S1B').get('SAR')
    
    elif satellite == 'CartoSat-1':
        sensor = None
        return satellite_sensor_map.get('CartoSat-1').get('PAN')
    
    elif satellite == 'EOS-04':
        sensor = None
        return satellite_sensor_map.get('EOS-04').get('SAR')
        
    elif satellite == 'Landsat-8':
        sensor = None
        return satellite_sensor_map.get('LandSat-8').get('OLI+TIRS')
    
    elif satellite == "Landsat-9":
        sensor = None
        return satellite_sensor_map.get('LandSat-9').get('OLI+TIRS')
    
    elif satellite is None and sensor is None:
        return flatten_dict_to_1d(satellite_sensor_map)

    else:
        print('Satellite and sensor combination not found. Please try again with a valid combination.\n----> Available satellites are: \nResourceSat-1, ResourceSat-2, ResourceSat-2A, Sentinel-2A, Sentinel-2B, IRS-1C, IRS-1D\n')

def create_payload(gdf, satelite, sensor, start_date, end_date, product="Standard", user_id=None):
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
    results = []
    if satellite is None and sensor is None:
        with Progress() as progress:
            task = progress.add_task("[green]Searching...", total=len(supported_satellites))
            for sat in supported_satellites:
                try:
                    sat_results = search_for_scenes(gdf, sat, None, start_date, end_date, session)
                    results.extend(sat_results)
                except:
                    pass
                progress.update(task, advance=1)
        return results
    
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