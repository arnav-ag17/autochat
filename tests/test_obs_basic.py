"""
Basic tests for observability features.
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from arvo.obs import (
    FailureClassifier, FailureRule, Severity,
    StatusDeriver, DeploymentStatus,
    CloudWatchLinkBuilder,
    DiagnosticReporter
)


class TestFailureClassifier:
    """Test failure detection and classification."""
    
    def test_classify_pip_error(self):
        """Test detection of pip install errors."""
        classifier = FailureClassifier()
        
        # Test pip install failure
        failure = classifier.detect_failure("pip install failed with error", "ec2:cloud-init")
        assert failure is not None
        assert failure["reason_code"] == "pip_install_error"
        assert "Python dependencies failed to install" in failure["message"]
        assert failure["severity"] == "high"
    
    def test_classify_npm_error(self):
        """Test detection of npm errors."""
        classifier = FailureClassifier()
        
        # Test npm error
        failure = classifier.detect_failure("npm ERR! something went wrong", "ecs:task")
        assert failure is not None
        assert failure["reason_code"] == "npm_error"
        assert "Node.js install/build failed" in failure["message"]
    
    def test_classify_address_in_use(self):
        """Test detection of port conflicts."""
        classifier = FailureClassifier()
        
        # Test address in use
        failure = classifier.detect_failure("Address already in use: 8080", "systemd")
        assert failure is not None
        assert failure["reason_code"] == "address_in_use"
        assert "Port already in use" in failure["message"]
    
    def test_classify_bind_loopback(self):
        """Test detection of loopback binding issues."""
        classifier = FailureClassifier()
        
        # Test loopback bind
        failure = classifier.detect_failure("binding to 127.0.0.1:8080", "ec2:cloud-init")
        assert failure is not None
        assert failure["reason_code"] == "bind_loopback"
        assert "bound to loopback address" in failure["message"]
    
    def test_no_failure_detected(self):
        """Test that normal messages don't trigger failures."""
        classifier = FailureClassifier()
        
        # Test normal message
        failure = classifier.detect_failure("Application started successfully", "ec2:cloud-init")
        assert failure is None
    
    def test_detected_failures_tracking(self):
        """Test that detected failures are tracked."""
        classifier = FailureClassifier()
        
        # Detect a failure
        failure = classifier.detect_failure("pip install failed with error", "ec2:cloud-init")
        assert failure is not None
        
        # Check that it's tracked
        detected = classifier.get_detected_failures()
        assert "pip_install_error" in detected
    
    def test_clear_detected_failures(self):
        """Test clearing detected failures."""
        classifier = FailureClassifier()
        
        # Detect a failure
        classifier.detect_failure("pip install failed with error", "ec2:cloud-init")
        assert len(classifier.get_detected_failures()) == 1
        
        # Clear failures
        classifier.clear_detected_failures()
        assert len(classifier.get_detected_failures()) == 0


class TestStatusDeriver:
    """Test status derivation from events."""
    
    def test_derive_healthy_status(self):
        """Test deriving healthy status."""
        deriver = StatusDeriver()
        
        events = [
            {"type": "INIT", "timestamp": 1000},
            {"type": "TF_APPLY_DONE", "timestamp": 2000},
            {"type": "VERIFY_OK", "timestamp": 3000},
            {"type": "DONE", "timestamp": 4000}
        ]
        
        status_info = deriver.derive_status(events)
        assert status_info.status == DeploymentStatus.HEALTHY
        assert "successful" in status_info.message
    
    def test_derive_failed_status(self):
        """Test deriving failed status."""
        deriver = StatusDeriver()
        
        events = [
            {"type": "INIT", "timestamp": 1000},
            {"type": "TF_APPLY_DONE", "timestamp": 2000},
            {"type": "FAILURE_DETECTED", "timestamp": 3000, "reason_code": "pip_install_error", "message": "Python deps failed", "hint": "Check requirements.txt"}
        ]
        
        status_info = deriver.derive_status(events)
        assert status_info.status == DeploymentStatus.FAILED
        assert status_info.failure_reason == "pip_install_error"
        assert status_info.failure_hint == "Check requirements.txt"
    
    def test_derive_in_progress_status(self):
        """Test deriving in-progress status."""
        deriver = StatusDeriver()
        
        events = [
            {"type": "INIT", "timestamp": 1000},
            {"type": "TF_APPLY_START", "timestamp": 2000}
        ]
        
        status_info = deriver.derive_status(events)
        assert status_info.status == DeploymentStatus.TF_APPLY
        assert "Applying infrastructure" in status_info.message
    
    def test_extract_log_links(self):
        """Test extracting log links from outputs."""
        deriver = StatusDeriver()
        
        outputs = {
            "log_links": json.dumps({
                "cloudwatch_group": "https://console.aws.amazon.com/...",
                "ec2_console": "https://console.aws.amazon.com/..."
            })
        }
        
        log_links = deriver._extract_log_links(outputs)
        assert "cloudwatch_group" in log_links
        assert "ec2_console" in log_links
    
    def test_is_terminal_status(self):
        """Test terminal status detection."""
        deriver = StatusDeriver()
        
        assert deriver.is_terminal_status(DeploymentStatus.HEALTHY)
        assert deriver.is_terminal_status(DeploymentStatus.FAILED)
        assert deriver.is_terminal_status(DeploymentStatus.DESTROYED)
        assert not deriver.is_terminal_status(DeploymentStatus.TF_APPLY)


