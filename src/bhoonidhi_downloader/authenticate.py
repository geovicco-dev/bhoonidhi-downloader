import requests
import json
import os
from bhoonidhi_downloader.constants import BASE_URL


def login(username, password):
    """
    A function to log in to Bhoonidhi with the provided username and password.

    Parameters:
    - username: str, the username for logging in.
    - password: str, the password for logging in.

    Returns:
    - dict: The response data containing user information if login is successful.
    """
    login_url = os.path.join(BASE_URL, "bhoonidhi/LoginServlet")
    payload = {
        "userId": username,
        "password": password,
        "action": "VALIDATE_LOGIN",
        "oldDB": "false"
    }
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    response = requests.post(login_url, data=json.dumps(payload), headers=headers)
    if response.status_code == 200:
        response_data = response.json()["Results"][0]
        if "JWT" in response_data and response_data["JWT"]:
            return response_data
        else:
            print("Error logging in. \nReason:", response_data['MSG'])
    else:
        print("Error logging in. Status code:", response.status_code)
        
def validate_session(jwt):
    """
    A function to validate a session using the provided JWT token.

    Parameters:
    - jwt: str, the JWT token to be used for session validation.

    Returns:
    - None
    """
    login_url = os.path.join(BASE_URL, "bhoonidhi/LoginServlet")
    payload = {
        "action": "VALIDATE_SESSION",
    }
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "token": jwt
    }
    response = requests.post(login_url, data=json.dumps(payload), headers=headers)
    if response.status_code == 200:
        print("Session validation successful")
    else:
        print("Error logging in. Status code:", response.status_code)
        
def save_session_info(session_info):
    """
    Save the session information to a file.

    Parameters:
    - session_info: dict, the session information to be saved.

    Return:
    - None
    """
    home_dir = os.path.expanduser("~")
    session_file = os.path.join(home_dir, ".bhoonidhi_session")
    with open(session_file, "w") as f:
        json.dump(session_info, f)

def load_session_info():
    """
    Load the session information from a file.

    Returns:
        dict: A dictionary containing the session information. The dictionary has the following keys:
            - jwt (str or None): The JSON Web Token (JWT) for the session.
            - userId (str or None): The ID of the user associated with the session.
            - user_email (str or None): The email address of the user associated with the session.
            - username (str or None): The username of the user associated with the session.

    If the session file does not exist, returns a dictionary with all values set to None.
    """
    home_dir = os.path.expanduser("~")
    session_file = os.path.join(home_dir, ".bhoonidhi_session")
    if os.path.exists(session_file):
        with open(session_file, "r") as f:
            return json.load(f)
    return {"jwt": None, "userId": None, "user_email": None, "username": None}