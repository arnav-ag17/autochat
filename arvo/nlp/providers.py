"""
Provider interface and adapters for LLM-based extraction.
"""

import json
import time
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
import os

logger = logging.getLogger(__name__)


class NLPProvider(ABC):
    """Abstract base class for NLP providers."""
    
    def __init__(self, model: Optional[str] = None):
        self.model = model
        self.name = self.__class__.__name__.replace("Provider", "").lower()
    
    @abstractmethod
    def extract(self, instructions: str, schema: Dict, examples: List[Dict], timeout_s: float) -> Dict[str, Any]:
        """
        Extract deployment overrides from instructions.
        
        Args:
            instructions: Raw instruction text
            schema: JSON schema for structured output
            examples: Few-shot examples
            timeout_s: Timeout in seconds
            
        Returns:
            Dictionary with extracted overrides
        """
        pass


class MockProvider(NLPProvider):
    """Mock provider for testing and offline use."""
    
    def __init__(self, model: Optional[str] = None):
        super().__init__(model)
        self.name = "mock"
    
    def extract(self, instructions: str, schema: Dict, examples: List[Dict], timeout_s: float) -> Dict[str, Any]:
        """Extract basic deployment requirements using simple pattern matching."""
        logger.debug(f"Mock provider called with instructions: {instructions[:100]}...")
        
        result = {}
        text = instructions.lower()
        
        # Extract cloud provider
        if any(cloud in text for cloud in ['aws', 'amazon']):
            result['cloud'] = 'aws'
        elif any(cloud in text for cloud in ['gcp', 'google', 'google cloud']):
            result['cloud'] = 'gcp'
        elif any(cloud in text for cloud in ['azure', 'microsoft']):
            result['cloud'] = 'azure'
        
        # Extract infrastructure type
        if any(infra in text for infra in ['serverless', 'lambda', 'functions']):
            result['infra'] = 'serverless'
        elif any(infra in text for infra in ['kubernetes', 'k8s', 'container']):
            result['infra'] = 'kubernetes'
        elif any(infra in text for infra in ['vm', 'virtual machine', 'ec2', 'instance']):
            result['infra'] = 'vm'
        
        # Extract region hints
        if 'us-east' in text:
            result['region'] = 'us-east-1'
        elif 'us-west' in text:
            result['region'] = 'us-west-2'
        elif 'eu-west' in text:
            result['region'] = 'eu-west-1'
        
        # Extract instance size hints
        if any(size in text for size in ['small', 'micro', 't2.micro']):
            result['instance_size'] = 'small'
        elif any(size in text for size in ['medium', 't2.medium']):
            result['instance_size'] = 'medium'
        elif any(size in text for size in ['large', 't2.large']):
            result['instance_size'] = 'large'
        
        # Extract framework hints
        if any(fw in text for fw in ['flask', 'python flask']):
            result['framework'] = 'flask'
        elif any(fw in text for fw in ['django', 'python django']):
            result['framework'] = 'django'
        elif any(fw in text for fw in ['fastapi', 'python fastapi']):
            result['framework'] = 'fastapi'
        elif any(fw in text for fw in ['express', 'node express', 'nodejs']):
            result['framework'] = 'express'
        elif any(fw in text for fw in ['next', 'nextjs', 'next.js']):
            result['framework'] = 'nextjs'
        
        # Extract port hints
        import re
        port_match = re.search(r'port\s*:?\s*(\d+)', text)
        if port_match:
            result['port'] = int(port_match.group(1))
        
        # Extract domain hints
        domain_match = re.search(r'domain\s*:?\s*([a-zA-Z0-9.-]+)', text)
        if domain_match:
            result['domain'] = domain_match.group(1)
        
        # Extract SSL hints
        if any(ssl in text for ssl in ['ssl', 'https', 'secure']):
            result['ssl'] = True
        
        # Extract autoscaling hints
        if any(scale in text for scale in ['autoscale', 'auto scale', 'scaling']):
            result['autoscale'] = True
        
        logger.debug(f"Mock provider extracted: {result}")
        return result


class OpenAIProvider(NLPProvider):
    """OpenAI provider using structured outputs."""
    
    def __init__(self, model: Optional[str] = None):
        super().__init__(model or "gpt-3.5-turbo")
        self.name = "openai"
        self.api_key = os.getenv("OPENAI_API_KEY")
    
    def extract(self, instructions: str, schema: Dict, examples: List[Dict], timeout_s: float) -> Dict[str, Any]:
        """Extract using OpenAI API with structured outputs."""
        if not self.api_key:
            logger.warning("OpenAI API key not found")
            return {}
        
        try:
            import openai
            client = openai.OpenAI(api_key=self.api_key)
            
            # Build system prompt
            system_prompt = self._build_system_prompt(schema, examples)
            
            # Make API call with timeout
            start_time = time.time()
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": instructions}
                ],
                response_format={"type": "json_object"},
                temperature=0.1,
                timeout=timeout_s
            )
            
            duration_ms = int((time.time() - start_time) * 1000)
            logger.debug(f"OpenAI API call completed in {duration_ms}ms")
            
            # Parse response
            content = response.choices[0].message.content
            if content:
                return json.loads(content)
            
        except Exception as e:
            logger.error(f"OpenAI API call failed: {e}")
        
        return {}
    
    def _build_system_prompt(self, schema: Dict, examples: List[Dict]) -> str:
        """Build system prompt with schema and examples."""
        prompt = """You are a deployment planner that extracts structured information from natural language instructions.

Output strictly as JSON per the provided schema. Don't invent values; leave unknown fields as null. Produce short 'notes' for nuanced user intent.

Examples:
"""
        
        for i, example in enumerate(examples[:3], 1):  # Limit to 3 examples
            prompt += f"\nExample {i}:\n"
            prompt += f"Input: {example['input']}\n"
            prompt += f"Output: {json.dumps(example['output'], indent=2)}\n"
        
        prompt += f"\nSchema: {json.dumps(schema, indent=2)}\n"
        prompt += "\nNow extract deployment overrides from the user's instructions."
        
        return prompt


