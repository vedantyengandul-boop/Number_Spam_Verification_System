import os
import requests
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("ABSTRACT_API_KEY")

phone_number = "+919699398262"

url = "https://phoneintelligence.abstractapi.com/v1"

params = {
    "api_key": api_key,
    "phone": phone_number
}

response = requests.get(url, params=params)

print("Status Code:", response.status_code)
print("Response:")
print(response.json())