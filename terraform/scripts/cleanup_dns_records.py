#!/usr/bin/env python3

import os
import boto3
import sys
from datetime import datetime, timezone

# ---------------------------
# Setup logging
# ---------------------------
log_file = "dns_record_cleanup_log.txt"
timestamp = datetime.now(timezone.utc).isoformat()
log_lines = [f"\n--- DNS Record Deletion Log [{timestamp}] ---\n"]

def log(message):
    print(message)
    log_lines.append(message + "\n")

# ---------------------------
# AWS credentials from env vars
# ---------------------------
aws_access_key_id = os.getenv("DEMO_AWS_ACCESS_KEY_ID")
aws_secret_access_key = os.getenv("DEMO_AWS_SECRET_ACCESS_KEY")
region = os.getenv("DEMO_AWS_REGION", "us-east-1")
hosted_zone_id = os.getenv("DEMO_HOSTED_ZONE_ID")

if not aws_access_key_id or not aws_secret_access_key or not hosted_zone_id:
    log("❌ ERROR: AWS credentials or Hosted Zone ID not set")
    sys.exit(1)

# ---------------------------
# Required env vars
# ---------------------------
participant_id = os.getenv("INSTRUQT_PARTICIPANT_ID")
dc1_ip = os.getenv("DC1_IP")

if not participant_id or not dc1_ip:
    log("❌ ERROR: INSTRUQT_PARTICIPANT_ID and DC1_IP must be set")
    sys.exit(1)

fqdn = f"{participant_id}-client.iracictechguru.com."

# ---------------------------
# Create boto3 session
# ---------------------------
session = boto3.Session(
    aws_access_key_id=aws_access_key_id,
    aws_secret_access_key=aws_secret_access_key,
    region_name=region
)

route53 = session.client("route53")

# ---------------------------
# Delete the A record
# ---------------------------
log(f"🗑️  Deleting A record: {fqdn} -> {dc1_ip}")
try:
    response = route53.change_resource_record_sets(
        HostedZoneId=hosted_zone_id,
        ChangeBatch={
            "Comment": f"Delete A record for {fqdn}",
            "Changes": [
                {
                    "Action": "DELETE",
                    "ResourceRecordSet": {
                        "Name": fqdn,
                        "Type": "A",
                        "TTL": 300,
                        "ResourceRecords": [{"Value": dc1_ip}]
                    }
                }
            ]
        }
    )
    status = response['ChangeInfo']['Status']
    log(f"✅  Deleted: {fqdn} -> {dc1_ip}")
    log(f"📡  Change status: {status}")
except route53.exceptions.InvalidChangeBatch as e:
    log(f"⚠️  Record {fqdn} may not exist or already deleted: {e}")
except Exception as e:
    log(f"❌ Failed to delete A record {fqdn}: {e}")
    sys.exit(1)

# ---------------------------
# Write cleanup log
# ---------------------------
with open(log_file, "a") as f:
    f.writelines(log_lines)

log(f"📄 Cleanup log written to {log_file}")
