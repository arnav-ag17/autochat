"""
Robust LLM provider with multiple model support and fallbacks.
"""

import os
import requests
import time
from typing import Dict, Any, Optional


class RobustLLMProvider:
    """Robust LLM provider with fast primary model and fallbacks."""
    
    def __init__(self):
        self.groq_key = os.getenv("GROQ_API_KEY")
        self.openai_key = os.getenv("OPENAI_API_KEY")
        self.hf_key = os.getenv("HUGGINGFACE_API_KEY")
        
        # Model priority: Fast -> Comprehensive -> Fallback
        self.models = [
            {"name": "groq_llama3_instant", "provider": "groq", "model": "llama-3.1-8b-instant", "fast": True},
            {"name": "groq_llama3_70b", "provider": "groq", "model": "llama-3.3-70b-versatile", "fast": False},
            {"name": "groq_compound", "provider": "groq", "model": "groq/compound", "fast": True},
            {"name": "groq_gemma2", "provider": "groq", "model": "gemma2-9b-it", "fast": True},
            {"name": "openai_gpt4", "provider": "openai", "model": "gpt-4o-mini", "fast": False},
            {"name": "openai_gpt35", "provider": "openai", "model": "gpt-3.5-turbo", "fast": False},
            {"name": "huggingface", "provider": "huggingface", "model": "microsoft/DialoGPT-medium", "fast": False}
        ]
    
    def _call_groq(self, prompt: str, model: str = "llama3-8b-8192") -> str:
        """Call Groq API."""
        if not self.groq_key:
            return "No Groq API key"
        
        try:
            response = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.groq_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.1,
                    "max_tokens": 1000
                },
                timeout=15
            )
            
            if response.status_code == 200:
                return response.json()["choices"][0]["message"]["content"]
            else:
                return f"Groq API error: {response.status_code} - {response.text}"
                
        except Exception as e:
            return f"Groq error: {e}"
    
    def _call_openai(self, prompt: str, model: str = "gpt-4o-mini") -> str:
        """Call OpenAI API."""
        if not self.openai_key:
            return "No OpenAI API key"
        
        try:
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.openai_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.1,
                    "max_tokens": 1000
                },
                timeout=15
            )
            
            if response.status_code == 200:
                return response.json()["choices"][0]["message"]["content"]
            else:
                return f"OpenAI API error: {response.status_code} - {response.text}"
                
        except Exception as e:
            return f"OpenAI error: {e}"
    
    def _call_huggingface(self, prompt: str, model: str = "microsoft/DialoGPT-medium") -> str:
        """Call Hugging Face API."""
        if not self.hf_key:
            return "No Hugging Face API key"
        
        try:
            response = requests.post(
                f"https://api-inference.huggingface.co/models/{model}",
                headers={
                    "Authorization": f"Bearer {self.hf_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "inputs": prompt,
                    "parameters": {
                        "max_length": 1000,
                        "temperature": 0.1
                    }
                },
                timeout=15
            )
            
            if response.status_code == 200:
                result = response.json()
                if isinstance(result, list) and len(result) > 0:
                    return result[0].get("generated_text", "No response")
                return str(result)
            else:
                return f"Hugging Face API error: {response.status_code} - {response.text}"
                
        except Exception as e:
            return f"Hugging Face error: {e}"
    
    def call_llm(self, prompt: str, prefer_fast: bool = True) -> str:
        """Call LLM with fallback support."""
        # Sort models by preference
        if prefer_fast:
            sorted_models = sorted(self.models, key=lambda x: (not x["fast"], x["name"]))
        else:
            sorted_models = sorted(self.models, key=lambda x: (x["fast"], x["name"]))
        
        for model_config in sorted_models:
            provider = model_config["provider"]
            model = model_config["model"]
            
            print(f"Trying {provider} with {model}...")
            
            if provider == "groq":
                result = self._call_groq(prompt, model)
            elif provider == "openai":
                result = self._call_openai(prompt, model)
            elif provider == "huggingface":
                result = self._call_huggingface(prompt, model)
            else:
                continue
            
            # Check if result is valid (not an error message)
            if not result.startswith(("No ", "API error:", "error:", "Error:")):
                print(f"✅ Success with {provider} {model}")
                return result
            else:
                print(f"❌ Failed with {provider} {model}: {result}")
                continue
        
        return "All LLM providers failed"


