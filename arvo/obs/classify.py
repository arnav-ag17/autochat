"""
Failure detection and classification system.
"""

import re
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from enum import Enum


class Severity(Enum):
    """Failure severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class FailureRule:
    """A rule for detecting specific failure patterns."""
    id: str
    name: str
    regexes: List[str]
    message: str
    hint: str
    severity: Severity
    context: Optional[str] = None  # Additional context for the failure


class FailureClassifier:
    """Classifies failures from log messages using regex patterns."""
    
    def __init__(self):
        self.rules = self._load_default_rules()
        self.detected_failures: Dict[str, FailureRule] = {}
    
    def _load_default_rules(self) -> List[FailureRule]:
        """Load default failure detection rules."""
        return [
            # Python/Dependency errors
            FailureRule(
                id="pip_install_error",
                name="Python Dependencies Failed",
                regexes=[
                    r'pip(3)? install .* (failed|ERROR|Could not find version)',
                    r'ERROR: Could not find a version that satisfies',
                    r'ERROR: No matching distribution found',
                    r'pip install.*returned non-zero exit status'
                ],
                message="Python dependencies failed to install",
                hint="Check requirements.txt and build tools; see CloudWatch stream 'ec2/cloud-init'",
                severity=Severity.HIGH
            ),
            
            FailureRule(
                id="module_not_found",
                name="Python Module Not Found",
                regexes=[
                    r'ModuleNotFoundError: No module named',
                    r'ImportError: No module named',
                    r'ImportError: cannot import name'
                ],
                message="Required Python module not found",
                hint="Check dependencies and virtual environment; ensure all required packages are installed",
                severity=Severity.HIGH
            ),
            
            # Node.js errors
            FailureRule(
                id="npm_error",
                name="Node.js Build Failed",
                regexes=[
                    r'npm ERR!',
                    r'Error: Cannot find module',
                    r'Module not found:',
                    r'npm install.*failed'
                ],
                message="Node.js install/build failed",
                hint="Check package.json, scripts, and lockfile; see stream 'ecs/<service>'",
                severity=Severity.HIGH
            ),
            
            # Network/Port errors
            FailureRule(
                id="address_in_use",
                name="Port Already in Use",
                regexes=[
                    r'Address already in use',
                    r'EADDRINUSE',
                    r'bind: address already in use',
                    r'Port \d+ is already in use'
                ],
                message="Port already in use",
                hint="Choose a different port or stop the other process",
                severity=Severity.MEDIUM
            ),
            
            FailureRule(
                id="connection_refused",
                name="Connection Refused",
                regexes=[
                    r'Connection refused',
                    r'ECONNREFUSED',
                    r'Failed to connect',
                    r'No connection could be made'
                ],
                message="Connection refused",
                hint="Check if the service is running and accessible",
                severity=Severity.MEDIUM
            ),
            
            # Application binding errors
            FailureRule(
                id="bind_loopback",
                name="Bound to Loopback Address",
                regexes=[
                    r'(127\.0\.0\.1|localhost).*bind',
                    r'bind.*(127\.0\.0\.1|localhost)',
                    r'listening on localhost only'
                ],
                message="Application bound to loopback address",
                hint="Patcher should enforce 0.0.0.0 binding; check application configuration",
                severity=Severity.HIGH
            ),
            
            # Permission errors
            FailureRule(
                id="permission_denied",
                name="Permission Denied",
                regexes=[
                    r'Permission denied',
                    r'EACCES',
                    r'Access denied',
                    r'Operation not permitted'
                ],
                message="Permission denied",
                hint="Check file permissions and user privileges",
                severity=Severity.MEDIUM
            ),
            
            # Web server errors
            FailureRule(
                id="uvicorn_import",
                name="ASGI App Import Error",
                regexes=[
                    r'Error loading ASGI app',
                    r'No ASGI app found',
                    r'Failed to import ASGI application'
                ],
                message="Failed to load ASGI application",
                hint="Check application entry point and module path",
                severity=Severity.HIGH
            ),
            
            # Database errors
            FailureRule(
                id="django_migrate",
                name="Database Migration Required",
                regexes=[
                    r'no such table',
                    r'django\.db.*does not exist',
                    r'relation.*does not exist',
                    r'Table.*doesn\'t exist'
                ],
                message="Database migration needed",
                hint="Run database migrations; not provisioned in v1",
                severity=Severity.MEDIUM
            ),
            
            # Health check failures
            FailureRule(
                id="health_check_failed",
                name="Health Check Failed",
                regexes=[
                    r'Health check failed',
                    r'HTTP.*(52[03]|504)',
                    r'Service unhealthy',
                    r'Health check timeout'
                ],
                message="Health check failed",
                hint="Check application startup and health endpoint",
                severity=Severity.MEDIUM
            ),
            
            # Service startup errors
            FailureRule(
                id="service_start_failed",
                name="Service Start Failed",
                regexes=[
                    r'Failed to start.*service',
                    r'systemd.*failed',
                    r'Service.*failed to start',
                    r'Job for.*failed'
                ],
                message="Service failed to start",
                hint="Check service configuration and dependencies",
                severity=Severity.HIGH
            ),
            
            # CloudWatch/Logging errors
            FailureRule(
                id="cloudwatch_error",
                name="CloudWatch Logs Error",
                regexes=[
                    r'CloudWatch.*error',
                    r'Failed to send logs',
                    r'Log group.*not found',
                    r'Access denied.*logs'
                ],
                message="CloudWatch logging error",
                hint="Check IAM permissions for CloudWatch Logs",
                severity=Severity.LOW
            ),
        ]
    
    def classify_message(self, message: str, source: str = "unknown") -> Optional[FailureRule]:
        """Classify a log message and return the first matching failure rule."""
        message_lower = message.lower()
        
        for rule in self.rules:
            for regex_pattern in rule.regexes:
                try:
                    if re.search(regex_pattern, message_lower, re.IGNORECASE):
                        return rule
                except re.error:
                    # Skip invalid regex patterns
                    continue
        
        return None
    
    def detect_failure(self, message: str, source: str = "unknown") -> Optional[Dict[str, Any]]:
        """Detect failure from a log message and return failure details."""
        rule = self.classify_message(message, source)
        
        if rule and rule.id not in self.detected_failures:
            self.detected_failures[rule.id] = rule
            
            return {
                "reason_code": rule.id,
                "name": rule.name,
                "message": rule.message,
                "hint": rule.hint,
                "severity": rule.severity.value,
                "source": source,
                "original_message": message
            }
        
        return None
    
    def get_detected_failures(self) -> Dict[str, FailureRule]:
        """Get all detected failures."""
        return self.detected_failures.copy()
    
    def clear_detected_failures(self):
        """Clear all detected failures."""
        self.detected_failures.clear()
    
    def add_custom_rule(self, rule: FailureRule):
        """Add a custom failure detection rule."""
        self.rules.append(rule)
    
    def get_rule_by_id(self, rule_id: str) -> Optional[FailureRule]:
        """Get a rule by its ID."""
        for rule in self.rules:
            if rule.id == rule_id:
                return rule
        return None
