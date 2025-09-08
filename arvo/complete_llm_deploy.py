"""
Complete LLM-powered deployment system that connects analysis to Terraform.
"""

import time
import json
from pathlib import Path
from typing import Dict, Any, List

from .robust_llm import ComprehensiveNLP, ComprehensiveRepositoryAnalyzer
from .llm_terraform_generator import LLMTerraformGenerator
from .simple_deploy import _clone_repository, _run_terraform, _get_terraform_outputs, _wait_for_application


def deploy_with_complete_llm_system(instructions: str, repo_url: str, region: str = "us-west-2") -> Dict[str, Any]:
    """
    Complete LLM-powered deployment that actually uses LLM analysis for Terraform generation.
    
    Args:
        instructions: Natural language deployment instructions
        repo_url: GitHub repository URL
        region: AWS region
        
    Returns:
        Complete deployment result
    """
    deployment_id = f"d-{int(time.time())}-{hash(repo_url) % 10000:04x}"
    
    print(f"🚀 Starting Complete LLM Deployment: {deployment_id}")
    print(f"📝 Instructions: {instructions}")
    print(f"📦 Repository: {repo_url}")
    print(f"🌍 Region: {region}")
    
    try:
        # Step 1: Comprehensive NLP extraction
        print("\n🧠 Step 1: LLM-powered requirement extraction...")
        nlp = ComprehensiveNLP()
        requirements = nlp.extract_deployment_requirements(instructions)
        
        print(f"   ✅ Extracted {len(requirements)} requirement categories")
        _print_requirements_summary(requirements)
        
        # Step 2: Comprehensive repository analysis
        print("\n🔍 Step 2: LLM-powered repository analysis...")
        analyzer = ComprehensiveRepositoryAnalyzer()
        analysis = analyzer.analyze_repository(repo_url)
        
        print(f"   ✅ Analyzed {len(analysis)} analysis categories")
        _print_analysis_summary(analysis)
        
        # Step 3: Generate Terraform configuration based on LLM analysis
        print("\n🏗️  Step 3: Generating Terraform from LLM analysis...")
        terraform_generator = LLMTerraformGenerator()
        terraform_files = terraform_generator.generate_terraform_config(
            requirements, analysis, region, repo_url
        )
        
        print(f"   ✅ Generated {len(terraform_files)} Terraform files")
        for filename in terraform_files.keys():
            print(f"      📄 {filename}")
        
        # Step 4: Write Terraform files and deploy
        print("\n⚙️  Step 4: Deploying infrastructure...")
        terraform_dir = Path(f".arvo/{deployment_id}")
        terraform_dir.mkdir(parents=True, exist_ok=True)
        
        # Write Terraform files
        for filename, content in terraform_files.items():
            with open(terraform_dir / filename, "w") as f:
                f.write(content)
        
        # Generate user data script
        user_data = _generate_user_data_from_analysis(analysis, repo_url)
        with open(terraform_dir / "user_data.sh", "w") as f:
            f.write(user_data)
        
        # Run Terraform
        success = _run_terraform(terraform_dir)
        
        if not success:
            return {
                "deployment_id": deployment_id,
                "status": "failed",
                "error": "Terraform deployment failed",
                "llm_requirements": requirements,
                "llm_analysis": analysis,
                "terraform_files": list(terraform_files.keys())
            }
        
        # Step 5: Get deployment outputs
        print("\n📊 Step 5: Getting deployment outputs...")
        outputs = _get_terraform_outputs(terraform_dir)
        
        # Step 6: Wait for application
        print("\n⏳ Step 6: Waiting for application to be ready...")
        application_url = outputs.get("application_url", {}).get("value")
        if not application_url:
            # Fallback to public IP
            public_ip = outputs.get("public_ip", {}).get("value")
            if public_ip:
                port = requirements.get("application_requirements", {}).get("port", 5000)
                application_url = f"http://{public_ip}:{port}"
        
        if application_url:
            # Extract IP and port for health check
            if "://" in application_url:
                ip_port = application_url.split("://")[1]
                if ":" in ip_port:
                    ip, port = ip_port.split(":")
                    _wait_for_application(ip, int(port))
        
        print(f"\n✅ Complete LLM deployment successful!")
        
        return {
            "deployment_id": deployment_id,
            "status": "success",
            "application_url": application_url,
            "health_check_url": application_url,
            "llm_requirements": requirements,
            "llm_analysis": analysis,
            "terraform_files": list(terraform_files.keys()),
            "deployment_features": _extract_deployment_features(requirements)
        }
        
    except Exception as e:
        print(f"\n❌ Complete LLM deployment failed: {e}")
        return {
            "deployment_id": deployment_id,
            "status": "failed",
            "error": str(e)
        }
    
