#!/usr/bin/env python3

import os
import boto3
import sys
from datetime import datetime

# ---------------------------
# Setup logging
# ---------------------------
log_file = "dns_log_gm.txt"
timestamp = datetime.utcnow().isoformat()
log_lines = [f"\n--- Infoblox GM DNS Record Log [{timestamp}] ---\n"]

def log(message):
    print(message)
    log_lines.append(message + "\n")

# ---------------------------
# AWS credentials and config
# ---------------------------
aws_access_key_id = os.getenv("DEMO_AWS_ACCESS_KEY_ID")
aws_secret_access_key = os.getenv("DEMO_AWS_SECRET_ACCESS_KEY")
region = os.getenv("DEMO_AWS_REGION", "us-east-1")
hosted_zone_id = os.getenv("DEMO_HOSTED_ZONE_ID")
gm_ip = os.getenv("GM_IP")

if not aws_access_key_id or not aws_secret_access_key or not hosted_zone_id:
    log("❌ ERROR: Missing AWS credentials or Hosted Zone ID in environment")
    sys.exit(1)

if not gm_ip:
    log("❌ ERROR: GM_IP is not set in the environment")
    sys.exit(1)

# ---------------------------
# Set A record for Infoblox GM
# ---------------------------
prefix = os.getenv("INSTRUQT_PARTICIPANT_ID", "").strip()
fqdn = f"{prefix + '-' if prefix else ''}infoblox-app.iracictechguru.com."

log(f"➡️  Creating A record: {fqdn} -> {gm_ip}")
try:
    session = boto3.Session(
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        region_name=region
    )
    route53 = session.client("route53")

    response = route53.change_resource_record_sets(
        HostedZoneId=hosted_zone_id,
        ChangeBatch={
            "Comment": "Upsert A record for Infoblox GM",
            "Changes": [
                {
                    "Action": "UPSERT",
                    "ResourceRecordSet": {
                        "Name": fqdn,
                        "Type": "A",
                        "TTL": 300,
                        "ResourceRecords": [{"Value": gm_ip}]
                    }
                }
            ]
        }
    )

    status = response['ChangeInfo']['Status']
    log(f"✅  A record created: {fqdn} -> {gm_ip}")
    log(f"📡  Change status: {status}")

except Exception as e:
    log(f"❌ Failed to create A record for {fqdn}: {e}")
    sys.exit(1)

# ---------------------------
# Write log to file
# ---------------------------
with open(log_file, "a") as f:
    f.writelines(log_lines)

log(f"📄 Log written to {log_file}")
