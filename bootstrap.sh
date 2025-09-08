#!/bin/bash
# Bootstrap script for Arvo deployment
set -euxo pipefail

echo "🚀 Starting Arvo deployment bootstrap..."

# Update system and install dependencies
yum update -y
yum install -y python3 python3-pip git curl awscli

# Install CloudWatch agent for log shipping
yum install -y amazon-cloudwatch-agent

# Install Flask and CORS support
pip3 install flask flask-cors

# Create application directory
mkdir -p /opt/app
cd /opt/app

# Clone the hello_world repository
echo "📥 Cloning hello_world repository..."
git clone https://github.com/Arvo-AI/hello_world.git repo
cd repo

# Determine the app directory (check if there's an 'app' subdirectory)
APP_DIR="/opt/app/repo"
if [ -d "app" ]; then
    APP_DIR="/opt/app/repo/app"
    cd app
fi

echo "📁 Using app directory: $APP_DIR"

# Install dependencies if requirements.txt exists
if [ -f "requirements.txt" ]; then
    echo "📦 Installing Python dependencies..."
    pip3 install -r requirements.txt
fi

# Get deployment metadata
DEPLOYMENT_ID="${DEPLOYMENT_ID:-d-$(date +%Y%m%d-%H%M%S)-$(openssl rand -hex 2)}"
REGION="${AWS_DEFAULT_REGION:-us-west-2}"
PUBLIC_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)
echo "🌐 Public IP: $PUBLIC_IP"
echo "🆔 Deployment ID: $DEPLOYMENT_ID"

# Fetch environment variables from SSM Parameter Store
echo "🔐 Fetching environment variables from SSM..."
ENV_FILE="/etc/default/arvo-app"
mkdir -p "$(dirname "$ENV_FILE")"

# Fetch all parameters for this deployment
aws ssm get-parameters-by-path \
    --path "/arvo/$DEPLOYMENT_ID/env/" \
    --with-decryption \
    --region "$REGION" \
    --output json > /tmp/ssm_params.json 2>/dev/null || {
    echo "⚠️  No SSM parameters found for deployment $DEPLOYMENT_ID"
    echo "# No environment variables from SSM" > "$ENV_FILE"
}

# Extract environment variables from SSM response
if [ -f "/tmp/ssm_params.json" ] && [ -s "/tmp/ssm_params.json" ]; then
    echo "📝 Writing environment variables to $ENV_FILE"
    python3 -c "
import json
import sys

try:
    with open('/tmp/ssm_params.json', 'r') as f:
        data = json.load(f)
    
    with open('$ENV_FILE', 'w') as f:
        f.write('# Environment variables from SSM Parameter Store\n')
        f.write('# Deployment ID: $DEPLOYMENT_ID\n\n')
        
        for param in data.get('Parameters', []):
            key = param['Name'].split('/')[-1]  # Extract key from path
            value = param['Value']
            f.write(f'export {key}=\"{value}\"\n')
    
    print('✅ Environment variables loaded from SSM')
except Exception as e:
    print(f'⚠️  Error processing SSM parameters: {e}')
    with open('$ENV_FILE', 'w') as f:
        f.write('# Error loading environment variables\n')
" || {
    echo "⚠️  Failed to process SSM parameters"
    echo "# Error loading environment variables" > "$ENV_FILE"
}
fi

# Set default environment variables
cat >> "$ENV_FILE" << EOF

# Default environment variables
export PORT=8080
export HOST=0.0.0.0
export FLASK_APP=app.py
export FLASK_ENV=production
export APP_DIR=$APP_DIR
export DEPLOYMENT_ID=$DEPLOYMENT_ID
export REGION=$REGION
EOF

chmod 644 "$ENV_FILE"

# Fix any localhost references in the frontend files
echo "🔧 Fixing frontend URLs..."
find . -name "*.html" -o -name "*.js" -o -name "*.py" | while read file; do
    if [ -f "$file" ]; then
        # Replace localhost:5000 with public IP:8080
        sed -i "s|http://localhost:5000|http://$PUBLIC_IP:8080|g" "$file"
        sed -i "s|http://127.0.0.1:5000|http://$PUBLIC_IP:8080|g" "$file"
        # Replace relative API calls with absolute ones
        sed -i "s|fetch('/api/|fetch('http://$PUBLIC_IP:8080/api/|g" "$file"
        sed -i "s|fetch(\"/api/|fetch(\"http://$PUBLIC_IP:8080/api/|g" "$file"
    fi
done

