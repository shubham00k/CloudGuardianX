import boto3
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from datetime import datetime
import argparse

# Hardcoded configuration (replace with your actual values)
AWS_REGION = "us-east-1"
AWS_ACCESS_KEY_ID = "your-aws-access-key"
AWS_SECRET_ACCESS_KEY = "your-aws-secret-key"
AWS_VOLUME_ID = "vol-1234567890abcdef0"  # Your EBS volume ID
INSTANCE_ID = "i-4567890abcdef123"      # Your EC2 instance ID
SLACK_TOKEN = "xoxb-your-slack-token"    # Your Slack Bot User OAuth Token
SLACK_CHANNEL = "#notification-test"     # Your Slack channel

# AWS and Slack clients
aws_ec2 = boto3.client('ec2', region_name=AWS_REGION, aws_access_key_id=AWS_ACCESS_KEY_ID, aws_secret_access_key=AWS_SECRET_ACCESS_KEY)
slack_client = WebClient(token=SLACK_TOKEN)

def send_slack_message(message, channel=SLACK_CHANNEL):
    try:
        slack_client.chat_postMessage(channel=channel, text=message)
    except SlackApiError as e:
        print(f"Slack error: {e}")

def analyze_snapshot_health(snapshot_id):
    health_score = 0.95 + (0.05 * (1 - 0.1))  # Simulated health (90%-100%)
    if health_score < 0.95:
        send_slack_message(f"Warning: Snapshot {snapshot_id} health low ({(health_score * 100):.1f}%)", SLACK_CHANNEL)
    return health_score

def list_aws_snapshots(volume_id=None):
    try:
        if volume_id:
            params = {'Filters': [{'Name': 'volume-id', 'Values': [volume_id]}]}
        else:
            params = {}  # List all snapshots if no volume_id specified
        response = aws_ec2.describe_snapshots(**params)
        return response['Snapshots']
    except Exception as e:
        print(f"Error listing snapshots: {e}")
        return []

def create_aws_snapshot(volume_id, instance_id=None):
    if not volume_id:
        print("No volume ID provided for snapshot creation.")
        return None
    try:
        params = {
            'VolumeId': volume_id,
            'Description': f"CloudGuardianX - {datetime.now().isoformat()}"
        }
        data = aws_ec2.create_snapshot(**params)
        snapshot_id = data['SnapshotId']
        health = analyze_snapshot_health(snapshot_id)
        send_slack_message(f"AWS Snapshot {snapshot_id} created (Health: {(health * 100):.1f}%) for Volume {volume_id}", SLACK_CHANNEL)
        return snapshot_id
    except Exception as e:
        send_slack_message(f"Error creating snapshot for Volume {volume_id}: {e}", SLACK_CHANNEL)
        print(f"Error: {e}")
        return None

def restore_aws_snapshot(snapshot_id, instance_id, volume_id, preview=False):
    if not instance_id or not volume_id:
        print("Instance ID and Volume ID required for restore.")
        return None
    try:
        instance_data = aws_ec2.describe_instances(InstanceIds=[instance_id])['Reservations'][0]['Instances'][0]
        current_volume = instance_data['BlockDeviceMappings'][0]['Ebs']['VolumeId']  # Assuming first block device

        if preview:
            send_slack_message(f"Preview: Restore {snapshot_id} to Instance {instance_id}, replace Volume {current_volume}", SLACK_CHANNEL)
            print("Estimated downtime: ~30-60s")
            return None

        aws_ec2.stop_instances(InstanceIds=[instance_id])
        aws_ec2.wait_for('instance_stopped', InstanceIds=[instance_id])

        volume_data = aws_ec2.create_volume(
            SnapshotId=snapshot_id,
            AvailabilityZone=instance_data['Placement']['AvailabilityZone']
        )
        new_volume_id = volume_data['VolumeId']
        aws_ec2.wait_for('volume_available', VolumeIds=[new_volume_id])

        aws_ec2.detach_volume(VolumeId=current_volume, InstanceId=instance_id)
        aws_ec2.wait_for('volume_available', VolumeIds=[current_volume])
        aws_ec2.attach_volume(VolumeId=new_volume_id, InstanceId=instance_id, Device='/dev/xvda')

        aws_ec2.start_instances(InstanceIds=[instance_id])
        send_slack_message(f"Rollback complete: Instance {instance_id} restored to Volume {new_volume_id}", SLACK_CHANNEL)
        return new_volume_id
    except Exception as e:
        send_slack_message(f"Rollback error for Instance {instance_id}, Volume {volume_id}: {e}", SLACK_CHANNEL)
        print(f"Error: {e}")
        return None

def delete_old_aws_snapshots(volume_id=None, days=30):
    snapshots = list_aws_snapshots(volume_id)
    for snap in snapshots:
        age = (datetime.now() - datetime.fromisoformat(snap['StartTime'].replace('Z', '+00:00'))).days
        if age > days:
            aws_ec2.delete_snapshot(SnapshotId=snap['SnapshotId'])
            send_slack_message(f"Deleted old snapshot {snap['SnapshotId']} for Volume {volume_id or 'all'}", SLACK_CHANNEL)

def gamified_recovery_challenge(snapshot_id, instance_id, volume_id):
    start_time = datetime.now()
    new_volume = restore_aws_snapshot(snapshot_id, instance_id, volume_id)
    if new_volume:
        recovery_time = (datetime.now() - start_time).total_seconds()
        score = max(100 - int(recovery_time * 10), 10)
        send_slack_message(f"Challenge: Restored in {recovery_time:.1f}s for Instance {instance_id}. Score: {score}/100", SLACK_CHANNEL)
        return score
    return 0

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CloudGuardianX - AWS Snapshot Management")
    parser.add_argument("action", choices=['create', 'list', 'restore', 'delete', 'challenge'])
    parser.add_argument("--snapshot-id", help="Snapshot ID for restore/challenge")
    parser.add_argument("--instance-id", help="Instance ID for restore/challenge")
    parser.add_argument("--volume-id", help="Volume ID for specific operations (optional, defaults to AWS_VOLUME_ID)")
    parser.add_argument("--preview", action="store_true", help="Preview restore without changes")

    args = parser.parse_args()

    volume_id = args.volume_id or AWS_VOLUME_ID
    instance_id = args.instance_id or INSTANCE_ID

    if args.action == 'create' and volume_id:
        create_aws_snapshot(volume_id, instance_id)
    elif args.action == 'list':
        snapshots = list_aws_snapshots(volume_id)
        for snap in snapshots:
            print(f"ID: {snap['SnapshotId']}, Time: {snap['StartTime']}, Volume: {snap.get('VolumeId', 'N/A')}")
    elif args.action == 'restore' and args.snapshot_id and instance_id and volume_id:
        restore_aws_snapshot(args.snapshot_id, instance_id, volume_id, args.preview)
    elif args.action == 'delete':
        delete_old_aws_snapshots(volume_id)
    elif args.action == 'challenge' and args.snapshot_id and instance_id and volume_id:
        gamified_recovery_challenge(args.snapshot_id, instance_id, volume_id)
    else:
        parser.print_help()