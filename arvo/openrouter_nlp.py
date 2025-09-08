"""
OpenRouter API integration with Claude 4.1 Opus Max for NLP extraction.
Replaces regex functionality with LLM-powered extraction while maintaining compatibility.
"""

import os
import json
import requests
from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class DeploymentRequirements:
    """Type-safe container for deployment requirements."""
    cloud: str = "aws"
    infra: str = "vm"
    region: str = "us-west-2"
    instance_size: str = "small"
    framework: Optional[str] = None
    port: Optional[int] = None
    domain: Optional[str] = None
    ssl: bool = False
    autoscale: bool = False
    database: bool = False
    load_balancer: bool = False
    monitoring: bool = False
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DeploymentRequirements':
        """Safely create from dictionary with type validation."""
        return cls(
            cloud=str(data.get("cloud", "aws")),
            infra=str(data.get("infra", "vm")),
            region=str(data.get("region", "us-west-2")),
            instance_size=str(data.get("instance_size", "small")),
            framework=data.get("framework"),
            port=int(data["port"]) if data.get("port") is not None else None,
            domain=data.get("domain"),
            ssl=bool(data.get("ssl", False)),
            autoscale=bool(data.get("autoscale", False)),
            database=bool(data.get("database", False)),
            load_balancer=bool(data.get("load_balancer", False)),
            monitoring=bool(data.get("monitoring", False))
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for compatibility with existing code."""
        return {
            "cloud": self.cloud,
            "infra": self.infra,
            "region": self.region,
            "instance_size": self.instance_size,
            "framework": self.framework,
            "port": self.port,
            "domain": self.domain,
            "ssl": self.ssl,
            "autoscale": self.autoscale,
            "database": self.database,
            "load_balancer": self.load_balancer,
            "monitoring": self.monitoring
        }


class OpenRouterNLP:
    """OpenRouter API integration with Claude 4.1 Opus Max for deployment requirements extraction."""
    
    def __init__(self):
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        self.base_url = "https://openrouter.ai/api/v1"
        self.model = "anthropic/claude-3-5-sonnet-20241022"  # Claude 4.1 Opus Max equivalent
        self.timeout = 30
    
    def extract_deployment_requirements(self, instructions: str) -> Dict[str, Any]:
        """
        Extract deployment requirements using Claude 4.1 Opus Max via OpenRouter.
        Falls back to regex system if LLM fails.
        
        Args:
            instructions: Natural language deployment instructions
            
        Returns:
            Dictionary with extracted requirements (same format as regex system)
        """
        print(f"🤖 Using Claude 4.1 Opus Max to extract requirements from: '{instructions}'")
        
        # Try LLM extraction first
        try:
            llm_result = self._extract_with_llm(instructions)
            if llm_result:
                print("✅ Claude 4.1 Opus Max extraction successful")
                return llm_result.to_dict()
        except Exception as e:
            print(f"❌ Claude 4.1 Opus Max extraction failed: {e}")
            print("🔄 Falling back to regex system...")
        
        # Fallback to regex (guaranteed to work)
        return self._extract_with_regex(instructions)
    
    def _extract_with_llm(self, instructions: str) -> DeploymentRequirements:
        """Extract using Claude 4.1 Opus Max with strict JSON schema."""
        
        prompt = f"""
        You are an expert DevOps engineer. Analyze the deployment instructions and extract specific requirements.

        Instructions: "{instructions}"

        Extract these EXACT fields and return ONLY a valid JSON object:
        {{
            "cloud": "aws",
            "infra": "vm", 
            "region": "us-west-2",
            "instance_size": "small",
            "framework": null,
            "port": null,
            "domain": null,
            "ssl": false,
            "autoscale": false,
            "database": false,
            "load_balancer": false,
            "monitoring": false
        }}

        Field Rules:
        - cloud: "aws", "gcp", "azure" (default: "aws")
        - infra: "vm", "serverless", "kubernetes" (default: "vm")
        - region: AWS region like "us-west-2", "us-east-1" (default: "us-west-2")
        - instance_size: "micro", "small", "medium", "large" (default: "small")
        - framework: "flask", "django", "fastapi", "express", "nextjs", "react" or null
        - port: integer port number or null
        - domain: domain name string or null
        - ssl: true/false (for HTTPS/SSL requirements)
        - autoscale: true/false (for auto-scaling requirements)
        - database: true/false (for database requirements)
        - load_balancer: true/false (for load balancer requirements)
        - monitoring: true/false (for monitoring/logging requirements)

        IMPORTANT:
        - Use boolean values (true/false) NOT objects
        - Use null for missing optional fields
        - Use strings for all text fields
        - Use integers for port numbers
        - Be conservative with resource requirements
        - Return ONLY the JSON object, no explanations

        JSON:
        """
        
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://github.com/arvo-ai/arvo",
                    "X-Title": "Arvo Deployment System"
                },
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.1,
                    "max_tokens": 500
                },
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                content = response.json()["choices"][0]["message"]["content"]
                print(f"📝 Claude response: {content[:200]}...")
                
                # Clean and parse JSON
                json_str = self._extract_json_from_response(content)
                data = json.loads(json_str)
                
                # Validate and normalize
                return self._validate_llm_output(data)
            else:
                raise Exception(f"OpenRouter API error: {response.status_code} - {response.text}")
                
        except Exception as e:
            raise Exception(f"LLM extraction failed: {e}")
    
    def _extract_json_from_response(self, content: str) -> str:
        """Extract JSON from Claude response, handling common formatting issues."""
        # Remove markdown code blocks
        content = content.replace("```json", "").replace("```", "")
        content = content.strip()
        
        # Find JSON object boundaries
        start = content.find("{")
        end = content.rfind("}") + 1
        
        if start != -1 and end != -1:
            return content[start:end]
        else:
            raise ValueError("No valid JSON found in Claude response")
    
    def _validate_llm_output(self, data: Dict[str, Any]) -> DeploymentRequirements:
        """Validate Claude output and ensure type safety."""
        
        # Normalize boolean fields (handle both true/false and "true"/"false")
        boolean_fields = ["ssl", "autoscale", "database", "load_balancer", "monitoring"]
        for field in boolean_fields:
            if field in data:
                value = data[field]
                if isinstance(value, str):
                    data[field] = value.lower() in ["true", "1", "yes", "on"]
                elif isinstance(value, (int, float)):
                    data[field] = bool(value)
                else:
                    data[field] = bool(value)
        
        # Normalize string fields
        string_fields = ["cloud", "infra", "region", "instance_size", "framework", "domain"]
        for field in string_fields:
            if field in data and data[field] is not None:
                data[field] = str(data[field])
        
        # Normalize port
        if "port" in data and data["port"] is not None:
            try:
                data["port"] = int(data["port"])
            except (ValueError, TypeError):
                data["port"] = None
        
        return DeploymentRequirements.from_dict(data)
    
    def _extract_with_regex(self, instructions: str) -> Dict[str, Any]:
        """Fallback to regex extraction (guaranteed to work)."""
        print("🔧 Using regex fallback system...")
        from arvo.simple_nlp import extract_deployment_requirements
        return extract_deployment_requirements(instructions)


# Backward compatibility function
def extract_deployment_requirements(instructions: str) -> Dict[str, Any]:
    """
    Main extraction function that uses OpenRouter with Claude 4.1 Opus Max.
    This replaces the regex function in simple_nlp.py with the same interface.
    """
    nlp = OpenRouterNLP()
    return nlp.extract_deployment_requirements(instructions)