def _print_requirements_summary(requirements: Dict[str, Any]):
        """Print a summary of extracted requirements."""
        infra = requirements.get("infrastructure_requirements", {})
        app = requirements.get("application_requirements", {})
        db = requirements.get("database_requirements", {})
        security = requirements.get("security_requirements", {})
        networking = requirements.get("networking", {})
        monitoring = requirements.get("monitoring_logging", {})
        
        print(f"      Infrastructure: {infra.get('infrastructure_type', 'vm')} ({infra.get('instance_type', 't2.micro')})")
        print(f"      Framework: {app.get('framework', 'unknown')} on port {app.get('port', 5000)}")
        print(f"      Database: {db.get('database_type', 'none')}")
        print(f"      SSL: {security.get('ssl_enabled', False)}")
        print(f"      Load Balancer: {networking.get('load_balancer', False)}")
        print(f"      Monitoring: {monitoring.get('monitoring_enabled', False)}")
        print(f"      Auto-scaling: {infra.get('auto_scaling', {}).get('enabled', False)}")
    
def _print_analysis_summary(analysis: Dict[str, Any]):
        """Print a summary of repository analysis."""
        app_class = analysis.get("Application Classification", {})
        tech_stack = analysis.get("Technology Stack", {})
        build_deploy = analysis.get("Build & Deployment", {})
        
        print(f"      App Type: {app_class.get('application_type', 'unknown')}")
        print(f"      Framework: {app_class.get('framework', 'unknown')}")
        print(f"      Runtime: {app_class.get('primary_language', 'unknown')}")
        print(f"      Build Required: {build_deploy.get('build_required', False)}")
        print(f"      Dependencies: {len(analysis.get('Dependencies & Requirements', {}).get('dependencies', []))} packages")
        print(f"      Start Command: {build_deploy.get('start_command', 'auto-detect')}")
    
