"""
LLM-powered NLP system for extracting deployment requirements.
"""

import os
import json
import requests
from typing import Dict, Any, Optional

class LLMNLPProvider:
    """LLM-powered NLP provider using OpenAI API."""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.base_url = "https://api.openai.com/v1/chat/completions"
        
    def extract_deployment_requirements(self, instructions: str) -> Dict[str, Any]:
        """
        Extract deployment requirements using LLM.
        
        Args:
            instructions: Natural language deployment instructions
            
        Returns:
            Dictionary with extracted requirements
        """
        if not self.api_key:
            print("⚠️ No OpenAI API key found. Using fallback NLP.")
            return self._fallback_extraction(instructions)
        
        prompt = f"""
        Analyze these deployment instructions and extract the requirements in JSON format:
        
        Instructions: "{instructions}"
        
        Extract the following information:
        - cloud: aws, gcp, azure (default: aws)
        - infra: vm, serverless, kubernetes (default: vm)
        - region: specific AWS region (default: us-west-2)
        - instance_size: micro, small, medium, large (default: small)
        - framework: flask, django, fastapi, express, nextjs, react (if mentioned)
        - port: specific port number (if mentioned)
        - domain: custom domain (if mentioned)
        - ssl: true/false (if mentioned)
        - autoscale: true/false (if mentioned)
        - database: true/false (if mentioned)
        - load_balancer: true/false (if mentioned)
        - monitoring: true/false (if mentioned)
        
        Return ONLY valid JSON, no other text.
        """
        
        try:
            response = requests.post(
                self.base_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "gpt-3.5-turbo",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.1,
                    "max_tokens": 500
                },
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result["choices"][0]["message"]["content"].strip()
                
                # Try to parse JSON
                try:
                    return json.loads(content)
                except json.JSONDecodeError:
                    print(f"⚠️ LLM returned invalid JSON: {content}")
                    return self._fallback_extraction(instructions)
            else:
                print(f"⚠️ LLM API error: {response.status_code}")
                return self._fallback_extraction(instructions)
                
        except Exception as e:
            print(f"⚠️ LLM API failed: {e}")
            return self._fallback_extraction(instructions)
    
    def _fallback_extraction(self, instructions: str) -> Dict[str, Any]:
        """Fallback to simple pattern matching."""
        from .simple_nlp import extract_deployment_requirements
        return extract_deployment_requirements(instructions)


class GitHubAnalyzer:
    """GitHub API-powered repository analyzer."""
    
    def __init__(self, token: Optional[str] = None):
        self.token = token or os.getenv("GITHUB_TOKEN")
        self.base_url = "https://api.github.com"
        
    def analyze_repository(self, repo_url: str) -> Dict[str, Any]:
        """
        Analyze repository using GitHub API.
        
        Args:
            repo_url: GitHub repository URL
            
        Returns:
            Dictionary with analysis results
        """
        if not self.token:
            print("⚠️ No GitHub token found. Using fallback analysis.")
            return self._fallback_analysis(repo_url)
        
        # Extract owner/repo from URL
        try:
            if "github.com" in repo_url:
                parts = repo_url.replace("https://github.com/", "").split("/")
                owner, repo = parts[0], parts[1]
            else:
                raise ValueError("Invalid GitHub URL")
        except:
            return self._fallback_analysis(repo_url)
        
        try:
            # Get repository info
            repo_response = requests.get(
                f"{self.base_url}/repos/{owner}/{repo}",
                headers={"Authorization": f"token {self.token}"},
                timeout=10
            )
            
            if repo_response.status_code != 200:
                return self._fallback_analysis(repo_url)
            
            repo_data = repo_response.json()
            
            # Get repository contents
            contents_response = requests.get(
                f"{self.base_url}/repos/{owner}/{repo}/contents",
                headers={"Authorization": f"token {self.token}"},
                timeout=10
            )
            
            if contents_response.status_code != 200:
                return self._fallback_analysis(repo_url)
            
            contents = contents_response.json()
            
            # Analyze using LLM
            analysis = self._llm_analyze_repo(repo_data, contents)
            return analysis
            
        except Exception as e:
            print(f"⚠️ GitHub API failed: {e}")
            return self._fallback_analysis(repo_url)
    
    def _llm_analyze_repo(self, repo_data: Dict, contents: list) -> Dict[str, Any]:
        """Use LLM to analyze repository structure."""
        if not self.token:  # No LLM available
            return self._fallback_analysis("")
        
        # Create a summary of the repository
        repo_summary = f"""
        Repository: {repo_data.get('name', 'unknown')}
        Description: {repo_data.get('description', 'No description')}
        Language: {repo_data.get('language', 'unknown')}
        Size: {repo_data.get('size', 0)} KB
        
        Top-level files:
        """
        
        for item in contents[:10]:  # Limit to first 10 items
            repo_summary += f"- {item.get('name', 'unknown')} ({item.get('type', 'unknown')})\n"
        
        prompt = f"""
        Analyze this repository and determine:
        1. What type of application this is
        2. What framework it uses
        3. Where the main application code is located
        4. What dependencies it needs
        5. How to run it
        
        Repository info:
        {repo_summary}
        
        Return JSON with:
        - runtime: python, node, static, unknown
        - framework: flask, django, fastapi, express, nextjs, react, static, unknown
        - app_path: relative path to main app code (e.g., "app", "src", ".")
        - start_command: how to start the app (e.g., "python app.py", "npm start")
        - needs_build: true/false
        - build_command: build command if needed
        - port: default port number
        - dependencies: list of main dependencies
        
        Return ONLY valid JSON, no other text.
        """
        
        try:
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "gpt-3.5-turbo",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.1,
                    "max_tokens": 500
                },
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result["choices"][0]["message"]["content"].strip()
                
                try:
                    return json.loads(content)
                except json.JSONDecodeError:
                    print(f"⚠️ LLM returned invalid JSON: {content}")
                    return self._fallback_analysis("")
            else:
                return self._fallback_analysis("")
                
        except Exception as e:
            print(f"⚠️ LLM analysis failed: {e}")
            return self._fallback_analysis("")
    
    def _fallback_analysis(self, repo_url: str) -> Dict[str, Any]:
        """Fallback to local analysis."""
        from .simple_analyzer import analyze_repository
        # This would need the repo to be cloned locally first
        return {
            "runtime": "unknown",
            "framework": "unknown", 
            "app_path": ".",
            "start_command": None,
            "needs_build": False,
            "build_command": None,
            "port": 8080,
            "dependencies": []
        }
