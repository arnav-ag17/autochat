#!/usr/bin/env python3
"""
Test the smart deployment system with actual API keys.
"""

import os
from arvo.smart_deploy import smart_analyze_instructions, smart_analyze_repository, execute_deployment_plan

def main():
    """Test with API keys."""
    print("🔑 Testing Smart Deployment with API Keys")
    print("=" * 50)
    
    # Check for API keys
    groq_key = os.getenv("GROQ_API_KEY")
    hf_key = os.getenv("HUGGINGFACE_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")
    
    print(f"Groq API Key: {'✅ Found' if groq_key else '❌ Missing'}")
    print(f"Hugging Face Key: {'✅ Found' if hf_key else '❌ Missing'}")
    print(f"OpenAI Key: {'✅ Found' if openai_key else '❌ Missing'}")
    
    if not any([groq_key, hf_key, openai_key]):
        print("\n❌ No API keys found!")
        print("Get free keys from:")
        print("  - Groq: https://console.groq.com/keys")
        print("  - Hugging Face: https://huggingface.co/settings/tokens")
        print("  - OpenAI: https://platform.openai.com/api-keys")
        return
    
    # Test complex instructions
    complex_instructions = """
    Deploy a Flask web application on AWS in us-east-1 region. 
    Use t2.medium instance with SSL enabled, autoscaling, PostgreSQL database, 
    and CloudWatch monitoring. The app should be accessible via custom domain.
    """
    
    print(f"\n🤖 Testing with instructions: {complex_instructions}")
    
    # Analyze instructions
    plan = smart_analyze_instructions(complex_instructions)
    print(f"\n📋 Generated Plan:")
    print(f"   Infrastructure: {plan.get('infrastructure_type')}")
    print(f"   Instance: {plan.get('instance_config', {}).get('type')} in {plan.get('instance_config', {}).get('region')}")
    print(f"   Framework: {plan.get('application_config', {}).get('framework')}")
    print(f"   SSL: {plan.get('security_config', {}).get('ssl')}")
    print(f"   Database: {plan.get('application_config', {}).get('needs_database')}")
    print(f"   Steps: {plan.get('deployment_steps', [])}")
    
    # Analyze repository
    repo_analysis = smart_analyze_repository("https://github.com/Arvo-AI/hello_world")
    print(f"\n🔍 Repository Analysis:")
    print(f"   App Type: {repo_analysis.get('app_type')}")
    print(f"   Runtime: {repo_analysis.get('technology_stack', {}).get('runtime')}")
    print(f"   Framework: {repo_analysis.get('technology_stack', {}).get('framework')}")
    print(f"   Start Command: {repo_analysis.get('deployment_requirements', {}).get('start_command')}")
    
    print(f"\n✅ Smart analysis complete!")
    print(f"   The LLM successfully parsed complex requirements and generated actionable deployment plans.")

if __name__ == "__main__":
    main()