class AnthropicProvider(NLPProvider):
    """Anthropic provider using tool use."""
    
    def __init__(self, model: Optional[str] = None):
        super().__init__(model or "claude-3-haiku-20240307")
        self.name = "anthropic"
        self.api_key = os.getenv("ANTHROPIC_API_KEY")
    
    def extract(self, instructions: str, schema: Dict, examples: List[Dict], timeout_s: float) -> Dict[str, Any]:
        """Extract using Anthropic API with tool use."""
        if not self.api_key:
            logger.warning("Anthropic API key not found")
            return {}
        
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=self.api_key)
            
            # Build system prompt
            system_prompt = self._build_system_prompt(schema, examples)
            
            # Make API call
            start_time = time.time()
            response = client.messages.create(
                model=self.model,
                max_tokens=1000,
                temperature=0.1,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": instructions}
                ],
                tools=[{
                    "name": "extract_overrides",
                    "description": "Extract deployment overrides from instructions",
                    "input_schema": schema
                }],
                tool_choice={"type": "tool", "name": "extract_overrides"}
            )
            
            duration_ms = int((time.time() - start_time) * 1000)
            logger.debug(f"Anthropic API call completed in {duration_ms}ms")
            
            # Extract tool use result
            if response.content and response.content[0].type == "tool_use":
                return response.content[0].input
            
        except Exception as e:
            logger.error(f"Anthropic API call failed: {e}")
        
        return {}
    
    def _build_system_prompt(self, schema: Dict, examples: List[Dict]) -> str:
        """Build system prompt with schema and examples."""
        prompt = """You are a deployment planner that extracts structured information from natural language instructions.

Use the extract_overrides tool to output structured data. Don't invent values; leave unknown fields as null. Produce short 'notes' for nuanced user intent.

Examples:
"""
        
        for i, example in enumerate(examples[:3], 1):
            prompt += f"\nExample {i}:\n"
            prompt += f"Input: {example['input']}\n"
            prompt += f"Output: {json.dumps(example['output'], indent=2)}\n"
        
        return prompt


class GeminiProvider(NLPProvider):
    """Google Gemini provider using function calling."""
    
    def __init__(self, model: Optional[str] = None):
        super().__init__(model or "gemini-1.5-flash")
        self.name = "gemini"
        self.api_key = os.getenv("GEMINI_API_KEY")
    
    def extract(self, instructions: str, schema: Dict, examples: List[Dict], timeout_s: float) -> Dict[str, Any]:
        """Extract using Gemini API with function calling."""
        if not self.api_key:
            logger.warning("Gemini API key not found")
            return {}
        
        try:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            
            model = genai.GenerativeModel(self.model)
            
            # Build prompt
            prompt = self._build_prompt(instructions, schema, examples)
            
            # Make API call
            start_time = time.time()
            response = model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.1,
                    max_output_tokens=1000,
                )
            )
            
            duration_ms = int((time.time() - start_time) * 1000)
            logger.debug(f"Gemini API call completed in {duration_ms}ms")
            
            # Parse response
            if response.text:
                # Try to extract JSON from response
                text = response.text.strip()
                if text.startswith("```json"):
                    text = text[7:]
                if text.endswith("```"):
                    text = text[:-3]
                
                return json.loads(text)
            
        except Exception as e:
            logger.error(f"Gemini API call failed: {e}")
        
        return {}
    
    def _build_prompt(self, instructions: str, schema: Dict, examples: List[Dict]) -> str:
        """Build prompt for Gemini."""
        prompt = """You are a deployment planner. Extract structured information from natural language instructions.

Output as JSON per the provided schema. Don't invent values; leave unknown fields as null.

Examples:
"""
        
        for i, example in enumerate(examples[:3], 1):
            prompt += f"\nExample {i}:\n"
            prompt += f"Input: {example['input']}\n"
            prompt += f"Output: {json.dumps(example['output'], indent=2)}\n"
        
        prompt += f"\nSchema: {json.dumps(schema, indent=2)}\n"
        prompt += f"\nInstructions: {instructions}\n"
        prompt += "\nOutput JSON:"
        
        return prompt


def get_provider(provider_name: Optional[str] = None, model: Optional[str] = None) -> NLPProvider:
    """Get NLP provider instance."""
    if not provider_name:
        provider_name = os.getenv("ARVO_NLP_PROVIDER", "mock")
    
    if not model:
        model = os.getenv("ARVO_NLP_MODEL")
    
    providers = {
        "mock": MockProvider,
        "openai": OpenAIProvider,
        "anthropic": AnthropicProvider,
        "gemini": GeminiProvider
    }
    
    provider_class = providers.get(provider_name.lower())
    if not provider_class:
        logger.warning(f"Unknown provider: {provider_name}, using mock")
        provider_class = MockProvider
    
    return provider_class(model)
