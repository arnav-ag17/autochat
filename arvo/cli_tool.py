#!/usr/bin/env python3
"""
Command Line Tool for Arvo Autodeployment System
"""

import click
import os
import sys
from pathlib import Path
from typing import Optional

from .complete_llm_deploy import deploy_with_complete_llm_system
from .robust_llm import ComprehensiveNLP, ComprehensiveRepositoryAnalyzer


@click.group()
def cli():
    """Arvo - AI-Powered Application Deployment System"""
    pass


@cli.command()
@click.option("--instructions", "-i", required=True, help="Natural language deployment instructions")
@click.option("--repo", "-r", required=True, help="GitHub repository URL or path to ZIP file")
@click.option("--region", "-g", default="us-west-2", help="AWS region for deployment")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
def deploy(instructions: str, repo: str, region: str, verbose: bool):
    """Deploy an application using natural language instructions."""
    
    if verbose:
        print("🔍 Verbose mode enabled")
        print(f"📝 Instructions: {instructions}")
        print(f"📦 Repository: {repo}")
        print(f"🌍 Region: {region}")
    
    # Check if it's a ZIP file
    if repo.endswith('.zip') or Path(repo).exists():
        print("📁 ZIP file support coming soon...")
        print("Please use GitHub repository URLs for now.")
        sys.exit(1)
    
    # Check for API keys
    groq_key = os.getenv("GROQ_API_KEY")
    if not groq_key:
        print("❌ Error: GROQ_API_KEY environment variable not set")
        print("Get your free API key from: https://console.groq.com/keys")
        sys.exit(1)
    
    print("🚀 Starting Arvo deployment...")
    
    try:
        result = deploy_with_complete_llm_system(instructions, repo, region)
        
        if result["status"] == "success":
            print(f"\n🎉 Deployment successful!")
            print(f"📱 Application URL: {result['application_url']}")
            print(f"🔍 Health Check: {result['health_check_url']}")
            print(f"🏗️  Features: {', '.join(result.get('deployment_features', []))}")
            print(f"📄 Terraform Files: {', '.join(result.get('terraform_files', []))}")
            
            # Save deployment info
            deployment_file = Path(f".arvo/{result['deployment_id']}/deployment_info.json")
            deployment_file.parent.mkdir(parents=True, exist_ok=True)
            with open(deployment_file, "w") as f:
                import json
                json.dump(result, f, indent=2)
            
            print(f"💾 Deployment info saved to: {deployment_file}")
            
        else:
            print(f"\n❌ Deployment failed: {result.get('error')}")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        sys.exit(1)


@cli.command()
@click.option("--instructions", "-i", required=True, help="Natural language deployment instructions")
def analyze(instructions: str):
    """Analyze deployment requirements without deploying."""
    
    print("🧠 Analyzing deployment requirements...")
    
    try:
        nlp = ComprehensiveNLP()
        requirements = nlp.extract_deployment_requirements(instructions)
        
        print("\n📋 Extracted Requirements:")
        print("=" * 40)
        
        infra = requirements.get("infrastructure_requirements", {})
        app = requirements.get("application_requirements", {})
        db = requirements.get("database_requirements", {})
        security = requirements.get("security_requirements", {})
        networking = requirements.get("networking", {})
        monitoring = requirements.get("monitoring_logging", {})
        
        print(f"☁️  Cloud Provider: {infra.get('cloud_provider', 'aws')}")
        print(f"🏗️  Infrastructure: {infra.get('infrastructure_type', 'vm')}")
        print(f"💻 Instance Type: {infra.get('instance_type', 't2.micro')}")
        print(f"🌍 Region: {infra.get('region', 'us-west-2')}")
        print(f"📱 Framework: {app.get('framework', 'unknown')}")
        print(f"🔌 Port: {app.get('port', 5000)}")
        print(f"🗄️  Database: {db.get('database_type', 'none')}")
        print(f"🔒 SSL: {security.get('ssl_enabled', False)}")
        print(f"⚖️  Load Balancer: {networking.get('load_balancer', False)}")
        print(f"📊 Monitoring: {monitoring.get('monitoring_enabled', False)}")
        print(f"📈 Auto-scaling: {infra.get('auto_scaling', {}).get('enabled', False)}")
        
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        sys.exit(1)


