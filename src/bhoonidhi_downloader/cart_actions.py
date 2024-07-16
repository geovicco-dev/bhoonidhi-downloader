from bhoonidhi_downloader import load_session_info, save_session_info
from bhoonidhi_downloader.utils import encode_scene_meta
import requests
import typer
from datetime import datetime
import json
import urllib.parse
from bhoonidhi_downloader.constants import BASE_URL
from bhoonidhi_downloader import authenticate

def view_cart(userId: str, cart_date: str, token: str):
    url = f"{BASE_URL}/bhoonidhi/CartServlet"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "token": token
    }
    date_object = datetime.strptime(cart_date, "%Y%m%d")
    # Format the date as required (assuming you want "DD Month YYYY" format)
    formatted_date = date_object.strftime("%d %B %Y")
    formatted_date = formatted_date.replace(" ", "%20")
        
    payload = {"userId":userId,"cartDate":formatted_date,"action":"VIEWCART"}
    response = requests.post(url, data=json.dumps(payload), headers=headers)
    return response

def add_scene_to_cart(scene):
    session = load_session_info()
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "token": session.get("jwt")
    }
    payload = {
        "dop":scene["DOP"],
        "PROD_ID":scene["ID"],
        "PROD_AV":"Y",
        "srt":scene["srt"],
        "selProds": encode_scene_meta(scene),
        "action":"ADDTOCART",
        "userId":session.get("userId")
    }
        
    url = f"{BASE_URL}/bhoonidhi/CartServlet"
    
    res = requests.post(url, headers=headers, json=payload)
    if res.status_code == 200:
        print("Scene added to card.")
        print(res.json())
    else:
        print("Error adding scene to card. Status code:", res.status_code)