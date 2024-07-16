from bhoonidhi_downloader.constants import BASE_URL
from datetime import datetime
import json
import urllib
from rich.markup import escape
from pathlib import Path
import subprocess

def parse_cart_date_from_sid(sid):
    """
    A function to parse the cart date from the given Search ID.

    Parameters:
    - sid: str, the Search ID containing the date part.

    Returns:
    - str: The formatted date in "DD Month YYYY" format.
    """
    # The date part is before the underscore in sid
    date_string = sid.split("_")[0]
    # Parse the date string
    date_object = datetime.strptime(date_string, "%Y%m%d")
    # Format the date as required (assuming you want "DD Month YYYY" format)
    formatted_date = date_object.strftime("%d %B %Y")
    formatted_date = formatted_date.replace(" ", "%20")    
    return formatted_date

def encode_scene_meta(data):
    """
    Parses the scene metadata by encoding it into a URL safe string.

    Parameters:
    - data: dict, the scene meta data to be parsed.

    Returns:
    - str, the URL safe encoded string representing the scene meta data.
    """
    json_string = json.dumps(data)
    encoded_string = urllib.parse.quote(json_string)
    return encoded_string

def get_scene_meta_url(scene):
    dirpath = scene["DIRPATH"]
    filename = scene["FILENAME"]
    meta_url = f"{BASE_URL}/{dirpath}/{filename}.meta"
    return meta_url

def get_quicklook_url(scene):
    dirpath = scene["DIRPATH"]
    filename = scene["FILENAME"]
    quicklook_url = f"{BASE_URL}/{dirpath}/{filename}.jpg"
    return quicklook_url

def create_clickable_link(url, text):
    return f"[link={url}]{escape(text)}[/link]"


def download_scene(scene_id: str, out_dir: Path, session: dict):
    scene = [scene for scene in session["scenes"] if scene['ID'] == scene_id][0]
    satellite = scene['SATELLITE']
    sensor = scene["SENSOR"]
    dirpath = scene['DIRPATH']
    filename = scene_id

    base_url = f"{BASE_URL}//bhoonidhi/data/"
    if satellite == "R2A" and sensor == "LIS4":
        sensor = "F"
    elif satellite == "RS2" and sensor == "LIS4":
        sensor = "F"
    elif satellite == 'R2A' and sensor == 'LIS3':
        sensor = '3'
    elif satellite == 'RS2' and sensor == 'LIS3':
        sensor = '3'
    elif satellite == "SEN2A" or satellite == "SEN2B":
        sensor = "MSI"
    else:
        print('Invalid selection. Please try again.')

    download_url = f"""{base_url}/{satellite}/{sensor}/{dirpath.split("/")[-4:][:2][0]}/{dirpath.split("/")[-4:][:2][1]}/{filename}.zip?token={session.get("jwt")}&product_id={filename}"""
    
    # Use WGET to download the file
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f'{filename}.zip'
    subprocess.run(["wget", download_url, "-O", out_file])