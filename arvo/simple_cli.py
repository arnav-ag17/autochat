"""
Simple CLI for the deployment system.
"""

import argparse
import sys
from .simple_deploy import deploy


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="Deploy applications with natural language")
    parser.add_argument("--instructions", "-i", required=True, help="Deployment instructions")
    parser.add_argument("--repo", "-r", required=True, help="Repository URL")
    parser.add_argument("--region", default="us-west-2", help="AWS region")
    parser.add_argument("--quiet", "-q", action="store_true", help="Quiet mode")
    
    args = parser.parse_args()
    
    try:
        result = deploy(args.instructions, args.repo, args.region)
        
        if result["status"] == "success":
            if not args.quiet:
                print(f"\n🎉 Deployment successful!")
                print(f"📱 Application URL: {result['application_url']}")
                print(f"🔍 Health Check: {result['health_check_url']}")
                print(f"🆔 Instance ID: {result['instance_id']}")
            sys.exit(0)
        else:
            print(f"\n❌ Deployment failed: {result.get('error', 'Unknown error')}")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⏹️  Deployment cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
