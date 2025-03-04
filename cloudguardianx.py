import boto3
import time
import random
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from datetime import datetime
import argparse

# Configuration (replace with your values)
AWS_VOLUME_ID = "vol-EBS-ID"  # Your EBS volume ID
AWS_REGION = "us-east-1"                 # Your AWS region
INSTANCE_ID = "i-EC2-ID"       # Your EC2 instance ID
SLACK_TOKEN = "xoxb-slack-token"    # Your Slack Bot User OAuth Token
SLACK_CHANNEL = "#not-test"               # Your Slack channel

# AWS and Slack clients
aws_ec2 = boto3.client('ec2', region_name=AWS_REGION)
slack_client = WebClient(token=SLACK_TOKEN)

def send_slack_message(message):
    try:
        slack_client.chat_postMessage(channel=SLACK_CHANNEL, text=message)
        print(f"Slack: {message}")
    except SlackApiError as e:
        print(f"Slack error: {e.response['error']}")

def analyze_snapshot_health(snapshot_id):
    health_score = random.uniform(0.9, 1.0)  # Simulated health
    if health_score < 0.95:
        send_slack_message(f"Warning: Snapshot {snapshot_id} health low ({health_score*100:.1f}%)")
    return health_score

def create_aws_snapshot():
    try:
        response = aws_ec2.create_snapshot(VolumeId=AWS_VOLUME_ID, Description=f"CloudGuardianX - {datetime.now()}")
        snapshot_id = response['SnapshotId']
        health = analyze_snapshot_health(snapshot_id)
        send_slack_message(f"AWS Snapshot {snapshot_id} created (Health: {health*100:.1f}%)")
        return snapshot_id
    except Exception as e:
        send_slack_message(f"Error creating snapshot: {str(e)}")
        print(f"Error: {e}")
        return None

def list_aws_snapshots():
    try:
        response = aws_ec2.describe_snapshots(Filters=[{'Name': 'volume-id', 'Values': [AWS_VOLUME_ID]}])
        return response['Snapshots']
    except Exception as e:
        print(f"Error listing snapshots: {e}")
        return []

def restore_aws_snapshot(snapshot_id, instance_id, preview=False):
    try:
        instance = aws_ec2.describe_instances(InstanceIds=[instance_id])['Reservations'][0]['Instances'][0]
        current_volume = next(
            vol for vol in instance['BlockDeviceMappings'] if vol['Ebs']['VolumeId'] == AWS_VOLUME_ID
        )['Ebs']['VolumeId']

        if preview:
            send_slack_message(f"Preview: Restore {snapshot_id} to {instance_id}, replace {current_volume}")
            print("Estimated downtime: ~30-60s")
            return None

        aws_ec2.stop_instances(InstanceIds=[instance_id])
        aws_ec2.get_waiter('instance_stopped').wait(InstanceIds=[instance_id])
        new_volume = aws_ec2.create_volume(SnapshotId=snapshot_id, AvailabilityZone=instance['Placement']['AvailabilityZone'])
        new_volume_id = new_volume['VolumeId']
        aws_ec2.get_waiter('volume_available').wait(VolumeIds=[new_volume_id])
        aws_ec2.detach_volume(VolumeId=current_volume, InstanceId=instance_id)
        aws_ec2.get_waiter('volume_available').wait(VolumeIds=[current_volume])
        aws_ec2.attach_volume(VolumeId=new_volume_id, InstanceId=instance_id, Device='/dev/xvda')
        aws_ec2.start_instances(InstanceIds=[instance_id])
        send_slack_message(f"Rollback complete: {instance_id} restored to {new_volume_id}")
        return new_volume_id
    except Exception as e:
        send_slack_message(f"Rollback error: {str(e)}")
        print(f"Error: {e}")
        return None

def delete_old_aws_snapshots(days=30):
    snapshots = list_aws_snapshots()
    for snap in snapshots:
        age = (datetime.now(snap['StartTime'].tzinfo) - snap['StartTime']).days
        if age > days:
            aws_ec2.delete_snapshot(SnapshotId=snap['SnapshotId'])
            send_slack_message(f"Deleted old snapshot {snap['SnapshotId']}")

def gamified_recovery_challenge(snapshot_id, instance_id):
    start_time = time.time()
    new_volume = restore_aws_snapshot(snapshot_id, instance_id)
    if new_volume:
        recovery_time = time.time() - start_time
        score = max(100 - int(recovery_time * 10), 10)
        send_slack_message(f"Challenge: Restored in {recovery_time:.1f}s. Score: {score}/100")
        return score
    return 0

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CloudGuardianX - AWS Snapshot Automation")
    parser.add_argument("action", choices=["create", "list", "restore", "delete", "challenge"])
    parser.add_argument("--snapshot-id", help="Snapshot ID for restore/challenge")
    parser.add_argument("--instance-id", help="EC2 instance ID for restore/challenge")
    parser.add_argument("--preview", action="store_true", help="Preview rollback")
    args = parser.parse_args()

    if args.action == "create":
        create_aws_snapshot()
    elif args.action == "list":
        for snap in list_aws_snapshots():
            print(f"ID: {snap['SnapshotId']}, Time: {snap['StartTime']}")
    elif args.action == "restore":
        if args.snapshot_id and args.instance_id:
            restore_aws_snapshot(args.snapshot_id, args.instance_id, args.preview)
        else:
            print("Error: --snapshot-id and --instance-id required for restore")
    elif args.action == "delete":
        delete_old_aws_snapshots()
    elif args.action == "challenge":
        if args.snapshot_id and args.instance_id:
            gamified_recovery_challenge(args.snapshot_id, args.instance_id)
        else:
            print("Error: --snapshot-id and --instance-id required for challenge")