class ComprehensiveNLP:
    """Comprehensive NLP using LLM for deployment requirement extraction."""
    
    def __init__(self):
        self.llm = RobustLLMProvider()
    
    def extract_requirements(self, instructions: str) -> Dict[str, Any]:
        """Extract deployment requirements using LLM."""
        prompt = f"""
        Analyze the following deployment instructions and extract specific requirements.
        Return ONLY a valid JSON object with the exact fields specified.

        Instructions: "{instructions}"

        Extract these fields:
        - cloud: "aws", "gcp", "azure", or "aws" (default)
        - infra: "vm", "serverless", "kubernetes", or "vm" (default)  
        - region: AWS region like "us-west-2", "us-east-1", or "us-west-2" (default)
        - instance_size: "micro", "small", "medium", "large", or "small" (default)
        - framework: "flask", "django", "fastapi", "express", "nextjs", "react", or null
        - port: integer port number or null
        - domain: domain name string or null
        - ssl: true/false
        - autoscale: true/false
        - database: true/false
        - load_balancer: true/false
        - monitoring: true/false

        Return ONLY the JSON object, no other text:
        """
        
        result = self.llm.call_llm(prompt)
        
        # Try to parse JSON from result
        try:
            import json
            # Extract JSON from response
            start = result.find("{")
            end = result.rfind("}") + 1
            if start != -1 and end != -1:
                json_str = result[start:end]
                return json.loads(json_str)
        except:
            pass
        
        # Fallback to default requirements
        return {
            "cloud": "aws",
            "infra": "vm",
            "region": "us-west-2",
            "instance_size": "small",
            "framework": None,
            "port": None,
            "domain": None,
            "ssl": False,
            "autoscale": False,
            "database": False,
            "load_balancer": False,
            "monitoring": False
        }


class ComprehensiveRepositoryAnalyzer:
    """Comprehensive repository analysis using LLM."""
    
    def __init__(self):
        self.llm = RobustLLMProvider()
    
    def analyze_repository(self, repo_path: str) -> Dict[str, Any]:
        """Analyze repository structure and requirements."""
        # Get repository structure
        import os
        from pathlib import Path
        
        repo_files = []
        for root, dirs, files in os.walk(repo_path):
            for file in files:
                if not file.startswith('.') and not any(d.startswith('.') for d in root.split(os.sep)):
                    rel_path = os.path.relpath(os.path.join(root, file), repo_path)
                    repo_files.append(rel_path)
        
        # Limit to first 20 files for prompt
        repo_files = repo_files[:20]
        
        prompt = f"""
        Analyze the following repository structure and determine the application type and requirements.
        Return ONLY a valid JSON object with the exact fields specified.

        Repository files: {repo_files}

        Determine these fields:
        - runtime: "python", "node", "docker", or "static"
        - framework: "flask", "django", "fastapi", "express", "nextjs", "react", or null
        - app_path: relative path to main application directory
        - dependencies: list of main dependencies
        - build_required: true/false
        - start_command: command to start the application

        Return ONLY the JSON object, no other text:
        """
        
        result = self.llm.call_llm(prompt)
        
        # Try to parse JSON from result
        try:
            import json
            start = result.find("{")
            end = result.rfind("}") + 1
            if start != -1 and end != -1:
                json_str = result[start:end]
                return json.loads(json_str)
        except:
            pass
        
        # Fallback analysis
        return {
            "runtime": "python",
            "framework": "flask",
            "app_path": ".",
            "dependencies": ["flask"],
            "build_required": False,
            "start_command": "python app.py"
        }
