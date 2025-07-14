import os
import json
import requests

class InfobloxSession:
    def __init__(self):
        self.base_url = "https://csp.infoblox.com"
        self.email = os.getenv("INFOBLOX_EMAIL")
        self.password = os.getenv("INFOBLOX_PASSWORD")
        self.jwt = None
        self.session = requests.Session()
        self.headers = {"Content-Type": "application/json"}

    def _auth_headers(self):
        return {
            "Authorization": f"Bearer {self.jwt}",
            "Content-Type": "application/json"
        }

    def _read_file(self, filename):
        with open(filename, "r") as f:
            return f.read().strip()

    def _save_to_file(self, filename, content):
        with open(filename, "w") as f:
            f.write(content)

    def login(self):
        url = f"{self.base_url}/v2/session/users/sign_in"
        payload = {"email": self.email, "password": self.password}
        response = self.session.post(url, headers=self.headers, json=payload)
        response.raise_for_status()
        self.jwt = response.json().get("jwt")
        print("✅ Logged in")

    def switch_account(self):
        sandbox_id = self._read_file("sandbox_id.txt")
        url = f"{self.base_url}/v2/session/account_switch"
        payload = {"id": f"identity/accounts/{sandbox_id}"}
        response = self.session.post(url, headers=self._auth_headers(), json=payload)
        response.raise_for_status()
        self.jwt = response.json().get("jwt")
        print(f"✅ Switched to sandbox: {sandbox_id}")

    def get(self, endpoint):
        url = f"{self.base_url}{endpoint}"
        response = self.session.get(url, headers=self._auth_headers())
        response.raise_for_status()
        return response.json()

    def post(self, endpoint, payload):
        url = f"{self.base_url}{endpoint}"
        response = self.session.post(url, headers=self._auth_headers(), json=payload)
        if response.status_code != 200:
            print(f"❌ Failed POST to {url}")
            print(f"Status Code: {response.status_code}")
            print(f"Response Text:\n{response.text}")
            print(f"Payload Sent:\n{json.dumps(payload, indent=2)}")
        response.raise_for_status()
        return response.json()


class TunnelUpdater:
    def __init__(self, session: InfobloxSession):
        self.session = session
        self.tunnel_file = "aws_tunnels.txt"

    def get_first_tunnel_ip(self):
        with open(self.tunnel_file, "r") as f:
            return f.readline().strip().split(",")[-1].strip()

    def build_access_location_update(self, endpoint, access_loc, tunnel_ip):
        pri_tunnel = access_loc["tunnel_configs"][0]
        sec_tunnel = access_loc["tunnel_configs"][1]

        pri_physical = pri_tunnel["physical_tunnels"][0]
        sec_physical = sec_tunnel["physical_tunnels"][0]

        access_location_payload = {
            "endpoint_id": endpoint["id"].split("/")[-1],
            "id": access_loc["id"].split("/")[-1],
            "routing_type": "dynamic",
            "type": "Cloud VPN",
            "name": access_loc["name"],
            "cloud_type": access_loc["cloud_type"],
            "cloud_region": access_loc["cloud_region"],
            "lan_subnets": [],
            "tunnel_configs": [
                {
                    "id": pri_tunnel["id"],
                    "name": pri_tunnel["name"],
                    "physical_tunnels": [
                        {
                            "path": pri_physical["path"],
                            "credential_id": pri_physical["credential_id"],
                            "index": 0,
                            "access_ip": tunnel_ip,
                            "bgp_configs": [
                                {
                                    "id": pri_physical["bgp_configs"][0]["id"],
                                    "asn": 64512,
                                    "hop_limit": 2,
                                    "cloud_cidr": pri_physical["bgp_configs"][0]["cloud_cidr"]
                                }
                            ]
                        }
                    ]
                },
                {
                    "id": sec_tunnel["id"],
                    "name": sec_tunnel["name"],
                    "physical_tunnels": [
                        {
                            "path": sec_physical["path"],
                            "credential_id": sec_physical["credential_id"],
                            "index": 0,
                            "access_ip": sec_physical["access_ip"],
                            "bgp_configs": [
                                {
                                    "id": sec_physical["bgp_configs"][0]["id"],
                                    "asn": 64512,
                                    "hop_limit": 2,
                                    "cloud_cidr": sec_physical["bgp_configs"][0]["cloud_cidr"]
                                }
                            ]
                        }
                    ]
                }
            ]
        }

        endpoint_payload = {
            "id": endpoint["id"].split("/")[-1],
            "name": endpoint["name"],
            "size": endpoint["size"],
            "service_location": endpoint["service_location"],
            "service_ip": endpoint["service_ip"],
            "neighbour_ips": endpoint["neighbour_ips"],
            "preferred_provider": endpoint["preferred_provider"],
            "tags": {},
            "routing_type": endpoint["routing_type"],
            "routing_config": endpoint["routing_config"]
        }

        return {
            "universal_service": {
                "operation": "UPDATE",
                "id": endpoint["universal_service_id"],
                "name": "Demo",
                "description": "",
                "capabilities": [{"type": "dns", "profile_id": ""}],
                "tags": {}
            },
            "access_locations": {
                "create": [],
                "update": [access_location_payload],
                "delete": []
            },
            "endpoints": {
                "create": [],
                "update": [endpoint_payload],
                "delete": []
            },
            "credentials": {"create": [], "update": []},
            "locations": {"create": [], "update": []}
        }

    def update_primary_tunnel_ip(self):
        tunnel_ip = self.get_first_tunnel_ip()
        print(f"🛰️ Using Tunnel 1 IP: {tunnel_ip}")

        endpoint_data = self.session.get("/api/universalinfra/v1/endpoints/")
        access_data = self.session.get("/api/universalinfra/v1/accesslocations")

        endpoint = endpoint_data["result"]
        access_loc = access_data["results"][0]

        payload = self.build_access_location_update(endpoint, access_loc, tunnel_ip)
        response = self.session.post("/api/universalinfra/v1/consolidated/configure", payload)
        print("🚀 Successfully updated primary tunnel IP!")


# === ENTRY POINT ===
if __name__ == "__main__":
    session = InfobloxSession()
    session.login()
    session.switch_account()

    updater = TunnelUpdater(session)
    updater.update_primary_tunnel_ip()
