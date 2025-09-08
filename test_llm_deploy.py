#!/usr/bin/env python3
"""
Test script for LLM-powered deployment system.
"""

import os
import sys
from arvo.llm_deploy import deploy_with_llm, test_llm_system

def main():
    """Main function."""
    print("🤖 LLM-Powered Deployment System Test")
    print("=" * 50)
    
    # Check for API keys
    openai_key = os.getenv("OPENAI_API_KEY")
    github_token = os.getenv("GITHUB_TOKEN")
    
    print(f"OpenAI API Key: {'✅ Found' if openai_key else '❌ Missing'}")
    print(f"GitHub Token: {'✅ Found' if github_token else '❌ Missing'}")
    
    if not openai_key:
        print("\n⚠️ To use LLM features, set OPENAI_API_KEY environment variable:")
        print("export OPENAI_API_KEY='your-api-key-here'")
        print("\nFalling back to simple NLP...")
    
    if not github_token:
        print("\n⚠️ To use GitHub API features, set GITHUB_TOKEN environment variable:")
        print("export GITHUB_TOKEN='your-github-token-here'")
        print("\nFalling back to local analysis...")
    
    print("\n" + "=" * 50)
    
    # Test the system
    test_llm_system()
    
    # If arguments provided, do a real deployment
    if len(sys.argv) >= 3:
        instructions = sys.argv[1]
        repo_url = sys.argv[2]
        region = sys.argv[3] if len(sys.argv) > 3 else "us-west-2"
        
        print(f"\n🚀 Starting LLM deployment...")
        result = deploy_with_llm(instructions, repo_url, region)
        
        if result["status"] == "success":
            print(f"\n🎉 Deployment successful!")
            print(f"📱 Application URL: {result['application_url']}")
        else:
            print(f"\n❌ Deployment failed: {result.get('error', 'Unknown error')}")
    else:
        print("\nUsage: python3 test_llm_deploy.py '<instructions>' '<repo_url>' [region]")
        print("Example: python3 test_llm_deploy.py 'Deploy this Flask app on AWS with SSL' 'https://github.com/Arvo-AI/hello_world'")

if __name__ == "__main__":
    main()
