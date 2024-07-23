from bhoonidhi_downloader.constants import BASE_URL
from datetime import datetime
import json
import urllib
from rich.markup import escape
import subprocess
from typing import List
from rich.table import Table
from rich.console import Console
import csv
from tabulate import tabulate
import typer
from pathlib import Path
import requests

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

def display_search_results(scenes: List, console: Console):
    table = Table(title="Available Scenes")
    table.add_column("Index", style="blue")
    table.add_column("Scene ID", style="red")
    table.add_column("Date", style="blue")
    table.add_column("Satellite", style="red")
    table.add_column("Sensor", style="blue")
    table.add_column('Product', style="red")
    table.add_column("Metadata", style="blue")
    table.add_column("Quick View", style="red")
    
    for idx, scene in enumerate(scenes):
        table.add_row(
            str(idx+1),
            scene.get('ID', 'N/A'),
            scene.get('DOP', 'N/A'),
            scene.get('SATELLITE', 'N/A'),
            scene.get('SENSOR', 'N/A'),
            scene.get('PRODTYPE', 'N/A'),
            create_clickable_link(get_scene_meta_url(scene), "View Metadata"),
            create_clickable_link(get_quicklook_url(scene), "Quick View"),
        )

    console.print(table)
    # Instructions for the user
    console.print("\nTo open table links from terminal:", style="yellow")
    console.print("Click while holding Cmd (on Mac) or Ctrl (on Windows/Linux)\n", style="dim")

def get_download_url(scene_id: str, session: dict):
    scene = [scene for scene in session["scenes"] if scene['ID'] == scene_id][0]
    satellite = scene['SATELLITE']
    sensor = scene["SENSOR"]
    dirpath = scene['DIRPATH']
    filename = scene_id
    
    base_url = f"{BASE_URL}//bhoonidhi/data/"
    if satellite == 'R2A' and sensor == 'LIS3':
        sensor = '3'
    elif satellite == "R2A" and sensor == "LIS4":
        sensor = "F"
    elif satellite == 'R2A' and sensor == 'AWIF':
        sensor = 'W'
    elif satellite == 'RS2' and sensor == 'LIS3':
        sensor = '3'
    elif satellite == "RS2" and sensor == "LIS4":
        sensor = "F"
    elif satellite == 'RS2' and sensor == 'AWIF':
        sensor = 'W'    
    elif satellite == "SEN2A" or satellite == "SEN2B":
        sensor = "MSI"
    elif satellite == "SEN1A" or satellite == "SEN1B":
        sensor = "SAR"
    elif satellite == "L8" or satellite == "L9":
        sensor = "O"
    elif satellite == 'P5' and sensor == 'PAN':
        download_url = f"""{base_url}CARTODEM/{satellite}/{sensor}/30m/{filename}.zip?token={session.get("jwt")}&product_id={filename}"""
        return download_url
    # else:
    #     print('Donwload feature not supported!')
    
    download_url = f"""{base_url}/{satellite}/{sensor}/{dirpath.split("/")[-4:][:2][0]}/{dirpath.split("/")[-4:][:2][1]}/{filename}.zip?token={session.get("jwt")}&product_id={filename}"""
    return download_url

def download_scene(url, out_dir, scene_id, console: Console):
    out_file = out_dir / f"{scene_id}.zip"
    try:
        subprocess.run(["wget", url, "-O", str(out_file), "--quiet", "--show-progress"], check=True)
    except:
        console.print(f"Error downloading scene {scene_id}", style="bold red")
        return

def get_scenes_data_for_export(scenes: List):
    export_data = {
        scene.get('ID', f'Unknown_{idx}'): {
            "Index": idx + 1,
            "Date": scene.get('DOP', 'N/A'),
            "Satellite": scene.get('SATELLITE', 'N/A'),
            "Sensor": scene.get('SENSOR', 'N/A'),
            "Product": scene.get('PRODTYPE', 'N/A'),
            "Metadata": get_scene_meta_url(scene),
            "Quick View": get_quicklook_url(scene),
            "Search ID": scene.get("srt", "N/A")
        }
        for idx, scene in enumerate(scenes)
    }
    return export_data

