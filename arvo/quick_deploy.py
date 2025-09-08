"""
Quick deployment CLI tool for Arvo.
"""

import sys
import time
from arvo.simple_deploy import deploy


def main():
    """Quick deployment CLI."""
    if len(sys.argv) < 3:
        print("🚀 Arvo Quick Deploy")
        print("=" * 25)
        print("Usage:")
        print("  python3 -m arvo.quick_deploy \"Deploy this Flask app on AWS\" https://github.com/user/repo")
        print("  python3 -m arvo.quick_deploy \"Deploy this Django app on AWS\" https://github.com/user/repo us-west-2")
        print()
        print("Examples:")
        print("  python3 -m arvo.quick_deploy \"Deploy this Flask application on AWS\" https://github.com/Arvo-AI/hello_world")
        print("  python3 -m arvo.quick_deploy \"Deploy this Node.js app with database\" https://github.com/user/myapp us-east-1")
        return
    
    instructions = sys.argv[1]
    repo_url = sys.argv[2]
    region = sys.argv[3] if len(sys.argv) > 3 else "us-west-2"
    
    print(f"🚀 Starting deployment...")
    print(f"📝 Instructions: {instructions}")
    print(f"📦 Repository: {repo_url}")
    print(f"🌍 Region: {region}")
    print()
    
    start_time = time.time()
    
    try:
        result = deploy(instructions, repo_url, region)
        
        end_time = time.time()
        deployment_time = end_time - start_time
        
        print(f"\n⏱️  Deployment completed in {deployment_time:.1f} seconds")
        
        if result["status"] == "success":
            print(f"✅ Deployment successful!")
            print(f"🌐 Application URL: {result['application_url']}")
            print(f"🔍 Health Check URL: {result['health_check_url']}")
            print(f"🆔 Instance ID: {result.get('instance_id', 'N/A')}")
            
            # Test the application
            print(f"\n🧪 Testing application...")
            import requests
            try:
                response = requests.get(result['application_url'], timeout=10)
                if response.status_code == 200:
                    print(f"✅ Application is responding! (Status: {response.status_code})")
                else:
                    print(f"⚠️  Application responded with status {response.status_code}")
            except Exception as e:
                print(f"⚠️  Application test failed: {e}")
                
        else:
            print(f"❌ Deployment failed: {result.get('error', 'Unknown error')}")
            
    except Exception as e:
        print(f"❌ Deployment error: {e}")


if __name__ == "__main__":
    main()
