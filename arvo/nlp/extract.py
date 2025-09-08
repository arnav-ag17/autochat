"""
Main extraction orchestrator for NLP processing.
"""

import time
import logging
from typing import Dict, Any, Optional, Tuple
from .schema import Overrides, NLPReport, OVERRIDES_SCHEMA
from .rules import extract_pass_a
from .normalize import validate_and_normalize_overrides
from .providers import get_provider
from .examples import get_examples

logger = logging.getLogger(__name__)


def extract_overrides(
    instructions: str,
    *,
    provider: Optional[str] = None,
    model: Optional[str] = None,
    default_cloud: str = "aws",
    default_region: str = "us-west-2",
    timeout_s: float = 15.0,
) -> Tuple[Overrides, NLPReport]:
    """
    Extract deployment overrides from natural language instructions.
    
    Args:
        instructions: Raw instruction text
        provider: NLP provider to use ("openai", "anthropic", "gemini", "mock")
        model: Provider-specific model hint
        default_cloud: Default cloud provider
        default_region: Default region
        timeout_s: Timeout in seconds
        
    Returns:
        Tuple of (overrides, report)
    """
    start_time = time.time()
    report = NLPReport()
    
    try:
        # Pass A: Deterministic extraction
        logger.debug("Starting Pass A: deterministic extraction")
        pass_a_overrides, pass_a_hits = extract_pass_a(instructions)
        report.passA_hits = pass_a_hits
        
        # Pass B: LLM extraction
        logger.debug("Starting Pass B: LLM extraction")
        pass_b_overrides = _extract_pass_b(instructions, provider, model, timeout_s, report)
        
        # Merge with precedence: Pass A > Pass B > defaults
        merged_overrides = _merge_overrides(pass_a_overrides, pass_b_overrides, default_cloud, default_region)
        
        # Normalize and validate
        normalized_dict, issues = validate_and_normalize_overrides(
            merged_overrides.to_dict(), 
            report.assumptions
        )
        
        # Add issues to assumptions
        report.assumptions.extend(issues)
        
        # Create final overrides
        final_overrides = Overrides.from_dict(normalized_dict)
        
        # Compute confidence
        confidence_score = _compute_confidence(final_overrides, report)
        final_overrides.confidence = confidence_score
        report.confidence = confidence_score
        
        # Add default assumptions if needed
        _add_default_assumptions(final_overrides, report, default_cloud, default_region)
        
    except Exception as e:
        logger.error(f"NLP extraction failed: {e}")
        # Return minimal overrides on error
        final_overrides = Overrides(confidence=0.1)
        report.assumptions.append(f"Extraction failed: {str(e)}")
    
    # Set duration
    report.duration_ms = int((time.time() - start_time) * 1000)
    
    return final_overrides, report


def _extract_pass_b(
    instructions: str, 
    provider: Optional[str], 
    model: Optional[str], 
    timeout_s: float,
    report: NLPReport
) -> Dict[str, Any]:
    """Extract using LLM provider (Pass B)."""
    try:
        nlp_provider = get_provider(provider, model)
        report.raw_provider = f"{nlp_provider.name}:{nlp_provider.model or 'default'}"
        
        examples = get_examples()
        
        # Limit timeout for LLM call
        llm_timeout = min(timeout_s * 0.7, 10.0)  # Use 70% of total timeout, max 10s
        
        logger.debug(f"Calling {nlp_provider.name} provider with timeout {llm_timeout}s")
        
        result = nlp_provider.extract(instructions, OVERRIDES_SCHEMA, examples, llm_timeout)
        
        if result:
            logger.debug(f"LLM extraction successful: {len(result)} fields extracted")
            return result
        else:
            logger.warning("LLM extraction returned empty result")
            report.assumptions.append("LLM unavailable; used rules-only")
            return {}
            
    except Exception as e:
        logger.error(f"LLM extraction failed: {e}")
        report.assumptions.append(f"LLM failed: {str(e)}; used rules-only")
        return {}


def _merge_overrides(
    pass_a: Overrides, 
    pass_b: Dict[str, Any], 
    default_cloud: str, 
    default_region: str
) -> Overrides:
    """Merge overrides with precedence: Pass A > Pass B > defaults."""
    merged = Overrides()
    
    # Convert Pass A to dict for easier merging
    pass_a_dict = pass_a.to_dict()
    
    # Merge with precedence: Pass A > Pass B > defaults
    for field in [
        "cloud", "infra", "region", "instance_size", "instance_type", 
        "containerized", "domain", "ssl", "autoscale", "min_instances", 
        "max_instances", "port", "health_path", "db", "env_overrides", 
        "ttl_hours", "notes", "confidence"
    ]:
        # Pass A takes precedence
        if field in pass_a_dict and pass_a_dict[field] is not None:
            setattr(merged, field, pass_a_dict[field])
        # Then Pass B
        elif field in pass_b and pass_b[field] is not None:
            setattr(merged, field, pass_b[field])
        # Then defaults for specific fields
        elif field == "cloud":
            setattr(merged, field, default_cloud)
        elif field == "region":
            setattr(merged, field, default_region)
    
    # Merge notes from both passes
    notes = []
    if pass_a.notes:
        notes.extend(pass_a.notes)
    if pass_b.get("notes"):
        notes.extend(pass_b["notes"])
    merged.notes = notes
    
    return merged


def _compute_confidence(overrides: Overrides, report: NLPReport) -> float:
    """Compute overall confidence score."""
    confidence = 0.5  # Base confidence
    
    # Boost confidence for specific findings
    if overrides.infra:
        confidence += 0.2
    if overrides.region:
        confidence += 0.2
    if overrides.instance_size or overrides.instance_type:
        confidence += 0.1
    if overrides.domain:
        confidence += 0.1
    if overrides.ssl is not None:
        confidence += 0.1
    
    # Reduce confidence for conflicts
    if report.conflicts:
        confidence -= 0.2 * len(report.conflicts)
    
    # Reduce confidence for many assumptions
    if len(report.assumptions) > 3:
        confidence -= 0.1
    
    # Cap at 1.0
    return min(confidence, 1.0)


def _add_default_assumptions(
    overrides: Overrides, 
    report: NLPReport, 
    default_cloud: str, 
    default_region: str
) -> None:
    """Add default assumptions to report."""
    if not overrides.cloud:
        report.assumptions.append(f"Defaulted cloud to {default_cloud}")
    
    if not overrides.region:
        report.assumptions.append(f"Defaulted region to {default_region}")
    
    if not overrides.infra:
        report.assumptions.append("No infrastructure specified; will be determined by analyzer")
    
    if overrides.ssl and not overrides.domain:
        report.assumptions.append("HTTPS requested but no domain specified; will use default CloudFront domain")


def redact_sensitive_info(text: str) -> str:
    """Redact sensitive information from text before logging."""
    import re
    
    # Redact potential API keys, tokens, passwords
    patterns = [
        (r'[A-Za-z0-9+/]{40,}={0,2}', '[REDACTED_TOKEN]'),  # Base64-like tokens
        (r'[A-Za-z0-9]{32,}', '[REDACTED_KEY]'),  # Long alphanumeric strings
        (r'password\s*[:=]\s*\S+', 'password=[REDACTED]'),
        (r'api[_-]?key\s*[:=]\s*\S+', 'api_key=[REDACTED]'),
        (r'token\s*[:=]\s*\S+', 'token=[REDACTED]'),
    ]
    
    redacted = text
    for pattern, replacement in patterns:
        redacted = re.sub(pattern, replacement, redacted, flags=re.IGNORECASE)
    
    return redacted
