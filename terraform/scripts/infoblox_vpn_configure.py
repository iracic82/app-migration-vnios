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
    interpolated = re.sub(r'\$\{(\w+)\}', replace_env, raw_yaml)
    return yaml.safe_load(interpolated)

class InfobloxVPNDeployer:
    def __init__(self, config_file):
        self.config = load_config_with_env(config_file)
        self.base_url = self.config["base_url"]
        self.email = self.config["email"]
        self.password = self.config["password"]
        self.sandbox_id_file = self.config["sandbox_id_file"]
        self.jwt = None
        self.headers = {}

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
        print("✅ Authenticated.")

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
        time.sleep(5)

    def deploy_vpn(self):
        url = f"{self.base_url}/api/universalinfra/v1/consolidated/configure"
        payload = self.config["vpn_payload"]
        r = requests.post(url, headers=self.headers, json=payload)

        try:
            r.raise_for_status()
        except requests.exceptions.HTTPError as e:
            print("❌ Deployment failed:")
            print(f"Status Code: {r.status_code}")
            print(f"Response: {r.text}")
            raise e  # re-raise to preserve traceback

if __name__ == "__main__":
    client = InfobloxVPNDeployer("config_vpn.yaml")
    client.authenticate()
    client.switch_account()
    client.deploy_vpn()
