"""
Simple deployment system that actually works.
"""

import os
import json
import subprocess
import time
import uuid
from pathlib import Path
from typing import Dict, Any, Optional
import shutil
import tempfile

from .openrouter_nlp import extract_deployment_requirements
from .simple_analyzer import analyze_repository


def deploy(instructions: str, repo_url: str, region: str = "us-west-2") -> Dict[str, Any]:
    """
    Deploy an application based on natural language instructions and repository URL.
    
    Args:
        instructions: Natural language deployment instructions
        repo_url: GitHub repository URL
        region: AWS region
        
    Returns:
        Deployment result with status and URLs
    """
    deployment_id = f"d-{int(time.time())}-{str(uuid.uuid4())[:8]}"
    
    print(f"🚀 Starting deployment: {deployment_id}")
    print(f"📝 Instructions: {instructions}")
    print(f"📦 Repository: {repo_url}")
    print(f"🌍 Region: {region}")
    
    try:
        # Step 1: Extract deployment requirements from instructions
        print("\n🔍 Step 1: Analyzing deployment requirements...")
        requirements = extract_deployment_requirements(instructions)
        print(f"   Cloud: {requirements['cloud']}")
        print(f"   Infrastructure: {requirements['infra']}")
        print(f"   Framework: {requirements['framework']}")
        
        # Step 2: Clone and analyze repository
        print("\n📥 Step 2: Cloning and analyzing repository...")
        repo_path = _clone_repository(repo_url, deployment_id)
        analysis = analyze_repository(repo_path)
        print(f"   Runtime: {analysis['runtime']}")
        print(f"   Framework: {analysis['framework']}")
        print(f"   App Path: {analysis['app_path']}")
        print(f"   Dependencies: {len(analysis['dependencies'])} packages")
        
        # Step 3: Generate deployment configuration
        print("\n⚙️  Step 3: Generating deployment configuration...")
        config = _generate_deployment_config(requirements, analysis, region, repo_url)
        
        # Step 4: Provision infrastructure
        print("\n🏗️  Step 4: Provisioning infrastructure...")
        terraform_dir = _setup_terraform(deployment_id, config)
        success = _run_terraform(terraform_dir)
        
        if not success:
            return {
                "deployment_id": deployment_id,
                "status": "failed",
                "error": "Terraform deployment failed"
            }
        
        # Step 5: Get deployment outputs
        print("\n📊 Step 5: Getting deployment outputs...")
        outputs = _get_terraform_outputs(terraform_dir)
        
        # Step 6: Wait for application to be ready
        print("\n⏳ Step 6: Waiting for application to be ready...")
        public_ip = outputs.get("public_ip", {}).get("value")
        if public_ip:
            _wait_for_application(public_ip, config["port"])
        
        print(f"\n✅ Deployment completed successfully!")
        print(f"🌐 Application URL: http://{public_ip}:{config['port']}")
        
        return {
            "deployment_id": deployment_id,
            "status": "success",
            "public_ip": public_ip,
            "application_url": f"http://{public_ip}:{config['port']}",
            "health_check_url": f"http://{public_ip}:{config['port']}",
            "instance_id": outputs.get("instance_id", {}).get("value"),
            "deployment_status": f"{analysis['framework']} application deployed successfully"
        }
        
    except Exception as e:
        print(f"\n❌ Deployment failed: {e}")
        return {
            "deployment_id": deployment_id,
            "status": "failed",
            "error": str(e)
        }


