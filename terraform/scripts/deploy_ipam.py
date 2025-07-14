import os
import re
import yaml
import json
import requests
import time

def load_config_with_env(file_path):
    with open(file_path, "r") as f:
        raw_yaml = f.read()

    def replace_env(match):
        env_var = match.group(1)
        return os.environ.get(env_var, f"<MISSING:{env_var}>")

    interpolated_yaml = re.sub(r'\$\{(\w+)\}', replace_env, raw_yaml)
    return yaml.safe_load(interpolated_yaml)

class InfobloxCSPClient:
    def __init__(self, config_file):
        config = load_config_with_env(config_file)

        self.base_url = config['base_url']
        self.email = config['email']
        self.password = config['password']
        self.sandbox_id_file = config['sandbox_id_file']
        self.realm = config['realm']
        self.blocks = config['blocks']
        self.jwt = None
        self.headers = {}
        self.output = {
            "realm": {},
            "blocks": []
        }

    def authenticate(self):
        url = f"{self.base_url}/v2/session/users/sign_in"
        payload = {"email": self.email, "password": self.password}
        r = requests.post(url, json=payload)
        r.raise_for_status()
        self.jwt = r.json()["jwt"]
        self.headers = {
            "Authorization": f"Bearer {self.jwt}",
            "Content-Type": "application/json"
        }
        print("✅ Logged in and JWT obtained.")

    def switch_account(self):
        with open(self.sandbox_id_file, "r") as f:
            sandbox_id = f.read().strip()
        url = f"{self.base_url}/v2/session/account_switch"
        payload = {"id": f"identity/accounts/{sandbox_id}"}
        r = requests.post(url, headers=self.headers, json=payload)
        r.raise_for_status()
        self.jwt = r.json()["jwt"]
        self.headers["Authorization"] = f"Bearer {self.jwt}"
        print(f"🔁 Switched to sandbox account {sandbox_id}")

        # ⏱️ Wait to avoid permission lag
        time.sleep(10)  # Add 10 seconds wait to be safe

    def create_realm(self):
        url = f"{self.base_url}/api/ddi/v1/federation/federated_realm"
        payload = {
            "name": self.realm["name"],
            "comment": self.realm["comment"],
            "tags": self.realm["tags"],
            "utilization": 0
        }
        r = requests.post(url, headers=self.headers, json=payload)
        r.raise_for_status()
        result = r.json()["result"]
        realm_id = result["id"]
        self.output["realm"] = result
        print(f"🏗️  Created federated realm: {result['name']} → ID: {realm_id}")
        return realm_id

    def create_blocks(self, realm_id):
        url = f"{self.base_url}/api/ddi/v1/federation/federated_block"
        for block in self.blocks:
            payload = {
                "name": block["name"],
                "address": block["address"],
                "cidr": block["cidr"],
                "comment": block["comment"],
                "federated_realm": realm_id,
                "tags": block["tags"],
                "utilization": 0
            }
            r = requests.post(url, headers=self.headers, json=payload)
            r.raise_for_status()
            result = r.json()["result"]
            self.output["blocks"].append(result)
            print(f"🧱 Created federated block: {block['name']}")

    def save_output(self, filename="federation_output.json"):
        with open(filename, "w") as f:
            json.dump(self.output, f, indent=2)
        print(f"📄 Output saved to {filename}")

if __name__ == "__main__":
    client = InfobloxCSPClient("config.yaml")
    client.authenticate()
    client.switch_account()
    realm_id = client.create_realm()
    client.create_blocks(realm_id)
    client.save_output()
