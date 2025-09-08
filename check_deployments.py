#!/usr/bin/env python3
"""
Deployment Verification Script

This script helps you verify if your deployments are working correctly.
"""

import requests
import json
import sys
from typing import Dict, Any

def check_deployment(url: str, expected_status: int = 200) -> Dict[str, Any]:
    """
    Check if a deployment is working.
    
    Args:
        url: The deployment URL to check
        expected_status: Expected HTTP status code
        
    Returns:
        Dictionary with check results
    """
    result = {
        "url": url,
        "status": "unknown",
        "response_time": None,
        "status_code": None,
        "content_type": None,
        "error": None
    }
    
    try:
        import time
        start_time = time.time()
        
        response = requests.get(url, timeout=10)
        
        result["response_time"] = round((time.time() - start_time) * 1000, 2)  # ms
        result["status_code"] = response.status_code
        result["content_type"] = response.headers.get("content-type", "unknown")
        
        if response.status_code == expected_status:
            result["status"] = "✅ WORKING"
        else:
            result["status"] = f"❌ FAILED (got {response.status_code}, expected {expected_status})"
            
    except requests.exceptions.Timeout:
        result["status"] = "⏰ TIMEOUT"
        result["error"] = "Request timed out after 10 seconds"
    except requests.exceptions.ConnectionError:
        result["status"] = "🔌 CONNECTION ERROR"
        result["error"] = "Could not connect to the server"
    except Exception as e:
        result["status"] = "❌ ERROR"
        result["error"] = str(e)
    
    return result

def check_api_endpoint(base_url: str, endpoint: str = "/api/message") -> Dict[str, Any]:
    """
    Check if an API endpoint is working.
    
    Args:
        base_url: Base URL of the deployment
        endpoint: API endpoint to check
        
    Returns:
        Dictionary with API check results
    """
    api_url = base_url.rstrip('/') + endpoint
    result = check_deployment(api_url)
    
    if result["status"] == "✅ WORKING":
        try:
            response = requests.get(api_url, timeout=5)
            if response.headers.get("content-type", "").startswith("application/json"):
                data = response.json()
                result["api_response"] = data
                result["status"] = "✅ API WORKING"
            else:
                result["status"] = "⚠️ API RESPONDING BUT NOT JSON"
        except:
            result["status"] = "❌ API ERROR"
    
    return result

def main():
    """Main function to check deployments."""
    if len(sys.argv) < 2:
        print("Usage: python3 check_deployments.py <url1> [url2] [url3] ...")
        print("Example: python3 check_deployments.py http://54.149.210.119:5000")
        sys.exit(1)
    
    urls = sys.argv[1:]
    
    print("🔍 Checking Deployments...")
    print("=" * 60)
    
    for url in urls:
        print(f"\n📱 Checking: {url}")
        
        # Check main application
        main_result = check_deployment(url)
        print(f"   Main App: {main_result['status']}")
        
        if main_result["response_time"]:
            print(f"   Response Time: {main_result['response_time']}ms")
        
        if main_result["error"]:
            print(f"   Error: {main_result['error']}")
        
        # Check API endpoint if main app is working
        if main_result["status"] == "✅ WORKING":
            api_result = check_api_endpoint(url)
            print(f"   API Endpoint: {api_result['status']}")
            
            if "api_response" in api_result:
                print(f"   API Response: {api_result['api_response']}")
        
        print("-" * 40)
    
    print("\n✅ Deployment check complete!")

if __name__ == "__main__":
    main()
