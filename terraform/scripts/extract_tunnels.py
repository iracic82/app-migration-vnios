import boto3

OUTPUT_FILE = "aws_tunnels.txt"

def extract_tunnel_ips():
    ec2 = boto3.client("ec2", region_name="eu-central-1")
    vpn_connections = ec2.describe_vpn_connections()["VpnConnections"]

    with open(OUTPUT_FILE, "w") as f:
        for vpn in vpn_connections:
            vpn_id = vpn["VpnConnectionId"]
            tunnels = vpn.get("Options", {}).get("TunnelOptions", [])
            for idx, tunnel in enumerate(tunnels, start=1):
                outside_ip = tunnel.get("OutsideIpAddress")
                if outside_ip:
                    line = f"{vpn_id}, Tunnel {idx}, {outside_ip}\n"
                    f.write(line)
                    print(f"✅ {line.strip()}")

    print(f"\n📄 Tunnel IPs saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    extract_tunnel_ips()