class TestCloudWatchLinkBuilder:
    """Test CloudWatch link building."""
    
    def test_build_log_group_url(self):
        """Test building log group URL."""
        builder = CloudWatchLinkBuilder("us-west-2")
        
        url = builder.build_log_group_url("/arvo/d-12345")
        assert "us-west-2" in url
        assert "%2Farvo%2Fd-12345" in url  # URL encoded
        assert "log-groups" in url
    
    def test_build_log_stream_url(self):
        """Test building log stream URL."""
        builder = CloudWatchLinkBuilder("us-west-2")
        
        url = builder.build_log_stream_url("/arvo/d-12345", "ec2/cloud-init")
        assert "us-west-2" in url
        assert "%2Farvo%2Fd-12345" in url  # URL encoded
        assert "ec2%2Fcloud-init" in url  # URL encoded
    
    def test_build_ec2_console_url(self):
        """Test building EC2 console URL."""
        builder = CloudWatchLinkBuilder("us-west-2")
        
        url = builder.build_ec2_console_url("i-1234567890abcdef0")
        assert "us-west-2" in url
        assert "i-1234567890abcdef0" in url
        assert "ec2" in url
    
    def test_build_log_links_ec2(self):
        """Test building comprehensive log links for EC2."""
        builder = CloudWatchLinkBuilder("us-west-2")
        
        outputs = {
            "instance_id": "i-1234567890abcdef0"
        }
        
        links = builder.build_log_links("d-12345", outputs)
        
        assert "cloudwatch_group" in links
        assert "ec2_console" in links
        assert "ec2_cloud_init" in links
        assert "ec2_systemd" in links
    
    def test_build_tail_command(self):
        """Test building AWS CLI tail command."""
        builder = CloudWatchLinkBuilder("us-west-2")
        
        cmd = builder.build_tail_command("/arvo/d-12345", "ec2/cloud-init")
        assert "aws logs tail" in cmd
        assert "/arvo/d-12345" in cmd
        assert "ec2/cloud-init" in cmd
        assert "us-west-2" in cmd
        assert "--follow" in cmd


class TestDiagnosticReporter:
    """Test diagnostic reporting."""
    
    def test_generate_healthy_report(self):
        """Test generating report for healthy deployment."""
        reporter = DiagnosticReporter()
        
        events = [
            {"type": "INIT", "timestamp": 1000},
            {"type": "DONE", "timestamp": 2000}
        ]
        
        report = reporter.generate_report("d-12345", events)
        
        assert report.status == "healthy"
        assert "successful" in report.summary
        assert len(report.failures) == 0
        assert len(report.recommendations) == 0
    
    def test_generate_failed_report(self):
        """Test generating report for failed deployment."""
        reporter = DiagnosticReporter()
        
        events = [
            {"type": "INIT", "timestamp": 1000},
            {"type": "FAILURE_DETECTED", "timestamp": 2000, "reason_code": "pip_install_error", "message": "Python deps failed", "hint": "Check requirements.txt", "severity": "high"}
        ]
        
        report = reporter.generate_report("d-12345", events)
        
        # The status should be "failed" because we have a critical failure
        assert report.status == "failed"
        assert "failed" in report.summary
        assert len(report.failures) == 1
        assert report.failures[0]["reason_code"] == "pip_install_error"
        assert len(report.recommendations) > 0
    
    def test_format_report(self):
        """Test formatting diagnostic report."""
        reporter = DiagnosticReporter()
        
        events = [
            {"type": "INIT", "timestamp": 1000},
            {"type": "FAILURE_DETECTED", "timestamp": 2000, "reason_code": "pip_install_error", "message": "Python deps failed", "hint": "Check requirements.txt", "severity": "high"}
        ]
        
        report = reporter.generate_report("d-12345", events)
        formatted = reporter.format_report(report)
        
        assert "d-12345" in formatted
        assert "FAILED" in formatted
        assert "Python deps failed" in formatted
        assert "Check requirements.txt" in formatted
    
    def test_analyze_failures(self):
        """Test failure analysis."""
        reporter = DiagnosticReporter()
        
        events = [
            {"type": "FAILURE_DETECTED", "timestamp": 1000, "reason_code": "pip_install_error", "message": "Python deps failed", "hint": "Check requirements.txt", "severity": "high"},
            {"type": "FAILURE_DETECTED", "timestamp": 2000, "reason_code": "address_in_use", "message": "Port in use", "hint": "Change port", "severity": "medium"}
        ]
        
        failures = reporter._analyze_failures(events)
        
        assert len(failures) == 2
        # Should be sorted by severity (high first)
        assert failures[0]["reason_code"] == "pip_install_error"
        assert failures[1]["reason_code"] == "address_in_use"
