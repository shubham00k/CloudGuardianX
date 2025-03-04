from flask import Flask, render_template
from cloudguardianx import AWS_REGION, AWS_VOLUME_ID, list_aws_snapshots

app = Flask(__name__, static_folder='static')  # Enable static files

@app.route('/')
def dashboard():
    snapshots = list_aws_snapshots()
    total_size = sum(snap['VolumeSize'] for snap in snapshots if 'VolumeSize' in snap) or 0  # Total size in GB
    cost_per_gb = 0.10  # Approx $0.10/GB/month for EBS snapshots
    monthly_cost = total_size * cost_per_gb
    return render_template('dashboard.html', snapshots=snapshots, total_size=total_size, cost=monthly_cost)

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)