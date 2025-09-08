"""
Smart deployment system that actually uses LLM responses effectively.
"""

import os
import json
import requests
from typing import Dict, Any, Optional

def get_free_llm_response(prompt: str, provider: str = "groq") -> str:
    """
    Get LLM response using free APIs.
    
    Args:
        prompt: The prompt to send
        provider: Which provider to use (groq, huggingface, openai)
        
    Returns:
        LLM response text
    """
    if provider == "groq":
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            return "No Groq API key found"
        
        try:
            response = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "llama3-8b-8192",  # Free model
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.1,
                    "max_tokens": 500
                },
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()["choices"][0]["message"]["content"]
            else:
                return f"API error: {response.status_code}"
                
        except Exception as e:
            return f"Error: {e}"
    
    elif provider == "huggingface":
        api_key = os.getenv("HUGGINGFACE_API_KEY")
        if not api_key:
            return "No Hugging Face API key found"
        
        try:
            response = requests.post(
                "https://api-inference.huggingface.co/models/microsoft/DialoGPT-medium",
                headers={"Authorization": f"Bearer {api_key}"},
                json={"inputs": prompt},
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()[0]["generated_text"]
            else:
                return f"API error: {response.status_code}"
                
        except Exception as e:
            return f"Error: {e}"
    
    return "No provider specified"


def smart_analyze_instructions(instructions: str) -> Dict[str, Any]:
    """
    Use LLM to analyze instructions and return actionable deployment plan.
    
    Args:
        instructions: Natural language instructions
        
    Returns:
        Deployment plan with specific actions
    """
    prompt = f"""
    Analyze these deployment instructions and create a specific deployment plan:
    
    Instructions: "{instructions}"
    
    Return a JSON object with:
    1. infrastructure_type: "simple_vm", "scaled_vm", "serverless", "kubernetes"
    2. instance_config: {{"type": "t2.micro", "count": 1, "region": "us-west-2"}}
    3. application_config: {{"framework": "flask", "port": 5000, "needs_database": false}}
    4. security_config: {{"ssl": false, "custom_domain": null, "firewall_rules": []}}
    5. monitoring_config: {{"enabled": false, "alerts": []}}
    6. deployment_steps: ["provision_vm", "install_dependencies", "deploy_app", "configure_ssl"]
    
    Be specific and actionable. Return ONLY valid JSON.
    """
    
    llm_response = get_free_llm_response(prompt)
    
    try:
        # Try to parse JSON from LLM response
        if llm_response.startswith("```json"):
            llm_response = llm_response.replace("```json", "").replace("```", "").strip()
        elif llm_response.startswith("```"):
            llm_response = llm_response.replace("```", "").strip()
        
        plan = json.loads(llm_response)
        return plan
        
    except json.JSONDecodeError:
        # Fallback to simple parsing
        return {
            "infrastructure_type": "simple_vm",
            "instance_config": {"type": "t2.micro", "count": 1, "region": "us-west-2"},
            "application_config": {"framework": "flask", "port": 5000, "needs_database": False},
            "security_config": {"ssl": False, "custom_domain": None, "firewall_rules": []},
            "monitoring_config": {"enabled": False, "alerts": []},
            "deployment_steps": ["provision_vm", "install_dependencies", "deploy_app"],
            "llm_error": llm_response
        }


def smart_analyze_repository(repo_url: str) -> Dict[str, Any]:
    """
    Use LLM to analyze repository and return deployment strategy.
    
    Args:
        repo_url: GitHub repository URL
        
    Returns:
        Repository analysis with deployment strategy
    """
    prompt = f"""
    Analyze this GitHub repository and create a deployment strategy:
    
    Repository: {repo_url}
    
    Return a JSON object with:
    1. app_type: "web_app", "api", "static_site", "microservice"
    2. technology_stack: {{"runtime": "python", "framework": "flask", "database": "none"}}
    3. deployment_requirements: {{"build_needed": false, "dependencies": ["flask"], "start_command": "python app.py"}}
    4. infrastructure_needs: {{"compute": "low", "storage": "minimal", "network": "standard"}}
    5. deployment_strategy: {{"method": "direct_deploy", "steps": ["clone", "install", "run"]}}
    
    Be specific about how to deploy this repository. Return ONLY valid JSON.
    """
    
    llm_response = get_free_llm_response(prompt)
    
    try:
        if llm_response.startswith("```json"):
            llm_response = llm_response.replace("```json", "").replace("```", "").strip()
        elif llm_response.startswith("```"):
            llm_response = llm_response.replace("```", "").strip()
        
        analysis = json.loads(llm_response)
        return analysis
        
    except json.JSONDecodeError:
        # Fallback analysis
        return {
            "app_type": "web_app",
            "technology_stack": {"runtime": "python", "framework": "flask", "database": "none"},
            "deployment_requirements": {"build_needed": False, "dependencies": ["flask"], "start_command": "python app.py"},
            "infrastructure_needs": {"compute": "low", "storage": "minimal", "network": "standard"},
            "deployment_strategy": {"method": "direct_deploy", "steps": ["clone", "install", "run"]},
            "llm_error": llm_response
        }


def execute_deployment_plan(plan: Dict[str, Any], repo_analysis: Dict[str, Any], repo_url: str) -> Dict[str, Any]:
    """
    Execute the deployment plan based on LLM analysis.
    
    Args:
        plan: Deployment plan from LLM
        repo_analysis: Repository analysis from LLM
        repo_url: Repository URL
        
    Returns:
        Deployment result
    """
    print("🤖 Executing LLM-generated deployment plan...")
    
    # Extract actionable information
    infra_type = plan.get("infrastructure_type", "simple_vm")
    instance_config = plan.get("instance_config", {})
    app_config = plan.get("application_config", {})
    security_config = plan.get("security_config", {})
    deployment_steps = plan.get("deployment_steps", [])
    
    print(f"   Infrastructure: {infra_type}")
    print(f"   Instance: {instance_config.get('type', 't2.micro')} in {instance_config.get('region', 'us-west-2')}")
    print(f"   Framework: {app_config.get('framework', 'flask')}")
    print(f"   Port: {app_config.get('port', 5000)}")
    print(f"   SSL: {security_config.get('ssl', False)}")
    print(f"   Steps: {', '.join(deployment_steps)}")
    
    # For now, use our existing deployment system
    # But with the LLM-informed configuration
    from .simple_deploy import deploy
    
    # Convert LLM plan to our deployment format
    instructions = f"Deploy {app_config.get('framework', 'flask')} application on AWS"
    region = instance_config.get('region', 'us-west-2')
    
    result = deploy(instructions, repo_url, region)
    
    # Add LLM analysis to result
    result["llm_plan"] = plan
    result["llm_analysis"] = repo_analysis
    
    return result


def test_smart_deployment():
    """Test the smart deployment system."""
    print("🧪 Testing Smart Deployment System")
    print("=" * 50)
    
    # Test complex instructions
    complex_instructions = """
    I need to deploy a Flask web application on AWS in the us-east-1 region. 
    The app should run on a t2.medium instance with SSL enabled and autoscaling. 
    I also need a PostgreSQL database and monitoring with CloudWatch logs.
    """
    
    print("1. Analyzing complex instructions...")
    plan = smart_analyze_instructions(complex_instructions)
    print(f"   Generated plan: {json.dumps(plan, indent=2)}")
    
    print("\n2. Analyzing repository...")
    repo_analysis = smart_analyze_repository("https://github.com/Arvo-AI/hello_world")
    print(f"   Repository analysis: {json.dumps(repo_analysis, indent=2)}")
    
    print("\n3. Ready to execute deployment plan!")
    return plan, repo_analysis


if __name__ == "__main__":
    test_smart_deployment()
