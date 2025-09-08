#!/usr/bin/env python3
"""
Script to easily switch between OpenRouter (Claude 4.1 Opus Max) and regex NLP systems.
"""

import os
import sys
import shutil

def switch_to_openrouter():
    """Switch to OpenRouter system with Claude 4.1 Opus Max."""
    print("🔄 Switching to OpenRouter system with Claude 4.1 Opus Max...")
    
    # Update simple_deploy.py to use OpenRouter
    with open('arvo/simple_deploy.py', 'r') as f:
        content = f.read()
    
    content = content.replace(
        'from .simple_nlp import extract_deployment_requirements',
        'from .openrouter_nlp import extract_deployment_requirements'
    )
    
    with open('arvo/simple_deploy.py', 'w') as f:
        f.write(content)
    
    print("✅ Switched to OpenRouter system with Claude 4.1 Opus Max")
    print("🤖 Now using: Claude 4.1 Opus Max via OpenRouter API")
    print("🔄 Automatic fallback to regex if LLM fails")

def switch_to_regex():
    """Switch back to regex system."""
    print("🔄 Switching back to regex system...")
    
    # Update simple_deploy.py to use regex
    with open('arvo/simple_deploy.py', 'r') as f:
        content = f.read()
    
    content = content.replace(
        'from .openrouter_nlp import extract_deployment_requirements',
        'from .simple_nlp import extract_deployment_requirements'
    )
    
    with open('arvo/simple_deploy.py', 'w') as f:
        f.write(content)
    
    print("✅ Switched back to regex system")
    print("🔧 Now using: Fast regex pattern matching")
    print("⚡ Fast and reliable, no API dependencies")

def show_status():
    """Show current NLP system status."""
    with open('arvo/simple_deploy.py', 'r') as f:
        content = f.read()
    
    if 'openrouter_nlp' in content:
        print("🤖 Current system: OpenRouter with Claude 4.1 Opus Max")
        print("🔄 Has automatic fallback to regex")
    elif 'simple_nlp' in content:
        print("🔧 Current system: Regex pattern matching")
        print("⚡ Fast and reliable")
    else:
        print("❓ Unknown system configuration")

def main():
    if len(sys.argv) < 2:
        print("🔄 Arvo NLP System Switcher")
        print("=" * 30)
        print("Usage:")
        print("  python3 switch_nlp_system.py openrouter  # Use Claude 4.1 Opus Max")
        print("  python3 switch_nlp_system.py regex       # Use regex system")
        print("  python3 switch_nlp_system.py status      # Show current system")
        print()
        show_status()
        return
    
    command = sys.argv[1].lower()
    
    if command == "openrouter":
        switch_to_openrouter()
    elif command == "regex":
        switch_to_regex()
    elif command == "status":
        show_status()
    else:
        print(f"❌ Unknown command: {command}")
        print("Available commands: openrouter, regex, status")

if __name__ == "__main__":
    main()