def export_search_results(format: str, export_data: dict, filename: str):
    Path(filename).parent.mkdir(parents=True, exist_ok=True) # Create parent directory if it doesn't exist
    # Export as CSV
    if format == 'csv':
        export_data = list(export_data.values())
        with open(filename, 'w', newline='') as csvfile:
            fieldnames = export_data[0].keys()
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for row in export_data:
                writer.writerow(row)
                
        typer.echo(f"----> Exported search results as CSV to {filename}.")

    # Export as JSON
    if format == 'json':
        with open(filename, 'w') as jsonfile:
            json.dump(export_data, jsonfile)
    
        typer.echo(f"----> Exported search results as JSON to {filename}.")

    # Export as Markdown table
    if format == 'markdown':
        export_data = list(export_data.values())
        headers = export_data[0].keys()
        table = tabulate(
            [row.values() for row in export_data],
            headers=headers,
            tablefmt="pipe"
        )
        with open(filename, 'w') as mdfile:
            mdfile.write(table)
            
        typer.echo(f"----> Exported search results as Markdown table to {filename}.")
        
def flatten_dict_to_1d(d):
    values = []
    def _flatten(d):
        for v in d.values():
            if isinstance(v, dict):
                _flatten(v)
            elif isinstance(v, list):
                values.extend(v)
            else:
                values.append(v)
    _flatten(d)
    return values

def get_archive_data():
    url = f"{BASE_URL}/bhoonidhi/SatSenServlet"
    payload = {"userId":"T","action":"GETAVCONFIG","userEmail":"abc@xyz.com"}

    response = requests.post(url, json=payload)
    data = response.json()["Results"]
    return data

def show_archive_data(archive_data, console: Console):
    table = Table(title="Bhoonidhi Browse & Order Archive")
    table.add_column("Index", style="blue")
    table.add_column("Satellite", style="red")
    table.add_column("Availability", style="blue")
    table.add_column("Access Level", style="red")
    table.add_column("Sensors", style="blue")
    table.add_column('Resolution (m)', style="red")

    if len(archive_data) != 0:
        for idx, record in enumerate(archive_data):
            res_range = f"{record.get('thisMinRes')} - {record.get('thisMaxRes')}" if record.get('thisMinRes') != record.get('thisMaxRes') else record.get('thisMinRes')
            
            availability = f"{datetime.strptime(record.get('totalStartDate'), '%m/%d/%Y').strftime('%d %B %Y')} - {datetime.strptime(record.get('totalEndDate'), '%m/%d/%Y').strftime('%d %B %Y')}" if record.get('totalEndDate') != '' else f"{datetime.strptime(record.get('totalStartDate'), '%m/%d/%Y').strftime('%d %B %Y')} - till date"
            
            sensors_list = [r.get('senName') for r in record.get('sensors')]
            sensors = ', '.join(sensors_list)
            
            table.add_row(
                str(idx+1),
                record.get('satName', 'N/A'),
                availability,
                record.get('priced', 'N/A').split('_')[-1],
                sensors,
                res_range
            )

        console.print(table)

def filter_archive_data(archive_data, satelite, console: Console):
    # Filter archive data based on satelite
    data = [item.get('sensors') for item in archive_data if item.get('satName') == satelite]

    # Create table
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Satellite", style="cyan", no_wrap=True)
    table.add_column("Sensor", style="cyan", no_wrap=True)
    table.add_column("Resolution (m)", style="cyan", no_wrap=True)
    table.add_column("Start Date", style="cyan", no_wrap=True)
    table.add_column("End Date", style="cyan", no_wrap=True)
    table.add_column("Products", style="cyan", no_wrap=True)

    # Add rows
    for d in data:
        for i in d:
            if i.get('endDate') == '':
                i['endDate'] = 'Till date'
            table.add_row(
                i.get('satName', '-'),
                i.get('senName', '-'),
                i.get('res', '-'),
                i.get('stDate', '-'),
                i.get('endDate', '-'),
                i.get('products', '-')
            )
    console.print(table)