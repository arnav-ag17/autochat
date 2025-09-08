"""
ULTRA FAST deployment - minimal LLM usage, maximum speed.
"""

import time
import json
import subprocess
from pathlib import Path
from typing import Dict, Any


def ultra_fast_deploy(instructions: str, repo_url: str, region: str = "us-west-2") -> Dict[str, Any]:
    """
    ULTRA FAST deployment - minimal processing, maximum speed.
    """
    deployment_id = f"d-{int(time.time())}-{hash(repo_url) % 10000:04x}"
    
    print(f"⚡⚡ ULTRA FAST Deployment: {deployment_id}")
    print(f"📝 Instructions: {instructions}")
    print(f"📦 Repository: {repo_url}")
    
    try:
        # Step 1: MINIMAL NLP (just extract framework)
        print("\n🧠 Step 1: Minimal requirement extraction...")
        framework = "flask"  # Default
        if "django" in instructions.lower():
            framework = "django"
        elif "fastapi" in instructions.lower():
            framework = "fastapi"
        elif "express" in instructions.lower() or "node" in instructions.lower():
            framework = "express"
        
        port = 5000 if framework in ["flask", "django"] else 3000
        print(f"   ✅ Framework: {framework}, Port: {port}")
        
        # Step 2: SKIP repository analysis (use defaults)
        print("\n🔍 Step 2: Skipping repository analysis (using defaults)")
        
        # Step 3: Generate MINIMAL Terraform
        print("\n🏗️  Step 3: Generating minimal Terraform...")
        terraform_dir = _generate_minimal_terraform(deployment_id, framework, port, region, repo_url)
        
        # Step 4: Deploy infrastructure
        print("\n⚙️  Step 4: Deploying infrastructure...")
        success = _run_terraform_fast(terraform_dir)
        
        if not success:
            return {
                "deployment_id": deployment_id,
                "status": "failed",
                "error": "Terraform deployment failed"
            }
        
        # Step 5: Get outputs
        print("\n📊 Step 5: Getting deployment outputs...")
        outputs = _get_terraform_outputs_fast(terraform_dir)
        
        # Step 6: Quick health check
        print("\n⏳ Step 6: Quick health check...")
        public_ip = outputs.get("public_ip", {}).get("value")
        if public_ip:
            _quick_health_check(public_ip, port)
        
        print(f"\n⚡⚡ ULTRA FAST deployment completed!")
        
        return {
            "deployment_id": deployment_id,
            "status": "success",
            "application_url": f"http://{public_ip}:{port}",
            "health_check_url": f"http://{public_ip}:{port}",
            "instance_id": outputs.get("instance_id", {}).get("value")
        }
        
    except Exception as e:
        print(f"\n❌ ULTRA FAST deployment failed: {e}")
        return {
            "deployment_id": deployment_id,
            "status": "failed",
            "error": str(e)
        }


def _generate_minimal_terraform(deployment_id: str, framework: str, port: int, region: str, repo_url: str) -> Path:
    """Generate minimal Terraform configuration."""
    
    terraform_dir = Path(f".arvo/{deployment_id}")
    terraform_dir.mkdir(parents=True, exist_ok=True)
    
    # Simple main.tf
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
  region = "{region}"
}}

# Security group
resource "aws_security_group" "app" {{
  name_prefix = "ultra-fast-"
  
  ingress {{
    from_port   = {port}
    to_port     = {port}
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
    Name = "ultra-fast-sg"
  }}
}}

# EC2 instance
resource "aws_instance" "app" {{
  ami           = "ami-0bbc328167dee8f3c"  # Amazon Linux 2
  instance_type = "t3.micro"
  
  vpc_security_group_ids = [aws_security_group.app.id]
  
  user_data = base64encode(<<-EOT
#!/bin/bash
set -e
yum install -y git python3 python3-pip
mkdir -p /opt/app && cd /opt/app
git clone {repo_url} .
if [ -d "app" ]; then cd app; fi
python3 -m venv venv && source venv/bin/activate
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
else
    pip install flask gunicorn flask-cors
fi
for py_file in *.py; do
    if [ -f "$py_file" ]; then
        sed -i 's/app.run(host="127.0.0.1")/app.run(host="0.0.0.0", port={port})/g' "$py_file"
        sed -i 's/app.run(host="127.0.0.1", port=5000)/app.run(host="0.0.0.0", port={port})/g' "$py_file"
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
Environment=PORT={port}
ExecStart=/opt/app/venv/bin/python app.py
Restart=always
RestartSec=10
[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload && systemctl enable app && systemctl start app
sleep 3
EOT
  )
  
  tags = {{
    Name = "ultra-fast-app"
  }}
}}

# Elastic IP
resource "aws_eip" "app" {{
  instance = aws_instance.app.id
  domain   = "vpc"
  
  tags = {{
    Name = "ultra-fast-eip"
  }}
}}
"""
    
    with open(terraform_dir / "main.tf", "w") as f:
        f.write(main_tf)
    
    # Simple outputs.tf
    outputs_tf = """
output "public_ip" {
  description = "Public IP address of the instance"
  value       = aws_eip.app.public_ip
}

output "instance_id" {
  description = "Instance ID"
  value       = aws_instance.app.id
}
"""
    
    with open(terraform_dir / "outputs.tf", "w") as f:
        f.write(outputs_tf)
    
    return terraform_dir


def _run_terraform_fast(terraform_dir: Path) -> bool:
    """Run Terraform with minimal commands."""
    try:
        # Initialize (skip if already done)
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
        
        # Apply directly
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


def _get_terraform_outputs_fast(terraform_dir: Path) -> Dict[str, Any]:
    """Get Terraform outputs quickly."""
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


def _quick_health_check(public_ip: str, port: int) -> bool:
    """Quick health check."""
    import requests
    
    url = f"http://{public_ip}:{port}"
    
    # Try 3 times with 2 second intervals
    for i in range(3):
        try:
            response = requests.get(url, timeout=3)
            if response.status_code == 200:
                print(f"   ✅ Application is responding at {url}")
                return True
        except:
            pass
        
        if i < 2:  # Don't sleep on last attempt
            time.sleep(2)
    
    print(f"   ⚠️  Application not responding yet at {url}")
    return False


def test_ultra_fast_deployment():
    """Test the ultra fast deployment system."""
    print("⚡⚡ Testing ULTRA FAST Deployment System")
    print("=" * 50)
    
    start_time = time.time()
    
    result = ultra_fast_deploy(
        "Deploy this Flask application on AWS",
        "https://github.com/Arvo-AI/hello_world",
        "us-west-2"
    )
    
    end_time = time.time()
    deployment_time = end_time - start_time
    
    print(f"\n⏱️  Total deployment time: {deployment_time:.1f} seconds")
    
    if result["status"] == "success":
        print(f"🎉 ULTRA FAST deployment successful!")
        print(f"📱 Application URL: {result['application_url']}")
        
        # Test the application
        print(f"\n🧪 Testing application...")
        import requests
        try:
            response = requests.get(result['application_url'], timeout=5)
            if response.status_code == 200:
                print(f"✅ Application is working! Response: {len(response.text)} characters")
            else:
                print(f"⚠️  Application responded with status {response.status_code}")
        except Exception as e:
            print(f"❌ Application test failed: {e}")
    else:
        print(f"❌ ULTRA FAST deployment failed: {result.get('error')}")
    
    return result


if __name__ == "__main__":
    test_ultra_fast_deployment()
