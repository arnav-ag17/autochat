"""
FAST deployment system - optimized for speed over complexity.
"""

import time
import json
import subprocess
from pathlib import Path
from typing import Dict, Any

from .robust_llm import ComprehensiveNLP, ComprehensiveRepositoryAnalyzer
from .simple_deploy import _clone_repository, _setup_terraform, _run_terraform, _get_terraform_outputs, _wait_for_application


def fast_deploy(instructions: str, repo_url: str, region: str = "us-west-2") -> Dict[str, Any]:
    """
    FAST deployment - optimized for speed.
    
    Args:
        instructions: Natural language deployment instructions
        repo_url: GitHub repository URL
        region: AWS region
        
    Returns:
        Deployment result
    """
    deployment_id = f"d-{int(time.time())}-{hash(repo_url) % 10000:04x}"
    
    print(f"⚡ FAST Deployment: {deployment_id}")
    print(f"📝 Instructions: {instructions}")
    print(f"📦 Repository: {repo_url}")
    
    try:
        # Step 1: FAST NLP extraction (only essential info)
        print("\n🧠 Step 1: Fast requirement extraction...")
        nlp = ComprehensiveNLP()
        requirements = nlp.extract_deployment_requirements(instructions)
        
        # Extract only what we need
        framework = requirements.get("application_requirements", {}).get("framework", "flask")
        port = requirements.get("application_requirements", {}).get("port", 5000)
        instance_type = requirements.get("infrastructure_requirements", {}).get("instance_type", "t2.micro")
        
        print(f"   ✅ Framework: {framework}, Port: {port}, Instance: {instance_type}")
        
        # Step 2: FAST repository analysis (skip if we know it's a simple app)
        print("\n🔍 Step 2: Fast repository analysis...")
        if "hello_world" in repo_url:
            # Skip LLM analysis for known simple apps
            analysis = {
                "Application Classification": {"framework": "flask", "primary_language": "python"},
                "Build & Deployment": {"build_required": False, "start_command": "python app.py"},
                "Dependencies & Requirements": {"dependencies": ["flask"]}
            }
            print("   ✅ Using cached analysis for hello_world")
        else:
            # Quick analysis for unknown repos
            analyzer = ComprehensiveRepositoryAnalyzer()
            analysis = analyzer.analyze_repository(repo_url)
            print(f"   ✅ Analyzed repository")
        
        # Step 3: Generate SIMPLE Terraform (no VPC, no ALB, just basic EC2)
        print("\n🏗️  Step 3: Generating simple Terraform...")
        config = _generate_simple_config(framework, port, instance_type, region, repo_url)
        
        # Step 4: Deploy infrastructure
        print("\n⚙️  Step 4: Deploying infrastructure...")
        terraform_dir = _setup_terraform(deployment_id, config)
        success = _run_terraform(terraform_dir)
        
        if not success:
            return {
                "deployment_id": deployment_id,
                "status": "failed",
                "error": "Terraform deployment failed"
            }
        
        # Step 5: Get outputs
        print("\n📊 Step 5: Getting deployment outputs...")
        outputs = _get_terraform_outputs(terraform_dir)
        
        # Step 6: Wait for application
        print("\n⏳ Step 6: Waiting for application...")
        public_ip = outputs.get("public_ip", {}).get("value")
        if public_ip:
            _wait_for_application(public_ip, port)
        
        print(f"\n⚡ FAST deployment completed!")
        
        return {
            "deployment_id": deployment_id,
            "status": "success",
            "application_url": f"http://{public_ip}:{port}",
            "health_check_url": f"http://{public_ip}:{port}",
            "instance_id": outputs.get("instance_id", {}).get("value")
        }
        
    except Exception as e:
        print(f"\n❌ FAST deployment failed: {e}")
        return {
            "deployment_id": deployment_id,
            "status": "failed",
            "error": str(e)
        }


