"""
Observability module for Arvo deployments.

Provides log streaming, failure detection, status derivation, and diagnostic capabilities.
"""

from .stream import StreamManager, LogSource
from .classify import FailureClassifier, FailureRule, Severity
from .status import StatusDeriver, DeploymentStatus
from .diag import DiagnosticReporter
from .cw_links import CloudWatchLinkBuilder

__all__ = [
    "StreamManager",
    "LogSource", 
    "FailureClassifier",
    "FailureRule",
    "Severity",
    "StatusDeriver",
    "DeploymentStatus",
    "DiagnosticReporter",
    "CloudWatchLinkBuilder",
]