# Create a startup script that ensures proper Flask configuration
cat > /usr/local/bin/start_app.sh << 'EOF'
#!/bin/bash
set -euxo pipefail

# Source environment variables
if [ -f "/etc/default/arvo-app" ]; then
    source /etc/default/arvo-app
fi

APP_DIR="${APP_DIR:-/opt/app/repo}"
if [ -d "/opt/app/repo/app" ]; then
    APP_DIR="/opt/app/repo/app"
fi

cd "$APP_DIR"
echo "🚀 Starting Flask app from: $APP_DIR"

# Set environment variables with defaults
export FLASK_APP="${FLASK_APP:-app.py}"
export FLASK_ENV="${FLASK_ENV:-production}"
export PORT="${PORT:-8080}"
export HOST="${HOST:-0.0.0.0}"

# Create a wrapper that ensures CORS and proper binding
python3 -c "
import os
import sys
sys.path.insert(0, '.')

# Import the Flask app
try:
    from app import app
except ImportError:
    print('❌ Could not import app from app.py')
    sys.exit(1)

# Add CORS support
try:
    from flask_cors import CORS
    CORS(app, origins=['*'])  # Allow all origins for simplicity
    print('✅ CORS enabled for all origins')
except ImportError:
    print('⚠️  flask-cors not available, CORS may not work')

# Add a test endpoint if it doesn't exist
if not any(rule.rule == '/api/message' for rule in app.url_map.iter_rules()):
    @app.route('/api/message')
    def api_message():
        from flask import jsonify
        return jsonify(message='Hello, World!')

# Start the app
host = os.environ.get('HOST', '0.0.0.0')
port = int(os.environ.get('PORT', '8080'))
print(f'🌐 Starting Flask app on {host}:{port}')
app.run(host=host, port=port, debug=False)
"
EOF

chmod +x /usr/local/bin/start_app.sh

# Create systemd service
cat > /etc/systemd/system/arvo-app.service << EOF
[Unit]
Description=Arvo Application
Wants=network-online.target
After=network-online.target

[Service]
Type=simple
EnvironmentFile=/etc/default/arvo-app
ExecStart=/usr/local/bin/start_app.sh
Restart=always
RestartSec=5
User=ec2-user
StandardOutput=journal
StandardError=journal
WorkingDirectory=$APP_DIR

[Install]
WantedBy=multi-user.target
EOF

# Configure CloudWatch Logs
echo "📊 Configuring CloudWatch Logs..."
cat > /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json << EOF
{
    "logs": {
        "logs_collected": {
            "files": {
                "collect_list": [
                    {
                        "file_path": "/var/log/cloud-init-output.log",
                        "log_group_name": "/arvo/$DEPLOYMENT_ID",
                        "log_stream_name": "ec2/cloud-init"
                    },
                    {
                        "file_path": "/var/log/messages",
                        "log_group_name": "/arvo/$DEPLOYMENT_ID",
                        "log_stream_name": "ec2/system"
                    }
                ]
            }
        }
    }
}
EOF

# Start CloudWatch agent
/opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl \
    -a fetch-config -m ec2 -c file:/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json -s

# Set permissions
chown -R ec2-user:ec2-user /opt/app

# Start the service
systemctl daemon-reload
systemctl enable --now arvo-app

# Wait for service to start
sleep 10

# Test the application
echo "🧪 Testing application..."
if systemctl is-active --quiet arvo-app; then
    echo "✅ Application started successfully!"
    
    # Test the main endpoint
    if curl -f -s "http://localhost:8080/" > /dev/null; then
        echo "✅ Main endpoint is responding"
    else
        echo "⚠️  Main endpoint test failed"
    fi
    
    # Test the API endpoint
    if curl -f -s "http://localhost:8080/api/message" > /dev/null; then
        echo "✅ API endpoint is responding"
        API_RESPONSE=$(curl -s "http://localhost:8080/api/message")
        echo "📄 API Response: $API_RESPONSE"
    else
        echo "⚠️  API endpoint test failed"
    fi
    
    echo "🌐 Application should be accessible at: http://$PUBLIC_IP:8080"
    echo "🔗 API endpoint: http://$PUBLIC_IP:8080/api/message"
    echo "📊 CloudWatch Logs: /arvo/$DEPLOYMENT_ID"
else
    echo "❌ Failed to start application"
    systemctl status arvo-app --no-pager
    echo "📋 Recent logs:"
    journalctl -u arvo-app -n 20 --no-pager
    exit 1
fi

echo "🎉 Bootstrap completed successfully!"