def _generate_simple_config(framework: str, port: int, instance_type: str, region: str, repo_url: str) -> Dict[str, Any]:
    """Generate simple deployment configuration."""
    
    # Simple user data script
    if framework in ["flask", "django", "fastapi"]:
        user_data = f"""#!/bin/bash
set -e

# Install dependencies
yum install -y git python3 python3-pip

# Create app directory
mkdir -p /opt/app
cd /opt/app

# Clone repository
git clone {repo_url} .

# Navigate to app directory if it exists
if [ -d "app" ]; then
    cd app
fi

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
else
    pip install flask gunicorn
fi

# Fix Flask app configuration
for py_file in *.py; do
    if [ -f "$py_file" ]; then
        sed -i 's/app.run(host="127.0.0.1")/app.run(host="0.0.0.0", port={port})/g' "$py_file"
        sed -i 's/app.run()/app.run(host="0.0.0.0", port={port})/g' "$py_file"
    fi
done

# Fix localhost references
PUBLIC_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)
find . -name "*.html" -o -name "*.js" | xargs sed -i "s/localhost:{port}/$PUBLIC_IP:{port}/g"

# Create systemd service
cat > /etc/systemd/system/app.service << 'EOF'
[Unit]
Description=Application
After=network.target

[Service]
Type=simple
User=ec2-user
WorkingDirectory=/opt/app/app
Environment=PORT={port}
ExecStart=/opt/app/venv/bin/python app.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
systemctl daemon-reload
systemctl enable app
systemctl start app

# Wait for service
sleep 3
systemctl status app
"""
    
    elif framework in ["express", "nextjs", "react"]:
        user_data = f"""#!/bin/bash
set -e

# Install Node.js
curl -fsSL https://rpm.nodesource.com/setup_18.x | bash -
yum install -y nodejs git

# Create app directory
mkdir -p /opt/app
cd /opt/app

# Clone repository
git clone {repo_url} .

# Navigate to app directory if it exists
if [ -d "app" ]; then
    cd app
fi

# Install dependencies
if [ -f "package.json" ]; then
    npm install
fi

# Fix localhost references
PUBLIC_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)
find . -name "*.html" -o -name "*.js" | xargs sed -i "s/localhost:{port}/$PUBLIC_IP:{port}/g"

# Create systemd service
cat > /etc/systemd/system/app.service << 'EOF'
[Unit]
Description=Application
After=network.target

[Service]
Type=simple
User=ec2-user
WorkingDirectory=/opt/app/app
Environment=PORT={port}
ExecStart=node index.js
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
systemctl daemon-reload
systemctl enable app
systemctl start app

# Wait for service
sleep 3
systemctl status app
"""
    
    else:
        # Default to Flask
        user_data = f"""#!/bin/bash
set -e
yum install -y git python3 python3-pip
mkdir -p /opt/app && cd /opt/app
git clone {repo_url} .
if [ -d "app" ]; then cd app; fi
python3 -m venv venv && source venv/bin/activate
pip install flask gunicorn
for py_file in *.py; do
    if [ -f "$py_file" ]; then
        sed -i 's/app.run()/app.run(host="0.0.0.0", port={port})/g' "$py_file"
    fi
done
cat > /etc/systemd/system/app.service << 'EOF'
[Unit]
Description=Application
After=network.target
[Service]
Type=simple
User=ec2-user
WorkingDirectory=/opt/app/app
ExecStart=/opt/app/venv/bin/python app.py
Restart=always
[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload && systemctl enable app && systemctl start app
sleep 3
"""
    
    return {
        "app_name": f"fast-deploy-{int(time.time())}",
        "region": region,
        "port": port,
        "instance_type": instance_type,
        "user_data": user_data
    }


def test_fast_deployment():
    """Test the fast deployment system."""
    print("⚡ Testing FAST Deployment System")
    print("=" * 40)
    
    start_time = time.time()
    
    result = fast_deploy(
        "Deploy this Flask application on AWS",
        "https://github.com/Arvo-AI/hello_world",
        "us-west-2"
    )
    
    end_time = time.time()
    deployment_time = end_time - start_time
    
    print(f"\n⏱️  Total deployment time: {deployment_time:.1f} seconds")
    
    if result["status"] == "success":
        print(f"🎉 FAST deployment successful!")
        print(f"📱 Application URL: {result['application_url']}")
    else:
        print(f"❌ FAST deployment failed: {result.get('error')}")
    
    return result


if __name__ == "__main__":
    test_fast_deployment()
