import json
import os

from staxapp.config import Config
from staxapp.openapi import StaxClient

Config.access_key = os.getenv("STAX_ACCESS_KEY")
Config.secret_key = os.getenv("STAX_SECRET_KEY")

networks = StaxClient("networking")

body = {
    "Name": "my-hub",
    "AccountId": "<account_uuid>",
    "Region": "ap-southeast-2",
    "Cidr": "10.128.0.0/22",
    "CreateNatGateway": False,
    "CreateInternetGateway": False,
}
response = networks.CreateHub(**body)
print(json.dumps(response, indent=4, sort_keys=True))
