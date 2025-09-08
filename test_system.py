#!/usr/bin/env python3
"""Test script to verify Arvo system components are working."""

import requests
import json
import time
import subprocess
import sys
from pathlib import Path

def test_api_health():
    """Test API health endpoint."""
    print("🔍 Testing API health...")
    try:
        response = requests.get("http://localhost:8081/", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ API is healthy: {data['message']}")
            return True
        else:
            print(f"❌ API health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ API health check failed: {e}")
        return False

def test_api_docs():
    """Test API documentation endpoint."""
    print("🔍 Testing API documentation...")
    try:
        response = requests.get("http://localhost:8081/docs", timeout=5)
        if response.status_code == 200 and "swagger" in response.text.lower():
            print("✅ API documentation is accessible")
            return True
        else:
            print(f"❌ API docs failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ API docs failed: {e}")
        return False

def test_web_ui():
    """Test web UI accessibility."""
    print("🔍 Testing web UI...")
    try:
        response = requests.get("http://localhost:3000/", timeout=5)
        if response.status_code == 200 and "Arvo" in response.text:
            print("✅ Web UI is accessible")
            return True
        else:
            print(f"❌ Web UI failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Web UI failed: {e}")
        return False

def test_cli():
    """Test CLI commands."""
    print("🔍 Testing CLI...")
    try:
        # Test help command
        result = subprocess.run([
            sys.executable, "-m", "arvo.cli.main", "--help"
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0 and "Arvo" in result.stdout:
            print("✅ CLI is working")
            return True
        else:
            print(f"❌ CLI failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ CLI failed: {e}")
        return False

def test_nlp_system():
    """Test NLP system."""
    print("🔍 Testing NLP system...")
    try:
        from arvo.nlp.extract import extract_overrides
        
        # Test simple extraction
        overrides, report = extract_overrides("Deploy Flask app on AWS")
        
        if overrides.cloud == "aws" and overrides.confidence > 0:
            print("✅ NLP system is working")
            return True
        else:
            print(f"❌ NLP system failed: {overrides}")
            return False
    except Exception as e:
        print(f"❌ NLP system failed: {e}")
        return False

def test_recipe_system():
    """Test recipe system."""
    print("🔍 Testing recipe system...")
    try:
        from arvo.recipes.registry import select_recipe
        from arvo.analyzer.spec import DeploymentSpec
        
        # Create a test spec
        spec = DeploymentSpec(
            app_path="/test",
            runtime="python",
            framework="flask",
            containerized=False,
            multi_service=False,
            start_command="python app.py",
            port=5000,
            health_path="/",
            needs_build=False,
            build_command=None,
            static_assets=None,
            db_required=False,
            env_required=[],
            env_example_path=None,
            localhost_refs=[],
            loopback_binds=[],
            warnings=[],
            rationale=[],
            manifests={}
        )
        
        recipe = select_recipe(spec, None)
        if recipe and hasattr(recipe, '__class__') and 'Flask' in recipe.__class__.__name__:
            print("✅ Recipe system is working")
            return True
        else:
            print(f"❌ Recipe system failed: {recipe}")
            return False
    except Exception as e:
        print(f"❌ Recipe system failed: {e}")
        return False

def main():
    """Run all tests."""
    print("🚀 Testing Arvo System Components")
    print("=" * 50)
    
    tests = [
        test_api_health,
        test_api_docs,
        test_web_ui,
        test_cli,
        test_nlp_system,
        test_recipe_system
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} crashed: {e}")
        print()
    
    print("=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Arvo system is working correctly.")
        print("\n🌐 Access points:")
        print("  - API: http://localhost:8081/")
        print("  - API Docs: http://localhost:8081/docs")
        print("  - Web UI: http://localhost:3000/")
        print("\n💡 To test a deployment:")
        print("  1. Configure AWS credentials")
        print("  2. Use the web UI or CLI to deploy an app")
        print("  3. Monitor logs and status")
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
