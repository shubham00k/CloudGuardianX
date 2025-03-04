# CloudGuardianX - AWS Snapshot Automation Suite
A disaster recovery tool for a single AWS EC2 instance/EBS volume, with dynamic snapshots, rollback, and an animated dashboard with happy kawaii clouds.

## Features
- Automated AWS snapshot creation, listing, deletion, and full rollback for one EC2 instance/EBS volume.
- Snapshot health analysis, gamified recovery challenge, real-time Slack alerts.
- Expanded, animated dashboard (fade, bounce, slide, progress) with increased snapshot visibility (up to 12+ items), happy kawaii clouds on both sides (floating, 300x375px).
- Dockerized, available on Docker Hub for easy deployment.

## Setup
1. Install Python 3.9+, AWS CLI, Docker on Ubuntu.
2. Run `pip3 install -r requirements.txt`.
3. Update config in `cloudguardianx.py` with AWS and Slack details (hardcoded or via environment variables).
4. Test: `python3 cloudguardianx.py create`.

## Docker
- Pull the Docker image from Docker Hub: `docker pull shubham00k/cloudguardianx:latest`
- Run: `docker run -p 5000:5000 -e AWS_ACCESS_KEY_ID=... -e AWS_SECRET_ACCESS_KEY=... shubham00k/cloudguardianx:latest`
- Access the dashboard at `http://localhost:5000`.

## Usage
- `python3 cloudguardianx.py restore --snapshot-id snap-123 --instance-id i-456` - Rollback instance.
- `python3 dashboard.py` - View dashboard at `localhost:5000`.

## Demo
![CloudGuardianX Demo](demo1.gif)