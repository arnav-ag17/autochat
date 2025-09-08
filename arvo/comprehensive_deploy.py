"""
Comprehensive deployment system using robust LLM analysis.
"""

import time
import json
from typing import Dict, Any
from .robust_llm import ComprehensiveNLP, ComprehensiveRepositoryAnalyzer
from .simple_deploy import _clone_repository, _generate_deployment_config, _setup_terraform, _run_terraform, _get_terraform_outputs, _wait_for_application


def deploy_with_comprehensive_llm(instructions: str, repo_url: str, region: str = "us-west-2") -> Dict[str, Any]:
    """
    Deploy using comprehensive LLM analysis.
    
    Args:
        instructions: Natural language deployment instructions
        repo_url: GitHub repository URL
        region: AWS region
        
    Returns:
        Comprehensive deployment result
    """
    deployment_id = f"d-{int(time.time())}-{hash(repo_url) % 10000:04x}"
    
    print(f"🚀 Starting Comprehensive LLM Deployment: {deployment_id}")
    print(f"📝 Instructions: {instructions}")
    print(f"📦 Repository: {repo_url}")
    print(f"🌍 Region: {region}")
    
    try:
        # Step 1: Comprehensive NLP extraction
        print("\n🧠 Step 1: Comprehensive LLM-powered requirement extraction...")
        nlp = ComprehensiveNLP()
        requirements = nlp.extract_deployment_requirements(instructions)
        
        print(f"   ✅ Extracted {len(requirements)} requirement categories")
        print(f"   Infrastructure: {requirements.get('infrastructure_type', 'vm')}")
        print(f"   Instance: {requirements.get('instance_type', 't2.micro')} x {requirements.get('instance_count', 1)}")
        print(f"   Database: {requirements.get('database_type', 'none')}")
        print(f"   SSL: {requirements.get('ssl_enabled', False)}")
        print(f"   Monitoring: {requirements.get('monitoring_enabled', False)}")
        print(f"   Auto-scaling: {requirements.get('auto_scaling', False)}")
        
        # Step 2: Comprehensive repository analysis
        print("\n🔍 Step 2: Comprehensive LLM-powered repository analysis...")
        analyzer = ComprehensiveRepositoryAnalyzer()
        analysis = analyzer.analyze_repository(repo_url)
        
        print(f"   ✅ Analyzed {len(analysis)} analysis categories")
        print(f"   App Type: {analysis.get('application_type', 'web_app')}")
        print(f"   Framework: {analysis.get('framework', 'flask')}")
        print(f"   Runtime: {analysis.get('primary_language', 'python')}")
        print(f"   Build Required: {analysis.get('build_required', False)}")
        print(f"   Dependencies: {len(analysis.get('dependencies', []))} packages")
        print(f"   Start Command: {analysis.get('start_command', 'auto-detect')}")
        
        # Step 3: Generate smart deployment configuration
        print("\n⚙️  Step 3: Generating smart deployment configuration...")
        config = _generate_smart_config(requirements, analysis, region, repo_url)
        
        # Step 4: Provision infrastructure
        print("\n🏗️  Step 4: Provisioning infrastructure...")
        terraform_dir = _setup_terraform(deployment_id, config)
        success = _run_terraform(terraform_dir)
        
        if not success:
            return {
                "deployment_id": deployment_id,
                "status": "failed",
                "error": "Terraform deployment failed",
                "llm_requirements": requirements,
                "llm_analysis": analysis
            }
        
        # Step 5: Get deployment outputs
        print("\n📊 Step 5: Getting deployment outputs...")
        outputs = _get_terraform_outputs(terraform_dir)
        
        # Step 6: Wait for application to be ready
        print("\n⏳ Step 6: Waiting for application to be ready...")
        public_ip = outputs.get("public_ip", {}).get("value")
        if public_ip:
            _wait_for_application(public_ip, config["port"])
        
        print(f"\n✅ Comprehensive LLM deployment completed successfully!")
        
        return {
            "deployment_id": deployment_id,
            "status": "success",
            "application_url": f"http://{public_ip}:{config['port']}",
            "health_check_url": f"http://{public_ip}:{config['port']}",
            "instance_id": outputs.get("instance_id", {}).get("value"),
            "llm_requirements": requirements,
            "llm_analysis": analysis,
            "deployment_config": config
        }
        
    except Exception as e:
        print(f"\n❌ Comprehensive LLM deployment failed: {e}")
        return {
            "deployment_id": deployment_id,
            "status": "failed",
            "error": str(e)
        }


