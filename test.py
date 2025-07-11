import requests

import config

url = "https://games-test.datsteam.dev/api/arena"
headers = {
    "accept": "application/json",
    "X-Auth-Token": config.TOKEN
}

response = requests.get(url, headers=headers)

# Вывод ответа
print("Status Code:", response.status_code)
print("Response Body:", response.json())