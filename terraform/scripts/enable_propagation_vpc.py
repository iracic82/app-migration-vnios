import boto3

REGION = "eu-central-1"
ROUTE_TAG = "public-rt"
VGW_TAG = "infoblox-lab-vgw"

ec2 = boto3.client("ec2", region_name=REGION)

def get_route_table_id_by_name(name):
    resp = ec2.describe_route_tables(
        Filters=[
            {"Name": "tag:Name", "Values": [name]}
        ]
    )
    if not resp["RouteTables"]:
        raise Exception(f"No Route Table found with tag Name={name}")
    return resp["RouteTables"][0]["RouteTableId"]

def get_vgw_id_by_name(name):
    resp = ec2.describe_vpn_gateways(
        Filters=[
            {"Name": "tag:Name", "Values": [name]}
        ]
    )
    if not resp["VpnGateways"]:
        raise Exception(f"No VGW found with tag Name={name}")
    return resp["VpnGateways"][0]["VpnGatewayId"]

def is_propagation_enabled(route_table_id, vgw_id):
    resp = ec2.describe_route_tables(RouteTableIds=[route_table_id])
    for vg in resp["RouteTables"][0].get("PropagatingVgws", []):
        if vg.get("GatewayId") == vgw_id:
            return True
    return False

def enable_propagation():
    rt_id = get_route_table_id_by_name(ROUTE_TAG)
    vgw_id = get_vgw_id_by_name(VGW_TAG)

    if is_propagation_enabled(rt_id, vgw_id):
        print(f"ℹ️ Propagation already enabled for {vgw_id} on {rt_id}")
    else:
        print(f"🔄 Enabling propagation for Route Table {rt_id} and VGW {vgw_id}...")
        ec2.enable_vgw_route_propagation(RouteTableId=rt_id, GatewayId=vgw_id)
        print("✅ Route propagation enabled.")

if __name__ == "__main__":
    enable_propagation()