def _generate_smart_config(requirements: Dict[str, Any], analysis: Dict[str, Any], region: str, repo_url: str) -> Dict[str, Any]:
    """
    Generate smart deployment configuration based on LLM analysis.
    
    Args:
        requirements: LLM-extracted requirements
        analysis: LLM repository analysis
        region: AWS region
        repo_url: Repository URL
        
    Returns:
        Deployment configuration
    """
    # Use LLM analysis to determine optimal configuration
    framework = analysis.get("framework", "flask")
    runtime = analysis.get("primary_language", "python")
    app_path = analysis.get("main_directory", ".")
    start_command = analysis.get("start_command", "python app.py")
    port = requirements.get("port") or analysis.get("port") or 5000
    
    # Determine instance type based on requirements
    instance_type = "t2.micro"  # Default
    if requirements.get("instance_type"):
        instance_type = requirements.get("instance_type")
    elif requirements.get("auto_scaling"):
        instance_type = "t3.small"  # Better for auto-scaling
    elif requirements.get("database_type") != "none":
        instance_type = "t3.medium"  # More resources for database
    
    # Generate user data script based on analysis
    user_data = _generate_smart_user_data(analysis, framework, port, repo_url)
    
    config = {
        "app_name": f"llm-deploy-{int(time.time())}",
        "region": region,
        "port": port,
        "instance_type": instance_type,
        "user_data": user_data,
        "framework": framework,
        "runtime": runtime,
        "app_path": app_path,
        "start_command": start_command
    }
    
    print(f"   Smart Config: {framework} app on {instance_type} in {region}")
    print(f"   App Path: {app_path}, Start Command: {start_command}")
    
    return config


def _generate_smart_user_data(analysis: Dict[str, Any], framework: str, port: int, repo_url: str) -> str:
    """
    Generate smart user data script based on LLM analysis.
    
    Args:
        analysis: LLM repository analysis
        framework: Detected framework
        port: Application port
        repo_url: Repository URL
        
    Returns:
        User data script
    """
    app_path = analysis.get("main_directory", ".")
    start_command = analysis.get("start_command", "python app.py")
    dependencies = analysis.get("dependencies", [])
    build_required = analysis.get("build_required", False)
    build_command = analysis.get("build_command", "")
    package_manager = analysis.get("package_manager", "pip")
    
    if framework in ["flask", "django", "fastapi"]:
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

# Navigate to app directory
if [ -d "{app_path}" ]; then
    cd {app_path}
fi

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
WorkingDirectory=/opt/app/{app_path}
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

# Wait for service
sleep 5
systemctl status app
"""
    
    elif framework in ["express", "nextjs", "react"]:
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

# Navigate to app directory
if [ -d "{app_path}" ]; then
    cd {app_path}
fi

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
find . -name "*.html" -o -name "*.js" | xargs sed -i "s/localhost:{port}/$PUBLIC_IP:{port}/g"

# Create systemd service
cat > /etc/systemd/system/app.service << 'EOF'
[Unit]
Description=Application
After=network.target

[Service]
Type=simple
User=ec2-user
WorkingDirectory=/opt/app/{app_path}
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

# Wait for service
sleep 5
systemctl status app
"""
    
    else:
        # Default Flask setup
        return _generate_smart_user_data(analysis, "flask", port, repo_url)


def test_comprehensive_deployment():
    """Test the comprehensive deployment system."""
    print("🧪 Testing Comprehensive Deployment System")
    print("=" * 60)
    
    # Test with complex instructions
    complex_instructions = """
    Deploy a Flask web application on AWS in us-east-1 region. Use t2.medium instances with auto-scaling. 
    Enable SSL with custom domain. Set up PostgreSQL database with daily backups. 
    Configure CloudWatch monitoring with alerts. Use Application Load Balancer with health checks.
    """
    
    print("Testing with complex instructions...")
    result = deploy_with_comprehensive_llm(
        complex_instructions,
        "https://github.com/Arvo-AI/hello_world",
        "us-west-2"
    )
    
    if result["status"] == "success":
        print(f"\n🎉 Deployment successful!")
        print(f"📱 Application URL: {result['application_url']}")
        print(f"🔍 Health Check: {result['health_check_url']}")
    else:
        print(f"\n❌ Deployment failed: {result.get('error')}")
    
    return result


if __name__ == "__main__":
    test_comprehensive_deployment()
