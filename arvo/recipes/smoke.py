"""
Smoke testing system for deployed applications.
"""

import time
import requests
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)


class SmokeTestResult:
    """Result of a smoke test."""
    
    def __init__(self, success: bool, message: str, details: Dict[str, Any] = None):
        self.success = success
        self.message = message
        self.details = details or {}


def run_smoke_test(public_url: str, smoke_checks: List[Dict], max_retries: int = 24, retry_delay: int = 5) -> SmokeTestResult:
    """
    Run smoke tests against a deployed application.
    
    Args:
        public_url: Base URL of the deployed application
        smoke_checks: List of smoke check configurations
        max_retries: Maximum number of retry attempts
        retry_delay: Delay between retries in seconds
        
    Returns:
        SmokeTestResult with success status and details
    """
    logger.info(f"Starting smoke tests for {public_url}")
    
    if not smoke_checks:
        return SmokeTestResult(True, "No smoke checks configured")
    
    # Ensure public_url doesn't end with /
    public_url = public_url.rstrip('/')
    
    failed_checks = []
    successful_checks = []
    
    for check in smoke_checks:
        path = check.get("path", "/")
        expected_status = check.get("expect", 200)
        expected_content = check.get("contains")
        max_tries = check.get("max_tries", max_retries)
        
        # Convert single status to list for easier handling
        if isinstance(expected_status, int):
            expected_status = [expected_status]
        
        logger.info(f"Testing {path} (expecting status {expected_status})")
        
        success = False
        last_error = None
        
        for attempt in range(max_tries):
            try:
                # Make request
                url = f"{public_url}{path}"
                response = requests.get(url, timeout=10)
                
                # Check status code
                if response.status_code in expected_status:
                    # Check content if specified
                    if expected_content:
                        if expected_content in response.text:
                            success = True
                            break
                        else:
                            last_error = f"Expected content '{expected_content}' not found in response"
                    else:
                        success = True
                        break
                else:
                    last_error = f"Expected status {expected_status}, got {response.status_code}"
                
            except requests.exceptions.RequestException as e:
                last_error = f"Request failed: {str(e)}"
            
            if attempt < max_tries - 1:
                logger.debug(f"Attempt {attempt + 1} failed, retrying in {retry_delay}s...")
                time.sleep(retry_delay)
        
        if success:
            successful_checks.append({
                "path": path,
                "status": response.status_code,
                "content_check": expected_content is not None
            })
            logger.info(f"✅ {path} passed")
        else:
            failed_checks.append({
                "path": path,
                "expected_status": expected_status,
                "expected_content": expected_content,
                "error": last_error,
                "attempts": max_tries
            })
            logger.error(f"❌ {path} failed: {last_error}")
    
    # Determine overall result
    if failed_checks:
        return SmokeTestResult(
            success=False,
            message=f"Smoke tests failed: {len(failed_checks)}/{len(smoke_checks)} checks failed",
            details={
                "successful_checks": successful_checks,
                "failed_checks": failed_checks,
                "total_checks": len(smoke_checks)
            }
        )
    else:
        return SmokeTestResult(
            success=True,
            message=f"All smoke tests passed: {len(successful_checks)}/{len(smoke_checks)} checks successful",
            details={
                "successful_checks": successful_checks,
                "failed_checks": [],
                "total_checks": len(smoke_checks)
            }
        )


def run_single_smoke_check(public_url: str, check: Dict, timeout: int = 10) -> Dict[str, Any]:
    """
    Run a single smoke check.
    
    Args:
        public_url: Base URL of the deployed application
        check: Single smoke check configuration
        timeout: Request timeout in seconds
        
    Returns:
        Dictionary with check results
    """
    path = check.get("path", "/")
    expected_status = check.get("expect", 200)
    expected_content = check.get("contains")
    
    # Convert single status to list
    if isinstance(expected_status, int):
        expected_status = [expected_status]
    
    try:
        url = f"{public_url.rstrip('/')}{path}"
        response = requests.get(url, timeout=timeout)
        
        result = {
            "path": path,
            "status": response.status_code,
            "success": False,
            "error": None
        }
        
        # Check status code
        if response.status_code in expected_status:
            # Check content if specified
            if expected_content:
                if expected_content in response.text:
                    result["success"] = True
                else:
                    result["error"] = f"Expected content '{expected_content}' not found"
            else:
                result["success"] = True
        else:
            result["error"] = f"Expected status {expected_status}, got {response.status_code}"
        
        return result
        
    except requests.exceptions.RequestException as e:
        return {
            "path": path,
            "status": None,
            "success": False,
            "error": f"Request failed: {str(e)}"
        }
