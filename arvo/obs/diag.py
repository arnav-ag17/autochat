"""
Diagnostic reporting and failure analysis.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import time


@dataclass
class DiagnosticReport:
    """Comprehensive diagnostic report."""
    deployment_id: str
    status: str
    summary: str
    failures: List[Dict[str, Any]]
    recommendations: List[str]
    log_sources: List[Dict[str, str]]
    next_steps: List[str]
    timestamp: float


class DiagnosticReporter:
    """Generates diagnostic reports from deployment data."""
    
    def __init__(self):
        self.failure_priorities = {
            "critical": 4,
            "high": 3,
            "medium": 2,
            "low": 1
        }
    
    def generate_report(
        self,
        deployment_id: str,
        events: List[Dict[str, Any]],
        outputs: Optional[Dict[str, str]] = None,
        log_streams: Optional[Dict[str, Dict[str, Any]]] = None
    ) -> DiagnosticReport:
        """Generate comprehensive diagnostic report."""
        
        # Analyze events for failures
        failures = self._analyze_failures(events)
        
        # Determine overall status
        status = self._determine_status(events, failures)
        
        # Generate summary
        summary = self._generate_summary(status, failures)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(failures, status)
        
        # Identify log sources
        log_sources = self._identify_log_sources(log_streams, outputs)
        
        # Generate next steps
        next_steps = self._generate_next_steps(status, failures, outputs)
        
        return DiagnosticReport(
            deployment_id=deployment_id,
            status=status,
            summary=summary,
            failures=failures,
            recommendations=recommendations,
            log_sources=log_sources,
            next_steps=next_steps,
            timestamp=time.time()
        )
    
    def _analyze_failures(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Analyze events for failure patterns."""
        failures = []
        
        for event in events:
            if event.get("type") == "FAILURE_DETECTED":
                failure = {
                    "reason_code": event.get("reason_code"),
                    "message": event.get("message"),
                    "hint": event.get("hint"),
                    "severity": event.get("severity", "medium"),
                    "timestamp": event.get("timestamp"),
                    "source": event.get("source", "unknown")
                }
                failures.append(failure)
        
        # Sort by severity (critical first)
        failures.sort(key=lambda f: self.failure_priorities.get(f["severity"], 0), reverse=True)
        
        return failures
    
    def _determine_status(self, events: List[Dict[str, Any]], failures: List[Dict[str, Any]]) -> str:
        """Determine overall deployment status."""
        if not events:
            return "unknown"
        
        last_event = events[-1]
        event_type = last_event.get("type", "")
        
        # Check for explicit status events
        if event_type == "DONE":
            return "healthy"
        elif event_type == "ERROR":
            return "failed"
        elif event_type == "DESTROY_DONE":
            return "destroyed"
        
        # Check for failures
        if failures:
            # Consider high and critical severity as failures
            high_or_critical_failures = [f for f in failures if f["severity"] in ["critical", "high"]]
            if high_or_critical_failures:
                return "failed"
        
        # Check for ongoing processes
        if event_type in ["TF_APPLY_START", "BOOTSTRAP_WAIT"]:
            return "in_progress"
        
        return "unknown"
    
    def _generate_summary(self, status: str, failures: List[Dict[str, Any]]) -> str:
        """Generate human-readable summary."""
        if status == "healthy":
            return "Deployment completed successfully. Application is running and accessible."
        elif status == "failed":
            if failures:
                primary_failure = failures[0]
                return f"Deployment failed: {primary_failure['message']}"
            else:
                return "Deployment failed with unknown error."
        elif status == "in_progress":
            return "Deployment is currently in progress."
        elif status == "destroyed":
            return "Deployment has been destroyed."
        else:
            return "Deployment status is unknown."
    
    def _generate_recommendations(self, failures: List[Dict[str, Any]], status: str) -> List[str]:
        """Generate actionable recommendations."""
        recommendations = []
        
        if status == "failed" and failures:
            # Add specific recommendations for each failure
            for failure in failures[:3]:  # Top 3 failures
                hint = failure.get("hint")
                if hint:
                    recommendations.append(hint)
        
        # Add general recommendations based on status
        if status == "failed":
            recommendations.extend([
                "Check the CloudWatch logs for detailed error information",
                "Verify that all required environment variables are set",
                "Ensure the application can bind to 0.0.0.0 and the specified port"
            ])
        elif status == "in_progress":
            recommendations.append("Wait for the deployment to complete and check logs for progress")
        
        return recommendations
    
    def _identify_log_sources(self, log_streams: Optional[Dict[str, Dict[str, Any]]], outputs: Optional[Dict[str, str]]) -> List[Dict[str, str]]:
        """Identify available log sources."""
        sources = []
        
        if log_streams:
            for stream_id, stream_info in log_streams.items():
                sources.append({
                    "id": stream_id,
                    "name": stream_info.get("source", "unknown"),
                    "description": f"Logs from {stream_info.get('source', 'unknown')}",
                    "console_url": stream_info.get("console_url", ""),
                    "active": stream_info.get("active", False)
                })
        
        # Add CloudWatch log group if available
        if outputs and "log_links" in outputs:
            try:
                import json
                log_links = json.loads(outputs["log_links"])
                if "cloudwatch_group" in log_links:
                    sources.append({
                        "id": "cloudwatch_group",
                        "name": "CloudWatch Logs",
                        "description": "All deployment logs in CloudWatch",
                        "console_url": log_links["cloudwatch_group"],
                        "active": True
                    })
            except (json.JSONDecodeError, TypeError):
                pass
        
        return sources
    
    def _generate_next_steps(self, status: str, failures: List[Dict[str, Any]], outputs: Optional[Dict[str, str]]) -> List[str]:
        """Generate next steps based on current state."""
        next_steps = []
        
        if status == "healthy":
            if outputs and outputs.get("public_url"):
                next_steps.append(f"Access your application at: {outputs['public_url']}")
            next_steps.extend([
                "Monitor application health and performance",
                "Set up additional monitoring if needed"
            ])
        elif status == "failed":
            next_steps.extend([
                "Review the failure details and recommendations above",
                "Check the specific log sources mentioned in the failures",
                "Fix the identified issues and redeploy"
            ])
        elif status == "in_progress":
            next_steps.append("Wait for deployment to complete and monitor progress")
        elif status == "destroyed":
            next_steps.append("Deployment has been successfully destroyed")
        
        return next_steps
    
    def format_report(self, report: DiagnosticReport) -> str:
        """Format diagnostic report as human-readable text."""
        lines = [
            f"🔍 Diagnostic Report for {report.deployment_id}",
            f"Status: {report.status.upper()}",
            f"Summary: {report.summary}",
            ""
        ]
        
        if report.failures:
            lines.append("❌ Failures Detected:")
            for i, failure in enumerate(report.failures, 1):
                lines.append(f"  {i}. {failure['message']} ({failure['severity']})")
                if failure.get('hint'):
                    lines.append(f"     💡 {failure['hint']}")
            lines.append("")
        
        if report.recommendations:
            lines.append("💡 Recommendations:")
            for i, rec in enumerate(report.recommendations, 1):
                lines.append(f"  {i}. {rec}")
            lines.append("")
        
        if report.log_sources:
            lines.append("📊 Available Log Sources:")
            for source in report.log_sources:
                status_icon = "🟢" if source.get("active") else "🔴"
                lines.append(f"  {status_icon} {source['name']}: {source['description']}")
                if source.get("console_url"):
                    lines.append(f"     🔗 {source['console_url']}")
            lines.append("")
        
        if report.next_steps:
            lines.append("🎯 Next Steps:")
            for i, step in enumerate(report.next_steps, 1):
                lines.append(f"  {i}. {step}")
        
        return "\n".join(lines)
