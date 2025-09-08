"""
LLM-powered deployment system.
"""

import time
import subprocess
import json
from pathlib import Path
from typing import Dict, Any

from .llm_nlp import LLMNLPProvider, GitHubAnalyzer
from .simple_deploy import _clone_repository, _generate_deployment_config, _setup_terraform, _run_terraform, _get_terraform_outputs, _wait_for_application


def deploy_with_llm(instructions: str, repo_url: str, region: str = "us-west-2") -> Dict[str, Any]:
    """
    Deploy using LLM-powered analysis.
    
    Args:
        instructions: Natural language deployment instructions
        repo_url: GitHub repository URL
        region: AWS region
        
    Returns:
        Deployment result
    """
    deployment_id = f"d-{int(time.time())}-{hash(repo_url) % 10000:04x}"
    
    print(f"🚀 Starting LLM-powered deployment: {deployment_id}")
    print(f"📝 Instructions: {instructions}")
    print(f"📦 Repository: {repo_url}")
    print(f"🌍 Region: {region}")
    
    try:
        # Step 1: LLM-powered NLP extraction
        print("\n🤖 Step 1: LLM-powered requirement extraction...")
        nlp_provider = LLMNLPProvider()
        requirements = nlp_provider.extract_deployment_requirements(instructions)
        
        print(f"   Cloud: {requirements.get('cloud', 'aws')}")
        print(f"   Infrastructure: {requirements.get('infra', 'vm')}")
        print(f"   Framework: {requirements.get('framework', 'auto-detect')}")
        print(f"   Region: {requirements.get('region', region)}")
        print(f"   Instance Size: {requirements.get('instance_size', 'small')}")
        
        # Step 2: GitHub API-powered repository analysis
        print("\n🔍 Step 2: GitHub API-powered repository analysis...")
        github_analyzer = GitHubAnalyzer()
        analysis = github_analyzer.analyze_repository(repo_url)
        
        print(f"   Runtime: {analysis.get('runtime', 'unknown')}")
        print(f"   Framework: {analysis.get('framework', 'unknown')}")
        print(f"   App Path: {analysis.get('app_path', '.')}")
        print(f"   Start Command: {analysis.get('start_command', 'auto-detect')}")
        print(f"   Dependencies: {len(analysis.get('dependencies', []))} packages")
        
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
        
        print(f"\n✅ LLM-powered deployment completed successfully!")
        
        return {
            "deployment_id": deployment_id,
            "status": "success",
            "application_url": f"http://{public_ip}:{config['port']}",
            "health_check_url": f"http://{public_ip}:{config['port']}",
            "instance_id": outputs.get("instance_id", {}).get("value"),
            "requirements": requirements,
            "analysis": analysis
        }
        
    except Exception as e:
        print(f"\n❌ LLM deployment failed: {e}")
        return {
            "deployment_id": deployment_id,
            "status": "failed",
            "error": str(e)
        }


def test_llm_system():
    """Test the LLM system with complex instructions."""
    
    # Test 1: Complex NLP instructions
    complex_instructions = """
    I need to deploy a Flask web application on AWS in the us-east-1 region. 
    The app should run on a t2.medium instance with SSL enabled and autoscaling. 
    I also need a PostgreSQL database and monitoring with CloudWatch logs. 
    The application should be accessible via a custom domain and have a load balancer 
    for high availability. Make sure it's secure with HTTPS.
    """
    
    print("🧪 Testing LLM-powered NLP extraction...")
    nlp_provider = LLMNLPProvider()
    requirements = nlp_provider.extract_deployment_requirements(complex_instructions)
    
    print("Extracted requirements:")
    for key, value in requirements.items():
        print(f"  {key}: {value}")
    
    # Test 2: GitHub repository analysis
    print("\n🧪 Testing GitHub API-powered repository analysis...")
    github_analyzer = GitHubAnalyzer()
    analysis = github_analyzer.analyze_repository("https://github.com/Arvo-AI/hello_world")
    
    print("Repository analysis:")
    for key, value in analysis.items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    test_llm_system()
