import requests
import json
from colorama import init, Fore, Style
import os
from dotenv import load_dotenv
load_dotenv()

init(autoreset=True)

API_KEY = os.getenv("API_KEY")

headers = {
    "Authorization": f"Bearer {API_KEY}"
}

with open("servicestotoggle.json") as f:
    services = json.load(f)

for service in services:
    service_id = service["id"]
    url = f"https://api.render.com/v1/services/{service_id}/start"

    response = requests.post(url, headers=headers)

    if response.status_code == 200:
        print(f"✅ Started: {service_id}")
    else:
        print(f"❌ Failed to start {service_id}: {response.status_code} - {response.text}")
        if response.status_code == 202:
            print(Fore.YELLOW + Style.BRIGHT + '[WARN]     ' + Fore.RESET + Style.RESET_ALL + 'Request accepted but not completed — try again after a few seconds.')
