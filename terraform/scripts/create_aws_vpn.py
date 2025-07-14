import boto3
import time
import sys

# Constants
CUSTOMER_GATEWAY_ASN = 65500
VGW_TAG_KEY = "Name"
VGW_TAG_VALUE = "infoblox-lab-vgw"
PRE_SHARED_KEY = "InfobloxLab.2025"
CNAME_FILE = "cnames.txt"

TUNNELS = [
    {"name": "vpn1", "ip": None, "cidr": "169.254.21.0/30"},
    {"name": "vpn2", "ip": None, "cidr": "169.254.22.0/30"}
]

def load_cnames(filename=CNAME_FILE):
    try:
        with open(filename, "r") as f:
            lines = [line.strip() for line in f if line.strip()]
        if len(lines) < 2:
            raise ValueError("❌ cname.txt must contain at least 2 valid IPs.")
        TUNNELS[0]["ip"] = lines[0]
        TUNNELS[1]["ip"] = lines[1]
        print(f"📥 Loaded CGW IPs: {lines}")
        return TUNNELS
    except FileNotFoundError:
        sys.exit(f"❌ File not found: {filename}")
    except Exception as e:
        sys.exit(str(e))

def find_vgw_id(ec2):
    response = ec2.describe_vpn_gateways(
        Filters=[{
            "Name": f"tag:{VGW_TAG_KEY}",
            "Values": [VGW_TAG_VALUE]
        }]
    )
    gateways = response.get("VpnGateways", [])
    if not gateways:
        sys.exit(f"❌ No VGW found with tag {VGW_TAG_KEY}={VGW_TAG_VALUE}")
    vgw_id = gateways[0]["VpnGatewayId"]
    print(f"✅ Found VGW ID: {vgw_id}")
    return vgw_id

def main():
    session = boto3.Session(region_name="eu-central-1")
    ec2 = session.client("ec2")

    tunnels = load_cnames()
    vgw_id = find_vgw_id(ec2)

    for tunnel in tunnels:
        print(f"🔧 Creating resources for {tunnel['name']}...")

        # 1. Create CGW
        cgw_resp = ec2.create_customer_gateway(
            BgpAsn=CUSTOMER_GATEWAY_ASN,
            PublicIp=tunnel["ip"],
            Type="ipsec.1",
            TagSpecifications=[{
                "ResourceType": "customer-gateway",
                "Tags": [{"Key": "Name", "Value": f"{tunnel['name']}-cgw"}]
            }]
        )
        cgw_id = cgw_resp["CustomerGateway"]["CustomerGatewayId"]
        print(f"✅ Created CGW: {cgw_id} for {tunnel['ip']}")

        # 2. Create VPN Connection
        vpn_resp = ec2.create_vpn_connection(
            CustomerGatewayId=cgw_id,
            Type="ipsec.1",
            VpnGatewayId=vgw_id,
            Options={
                "StaticRoutesOnly": False,
                "TunnelOptions": [{
                    "TunnelInsideCidr": tunnel["cidr"],
                    "PreSharedKey": PRE_SHARED_KEY,
                    "StartupAction": "start"
                }]
            },
            TagSpecifications=[{
                "ResourceType": "vpn-connection",
                "Tags": [{"Key": "Name", "Value": f"{tunnel['name']}-vpn"}]
            }]
        )
        vpn_id = vpn_resp["VpnConnection"]["VpnConnectionId"]
        print(f"🚀 Created VPN Connection: {vpn_id} → CGW: {cgw_id}")

        time.sleep(1)

if __name__ == "__main__":
    main()
