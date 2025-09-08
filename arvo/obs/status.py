"""
Status derivation from events and log signals.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import json
import time


class DeploymentStatus(Enum):
    """Deployment status states."""
    QUEUED = "queued"
    INIT = "init"
    TF_INIT = "tf_init"
    TF_PLAN = "tf_plan"
    TF_APPLY = "tf_apply"
    BOOTSTRAPPING = "bootstrapping"
    VERIFYING = "verifying"
    HEALTHY = "healthy"
    FAILED = "failed"
    DESTROYING = "destroying"
    DESTROYED = "destroyed"


@dataclass
class StatusInfo:
    """Comprehensive status information."""
    status: DeploymentStatus
    message: str
    last_event: Optional[Dict[str, Any]] = None
    failure_reason: Optional[str] = None
    failure_hint: Optional[str] = None
    public_url: Optional[str] = None
    log_links: Optional[Dict[str, str]] = None
    timestamp: Optional[float] = None


class StatusDeriver:
    """Derives deployment status from events and log signals."""
    
    def __init__(self):
        self.status_transitions = {
            DeploymentStatus.QUEUED: [DeploymentStatus.INIT, DeploymentStatus.FAILED],
            DeploymentStatus.INIT: [DeploymentStatus.TF_INIT, DeploymentStatus.FAILED],
            DeploymentStatus.TF_INIT: [DeploymentStatus.TF_PLAN, DeploymentStatus.FAILED],
            DeploymentStatus.TF_PLAN: [DeploymentStatus.TF_APPLY, DeploymentStatus.FAILED],
            DeploymentStatus.TF_APPLY: [DeploymentStatus.BOOTSTRAPPING, DeploymentStatus.FAILED],
            DeploymentStatus.BOOTSTRAPPING: [DeploymentStatus.VERIFYING, DeploymentStatus.FAILED],
            DeploymentStatus.VERIFYING: [DeploymentStatus.HEALTHY, DeploymentStatus.FAILED],
            DeploymentStatus.HEALTHY: [DeploymentStatus.DESTROYING, DeploymentStatus.FAILED],
            DeploymentStatus.FAILED: [DeploymentStatus.DESTROYING],
            DeploymentStatus.DESTROYING: [DeploymentStatus.DESTROYED, DeploymentStatus.FAILED],
            DeploymentStatus.DESTROYED: []
        }
    
    def derive_status(self, events: List[Dict[str, Any]], outputs: Optional[Dict[str, str]] = None) -> StatusInfo:
        """Derive current status from events and outputs."""
        if not events:
            return StatusInfo(
                status=DeploymentStatus.QUEUED,
                message="No events found",
                timestamp=time.time()
            )
        
        last_event = events[-1]
        event_type = last_event.get("type", "")
        timestamp = last_event.get("timestamp", time.time())
        
        # Check for failure detection first
        failure_info = self._check_for_failures(events)
        if failure_info:
            return StatusInfo(
                status=DeploymentStatus.FAILED,
                message=failure_info["message"],
                last_event=last_event,
                failure_reason=failure_info["reason_code"],
                failure_hint=failure_info["hint"],
                timestamp=timestamp
            )
        
        # Derive status from last significant event
        status = self._derive_from_events(events)
        
        # Get public URL and log links from outputs
        public_url = None
        log_links = None
        if outputs:
            public_url = outputs.get("public_url")
            log_links = self._extract_log_links(outputs)
        
        return StatusInfo(
            status=status,
            message=self._get_status_message(status, last_event),
            last_event=last_event,
            public_url=public_url,
            log_links=log_links,
            timestamp=timestamp
        )
    
    def _check_for_failures(self, events: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Check for FAILURE_DETECTED events."""
        for event in reversed(events):  # Check most recent first
            if event.get("type") == "FAILURE_DETECTED":
                return {
                    "reason_code": event.get("reason_code"),
                    "message": event.get("message"),
                    "hint": event.get("hint"),
                    "severity": event.get("severity")
                }
        return None
    
    def _derive_from_events(self, events: List[Dict[str, Any]]) -> DeploymentStatus:
        """Derive status from event sequence."""
        # Map event types to status
        event_to_status = {
            "INIT": DeploymentStatus.INIT,
            "TF_INIT": DeploymentStatus.TF_INIT,
            "TF_PLAN": DeploymentStatus.TF_PLAN,
            "TF_APPLY_START": DeploymentStatus.TF_APPLY,
            "TF_APPLY_DONE": DeploymentStatus.BOOTSTRAPPING,
            "BOOTSTRAP_WAIT": DeploymentStatus.BOOTSTRAPPING,
            "VERIFY_OK": DeploymentStatus.HEALTHY,
            "DONE": DeploymentStatus.HEALTHY,
            "ERROR": DeploymentStatus.FAILED,
            "DESTROY_START": DeploymentStatus.DESTROYING,
            "DESTROY_DONE": DeploymentStatus.DESTROYED,
        }
        
        # Find the most recent significant event
        for event in reversed(events):
            event_type = event.get("type", "")
            if event_type in event_to_status:
                return event_to_status[event_type]
        
        # Default to queued if no significant events
        return DeploymentStatus.QUEUED
    
    def _get_status_message(self, status: DeploymentStatus, last_event: Dict[str, Any]) -> str:
        """Get human-readable status message."""
        messages = {
            DeploymentStatus.QUEUED: "Deployment queued",
            DeploymentStatus.INIT: "Initializing deployment",
            DeploymentStatus.TF_INIT: "Initializing Terraform",
            DeploymentStatus.TF_PLAN: "Planning infrastructure",
            DeploymentStatus.TF_APPLY: "Applying infrastructure changes",
            DeploymentStatus.BOOTSTRAPPING: "Bootstrapping application",
            DeploymentStatus.VERIFYING: "Verifying deployment",
            DeploymentStatus.HEALTHY: "Deployment successful",
            DeploymentStatus.FAILED: "Deployment failed",
            DeploymentStatus.DESTROYING: "Destroying deployment",
            DeploymentStatus.DESTROYED: "Deployment destroyed"
        }
        
        base_message = messages.get(status, "Unknown status")
        
        # Add context from last event if available
        if last_event.get("message"):
            return f"{base_message}: {last_event['message']}"
        
        return base_message
    
    def _extract_log_links(self, outputs: Dict[str, str]) -> Dict[str, str]:
        """Extract log links from outputs."""
        log_links = {}
        
        # Look for log_links in outputs
        if "log_links" in outputs:
            try:
                log_links = json.loads(outputs["log_links"])
            except (json.JSONDecodeError, TypeError):
                pass
        
        # Extract individual log link fields
        for key, value in outputs.items():
            if key.startswith("log_") and key.endswith("_url"):
                link_name = key[4:-4]  # Remove "log_" prefix and "_url" suffix
                log_links[link_name] = value
        
        return log_links
    
    def is_terminal_status(self, status: DeploymentStatus) -> bool:
        """Check if status is terminal (no further transitions possible)."""
        return status in [DeploymentStatus.HEALTHY, DeploymentStatus.FAILED, DeploymentStatus.DESTROYED]
    
    def can_transition_to(self, current_status: DeploymentStatus, target_status: DeploymentStatus) -> bool:
        """Check if transition from current to target status is valid."""
        return target_status in self.status_transitions.get(current_status, [])
    
    def get_next_possible_statuses(self, current_status: DeploymentStatus) -> List[DeploymentStatus]:
        """Get list of possible next statuses."""
        return self.status_transitions.get(current_status, [])