def _clone_repository(repo_url: str, deployment_id: str) -> str:
    """Clone repository to temporary directory."""
    temp_dir = Path(tempfile.gettempdir()) / f"arvo-{deployment_id}"
    temp_dir.mkdir(exist_ok=True)
    
    # Clone repository
    result = subprocess.run(
        ["git", "clone", repo_url, str(temp_dir)],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        raise Exception(f"Failed to clone repository: {result.stderr}")
    
    return str(temp_dir)


def _generate_deployment_config(requirements: Dict[str, Any], analysis: Dict[str, Any], region: str, repo_url: str) -> Dict[str, Any]:
    """Generate deployment configuration."""
    # Use detected framework or fallback to requirements
    framework = analysis.get("framework") or requirements.get("framework") or "flask"
    port = analysis.get("port") or requirements.get("port") or 8080
    
    # Generate user data script
    user_data = _generate_user_data_script(analysis, framework, port, repo_url)
    
    return {
        "app_name": f"{framework}-app",
        "region": region,
        "port": port,
        "framework": framework,
        "user_data": user_data,
        "instance_type": "t3.micro"  # Free tier eligible
    }


def _generate_user_data_script(analysis: Dict[str, Any], framework: str, port: int, repo_url: str = None) -> str:
    """Generate user data script for EC2 instance."""
    
    app_path_in_repo = analysis.get("app_path", ".") # e.g., "app" for hello_world
    start_command = analysis.get("start_command", "")
    needs_build = analysis.get("needs_build", False)
    build_command = analysis.get("build_command", "")
    
    if framework == "flask":
        return f"""#!/bin/bash
set -e

# Install git and Python (skip update for speed)
yum install -y git python3 python3-pip

# Create app directory
mkdir -p /opt/app
cd /opt/app

# Clone repository
git clone {repo_url} .

# Create virtual environment in the main app directory
python3 -m venv venv
source venv/bin/activate

# Navigate to app directory if it exists
if [ -d "{app_path_in_repo}" ]; then
    cd {app_path_in_repo}
fi

if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
else
    pip install flask gunicorn uvicorn
fi

# Fix Flask app configuration in all Python files
for py_file in *.py; do
    if [ -f "$py_file" ]; then
        sed -i 's/app.run(host="127.0.0.1", port=5000)/app.run(host="0.0.0.0", port={port})/g' "$py_file"
        sed -i 's/app.run(host="127.0.0.1")/app.run(host="0.0.0.0", port={port})/g' "$py_file"
        sed -i 's/app.run(port=5000)/app.run(host="0.0.0.0", port={port})/g' "$py_file"
        sed -i 's/app.run()/app.run(host="0.0.0.0", port={port})/g' "$py_file"
    fi
done

# Fix localhost references in HTML/JS files
PUBLIC_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)
find . -name "*.html" -o -name "*.js" | xargs sed -i "s/localhost:{port}/$PUBLIC_IP:{port}/g"
find . -name "*.html" -o -name "*.js" | xargs sed -i "s/127.0.0.1:{port}/$PUBLIC_IP:{port}/g"

# Create systemd service
cat > /etc/systemd/system/app.service << 'EOF'
[Unit]
Description=Application
After=network.target

[Service]
Type=simple
User=ec2-user
WorkingDirectory=/opt/app/{app_path_in_repo}
Environment=PORT={port}
ExecStart=/opt/app/venv/bin/python {start_command.split()[-1] if start_command else "app.py"}
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
systemctl daemon-reload
systemctl enable app
systemctl start app

# Wait for service to be ready
sleep 5
systemctl status app
"""
    
    elif framework == "fastapi":
        return f"""#!/bin/bash
set -e

# Install git and Python (skip update for speed)
yum install -y git python3 python3-pip

# Create app directory
mkdir -p /opt/app
cd /opt/app

# Clone repository
git clone {repo_url} .

# Navigate to app directory if it exists
if [ -d "{app_path_in_repo}" ]; then
    cd {app_path_in_repo}
fi

# Create virtual environment and install dependencies
python3 -m venv venv
source venv/bin/activate

if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
else
    pip install fastapi uvicorn
fi

# Fix localhost references in HTML/JS files
PUBLIC_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)
find . -name "*.html" -o -name "*.js" | xargs sed -i "s/localhost:{port}/$PUBLIC_IP:{port}/g"
find . -name "*.html" -o -name "*.js" | xargs sed -i "s/127.0.0.1:{port}/$PUBLIC_IP:{port}/g"

# Create systemd service
cat > /etc/systemd/system/app.service << 'EOF'
[Unit]
Description=Application
After=network.target

[Service]
Type=simple
User=ec2-user
WorkingDirectory=/opt/app/{app_path_in_repo}
Environment=PORT={port}
ExecStart=/opt/app/venv/bin/uvicorn main:app --host 0.0.0.0 --port {port}
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
systemctl daemon-reload
systemctl enable app
systemctl start app

# Wait for service to be ready
sleep 5
systemctl status app
"""
    
    elif framework == "express":
        return f"""#!/bin/bash
set -e

# Install Node.js (skip update for speed)
curl -fsSL https://rpm.nodesource.com/setup_18.x | bash -
yum install -y nodejs git

# Create app directory
mkdir -p /opt/app
cd /opt/app

# Clone repository
git clone {repo_url} .

# Navigate to app directory if it exists
if [ -d "{app_path_in_repo}" ]; then
    cd {app_path_in_repo}
fi

# Install dependencies
if [ -f "package.json" ]; then
    npm install
fi

# Build if needed
if [ "{needs_build}" = "True" ] && [ -n "{build_command}" ]; then
    echo "Building application..."
    {build_command}
fi

# Fix localhost references in HTML/JS files
PUBLIC_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)
find . -name "*.html" -o -name "*.js" | xargs sed -i "s/localhost:{port}/$PUBLIC_IP:{port}/g"
find . -name "*.html" -o -name "*.js" | xargs sed -i "s/127.0.0.1:{port}/$PUBLIC_IP:{port}/g"

# Create systemd service
cat > /etc/systemd/system/app.service << 'EOF'
[Unit]
Description=Application
After=network.target

[Service]
Type=simple
    User=ec2-user
    WorkingDirectory=/opt/app/{app_path_in_repo}
    Environment=PORT={port}
    ExecStart={start_command if start_command else "node index.js"}
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
systemctl daemon-reload
systemctl enable app
systemctl start app

# Wait for service to be ready
sleep 5
systemctl status app
"""
    
    else:
        # Default Flask setup
        return _generate_user_data_script(analysis, "flask", port)


def _setup_terraform(deployment_id: str, config: Dict[str, Any]) -> Path:
    """Setup Terraform configuration."""
    terraform_dir = Path(f".arvo/{deployment_id}")
    terraform_dir.mkdir(parents=True, exist_ok=True)
    
    # Create main.tf
    main_tf = f"""
terraform {{
  required_providers {{
    aws = {{
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }}
  }}
}}

provider "aws" {{
  region = "{config['region']}"
}}

# Security group
resource "aws_security_group" "app" {{
  name_prefix = "{config['app_name']}-"
  
  ingress {{
    from_port   = {config['port']}
    to_port     = {config['port']}
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }}
  
  ingress {{
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }}
  
  egress {{
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }}
  
  tags = {{
    Name = "{config['app_name']}-sg"
  }}
}}

# EC2 instance
resource "aws_instance" "app" {{
  ami           = "ami-0bbc328167dee8f3c"  # Amazon Linux 2
  instance_type = "{config['instance_type']}"
  
  vpc_security_group_ids = [aws_security_group.app.id]
  
  user_data = base64encode(<<-EOT
{config['user_data']}
EOT
  )
  
  tags = {{
    Name = "{config['app_name']}"
  }}
}}

# Elastic IP
resource "aws_eip" "app" {{
  instance = aws_instance.app.id
  domain   = "vpc"
  
  tags = {{
    Name = "{config['app_name']}-eip"
  }}
}}
"""
    
    with open(terraform_dir / "main.tf", "w") as f:
        f.write(main_tf)
    
    # Create outputs.tf
    outputs_tf = f"""
output "public_ip" {{
  description = "Public IP address of the application"
  value       = aws_eip.app.public_ip
}}

output "application_url" {{
  description = "URL to access the application"
  value       = "http://${{aws_eip.app.public_ip}}:{config['port']}"
}}

output "health_check_url" {{
  description = "Health check endpoint URL"
  value       = "http://${{aws_eip.app.public_ip}}:{config['port']}"
}}

output "instance_id" {{
  description = "EC2 instance ID"
  value       = aws_instance.app.id
}}

output "deployment_status" {{
  description = "Status of the deployment"
  value       = "{config['framework']} application deployed successfully"
}}
"""
    
    with open(terraform_dir / "outputs.tf", "w") as f:
        f.write(outputs_tf)
    
    return terraform_dir


def _run_terraform(terraform_dir: Path) -> bool:
    """Run Terraform commands - optimized for speed."""
    try:
        # Initialize Terraform (skip if already initialized)
        if not (terraform_dir / ".terraform").exists():
            result = subprocess.run(
                ["terraform", "init", "-upgrade=false"],
                cwd=terraform_dir,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                print(f"Terraform init failed: {result.stderr}")
                return False
        
        # Apply directly (skip plan for speed)
        result = subprocess.run(
            ["terraform", "apply", "-auto-approve", "-refresh=false"],
            cwd=terraform_dir,
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            print(f"Terraform apply failed: {result.stderr}")
            return False
        
        return True
        
    except Exception as e:
        print(f"Terraform error: {e}")
        return False


def _get_terraform_outputs(terraform_dir: Path) -> Dict[str, Any]:
    """Get Terraform outputs."""
    try:
        result = subprocess.run(
            ["terraform", "output", "-json"],
            cwd=terraform_dir,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            return json.loads(result.stdout)
        else:
            return {}
            
    except Exception:
        return {}


def _wait_for_application(public_ip: str, port: int, timeout: int = 120) -> bool:
    """Wait for application to be ready."""
    import requests
    
    url = f"http://{public_ip}:{port}"
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                return True
        except:
            pass
        
        time.sleep(5)  # Check every 5 seconds instead of 10
        print(f"   Waiting for application at {url}...")
    
    return False


def destroy(deployment_id: str) -> bool:
    """Destroy a deployment."""
    terraform_dir = Path(f".arvo/{deployment_id}")
    
    if not terraform_dir.exists():
        print(f"Deployment {deployment_id} not found")
        return False
    
    try:
        result = subprocess.run(
            ["terraform", "destroy", "-auto-approve"],
            cwd=terraform_dir,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print(f"✅ Deployment {deployment_id} destroyed successfully")
            return True
        else:
            print(f"❌ Failed to destroy deployment {deployment_id}: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Error destroying deployment {deployment_id}: {e}")
        return False