def _generate_user_data_from_analysis(analysis: Dict[str, Any], repo_url: str) -> str:
        """Generate user data script based on LLM analysis."""
        app_class = analysis.get("Application Classification", {})
        build_deploy = analysis.get("Build & Deployment", {})
        deps = analysis.get("Dependencies & Requirements", {})
        
        framework = app_class.get("framework", "flask")
        runtime = app_class.get("primary_language", "python")
        start_command = build_deploy.get("start_command", "python app.py")
        build_required = build_deploy.get("build_required", False)
        build_command = build_deploy.get("build_command", "")
        dependencies = deps.get("dependencies", [])
        package_manager = deps.get("package_manager", "pip")
        
        if runtime == "python":
            return f"""#!/bin/bash
set -e

# Install system dependencies
yum install -y git python3 python3-pip

# Create app directory
mkdir -p /opt/app
cd /opt/app

# Clone repository
git clone {repo_url} .

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
else:
    pip install {' '.join(dependencies) if dependencies else 'flask gunicorn uvicorn'}

# Build if required
if [ "{build_required}" = "True" ] && [ -n "{build_command}" ]; then
    echo "Building application..."
    {build_command}
fi

# Fix Flask app configuration
for py_file in *.py; do
    if [ -f "$py_file" ]; then
        sed -i 's/app.run(host="127.0.0.1")/app.run(host="0.0.0.0", port=5000)/g' "$py_file"
        sed -i 's/app.run()/app.run(host="0.0.0.0", port=5000)/g' "$py_file"
    fi
done

# Fix localhost references
PUBLIC_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)
find . -name "*.html" -o -name "*.js" | xargs sed -i "s/localhost:5000/$PUBLIC_IP:5000/g"

# Create systemd service
cat > /etc/systemd/system/app.service << 'EOF'
[Unit]
Description=Application
After=network.target

[Service]
Type=simple
User=ec2-user
WorkingDirectory=/opt/app
Environment=PORT=5000
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

# Wait for service
sleep 5
systemctl status app
"""
        
        elif runtime == "javascript" or runtime == "node":
            return f"""#!/bin/bash
set -e

# Install Node.js
curl -fsSL https://rpm.nodesource.com/setup_18.x | bash -
yum install -y nodejs git

# Create app directory
mkdir -p /opt/app
cd /opt/app

# Clone repository
git clone {repo_url} .

# Install dependencies
if [ -f "package.json" ]; then
    npm install
fi

# Build if required
if [ "{build_required}" = "True" ] && [ -n "{build_command}" ]; then
    echo "Building application..."
    {build_command}
fi

# Fix localhost references
PUBLIC_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)
find . -name "*.html" -o -name "*.js" | xargs sed -i "s/localhost:3000/$PUBLIC_IP:3000/g"

# Create systemd service
cat > /etc/systemd/system/app.service << 'EOF'
[Unit]
Description=Application
After=network.target

[Service]
Type=simple
User=ec2-user
WorkingDirectory=/opt/app
Environment=PORT=3000
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

# Wait for service
sleep 5
systemctl status app
"""
        
        else:
            # Default to Python
            return _generate_user_data_from_analysis({**analysis, "Application Classification": {**app_class, "primary_language": "python"}}, repo_url)
    
def _extract_deployment_features(requirements: Dict[str, Any]) -> List[str]:
        """Extract list of deployment features enabled."""
        features = []
        
        if requirements.get("database_requirements", {}).get("database_type") != "none":
            features.append("database")
        
        if requirements.get("security_requirements", {}).get("ssl_enabled"):
            features.append("ssl")
        
        if requirements.get("networking", {}).get("load_balancer"):
            features.append("load_balancer")
        
        if requirements.get("monitoring_logging", {}).get("monitoring_enabled"):
            features.append("monitoring")
        
        if requirements.get("infrastructure_requirements", {}).get("auto_scaling", False):
            features.append("auto_scaling")
        
        if requirements.get("security_requirements", {}).get("vpc_required"):
            features.append("vpc")
        
        return features


def test_complete_system():
    """Test the complete LLM deployment system."""
    print("🧪 Testing Complete LLM Deployment System")
    print("=" * 60)
    
    # Test with complex instructions
    complex_instructions = """
    Deploy a Flask web application on AWS in us-west-2 region. Use t2.medium instances with auto-scaling (min 2, max 5). 
    Enable SSL with custom domain. Set up PostgreSQL database with daily backups. 
    Configure CloudWatch monitoring with alerts. Use Application Load Balancer with health checks.
    Enable VPC with private subnets for security.
    """
    
    print("Testing with complex instructions...")
    result = deploy_with_complete_llm_system(
        complex_instructions,
        "https://github.com/Arvo-AI/hello_world",
        "us-west-2"
    )
    
    if result["status"] == "success":
        print(f"\n🎉 Deployment successful!")
        print(f"📱 Application URL: {result['application_url']}")
        print(f"🔍 Health Check: {result['health_check_url']}")
        print(f"🏗️  Features: {', '.join(result.get('deployment_features', []))}")
        print(f"📄 Terraform Files: {', '.join(result.get('terraform_files', []))}")
    else:
        print(f"\n❌ Deployment failed: {result.get('error')}")
    
    return result


if __name__ == "__main__":
    test_complete_system()