@cli.command()
@click.option("--repo", "-r", required=True, help="GitHub repository URL")
def inspect(repo: str):
    """Inspect a repository without deploying."""
    
    print("🔍 Analyzing repository...")
    
    try:
        analyzer = ComprehensiveRepositoryAnalyzer()
        analysis = analyzer.analyze_repository(repo)
        
        print("\n📦 Repository Analysis:")
        print("=" * 40)
        
        app_class = analysis.get("Application Classification", {})
        tech_stack = analysis.get("Technology Stack", {})
        build_deploy = analysis.get("Build & Deployment", {})
        deps = analysis.get("Dependencies & Requirements", {})
        
        print(f"📱 App Type: {app_class.get('application_type', 'unknown')}")
        print(f"🏗️  Framework: {app_class.get('framework', 'unknown')}")
        print(f"💻 Runtime: {app_class.get('primary_language', 'unknown')}")
        print(f"🔨 Build Required: {build_deploy.get('build_required', False)}")
        print(f"📦 Dependencies: {len(deps.get('dependencies', []))} packages")
        print(f"🚀 Start Command: {build_deploy.get('start_command', 'auto-detect')}")
        print(f"📁 Main Directory: {analysis.get('Application Structure', {}).get('main_directory', '.')}")
        
        if deps.get('dependencies'):
            print(f"\n📋 Dependencies:")
            for dep in deps['dependencies'][:10]:  # Show first 10
                print(f"   • {dep}")
            if len(deps['dependencies']) > 10:
                print(f"   ... and {len(deps['dependencies']) - 10} more")
        
    except Exception as e:
        print(f"❌ Inspection failed: {e}")
        sys.exit(1)


@cli.command()
@click.option("--deployment-id", "-d", required=True, help="Deployment ID")
def status(deployment_id: str):
    """Check status of a deployment."""
    
    deployment_file = Path(f".arvo/{deployment_id}/deployment_info.json")
    
    if not deployment_file.exists():
        print(f"❌ Deployment {deployment_id} not found")
        sys.exit(1)
    
    try:
        import json
        with open(deployment_file, "r") as f:
            result = json.load(f)
        
        print(f"📊 Deployment Status: {deployment_id}")
        print("=" * 40)
        print(f"Status: {result['status']}")
        
        if result['status'] == 'success':
            print(f"📱 Application URL: {result['application_url']}")
            print(f"🔍 Health Check: {result['health_check_url']}")
            print(f"🏗️  Features: {', '.join(result.get('deployment_features', []))}")
        else:
            print(f"❌ Error: {result.get('error')}")
        
    except Exception as e:
        print(f"❌ Failed to read deployment info: {e}")
        sys.exit(1)


@cli.command()
def list():
    """List all deployments."""
    
    arvo_dir = Path(".arvo")
    if not arvo_dir.exists():
        print("No deployments found")
        return
    
    deployments = []
    for item in arvo_dir.iterdir():
        if item.is_dir() and item.name.startswith("d-"):
            deployment_file = item / "deployment_info.json"
            if deployment_file.exists():
                try:
                    import json
                    with open(deployment_file, "r") as f:
                        result = json.load(f)
                    deployments.append((item.name, result))
                except:
                    deployments.append((item.name, {"status": "unknown"}))
    
    if not deployments:
        print("No deployments found")
        return
    
    print("📋 Deployments:")
    print("=" * 60)
    print(f"{'ID':<20} {'Status':<10} {'URL':<30}")
    print("-" * 60)
    
    for deployment_id, result in deployments:
        status = result.get('status', 'unknown')
        url = result.get('application_url', 'N/A')[:30]
        print(f"{deployment_id:<20} {status:<10} {url:<30}")


@cli.command()
def setup():
    """Setup Arvo with API keys."""
    
    print("🔧 Arvo Setup")
    print("=" * 30)
    
    groq_key = os.getenv("GROQ_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")
    hf_key = os.getenv("HUGGINGFACE_API_KEY")
    
    print(f"Groq API Key: {'✅ Found' if groq_key else '❌ Missing'}")
    print(f"OpenAI API Key: {'✅ Found' if openai_key else '❌ Missing'}")
    print(f"Hugging Face Key: {'✅ Found' if hf_key else '❌ Missing'}")
    
    if not any([groq_key, openai_key, hf_key]):
        print("\n❌ No API keys found!")
        print("\nTo get started:")
        print("1. Get a free Groq API key: https://console.groq.com/keys")
        print("2. Set environment variable: export GROQ_API_KEY='your-key-here'")
        print("3. Run: arvo deploy --help")
    else:
        print("\n✅ Setup complete! You can now use Arvo.")
        print("Try: arvo deploy --instructions 'Deploy this Flask app on AWS' --repo 'https://github.com/Arvo-AI/hello_world'")


if __name__ == "__main__":
    cli()
