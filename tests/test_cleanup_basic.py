"""
Basic tests for cleanup and tagging functionality.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, mock_open
from arvo.tags import base_tags, parse_user_tags, add_ttl_tags, is_expired
from arvo.cost import estimate_cost, format_cost_hint, should_show_cost_warning
from arvo.cleanup.models import FoundResource


class TestTags:
    """Test tagging functionality."""
    
    def test_base_tags(self):
        """Test base tag generation."""
        tags = base_tags("d-12345")
        
        assert tags["project"] == "arvo"
        assert tags["deployment_id"] == "d-12345"
        assert "created_at" in tags
        assert tags["created_at"].endswith("Z")
    
    def test_base_tags_with_extra(self):
        """Test base tags with extra tags."""
        extra = {"owner": "test-user", "stage": "dev"}
        tags = base_tags("d-12345", extra)
        
        assert tags["project"] == "arvo"
        assert tags["deployment_id"] == "d-12345"
        assert tags["owner"] == "test-user"
        assert tags["stage"] == "dev"
    
    def test_parse_user_tags(self):
        """Test parsing user tag strings."""
        tag_strings = ["owner=test-user", "stage=dev", "env=production"]
        tags = parse_user_tags(tag_strings)
        
        assert tags["owner"] == "test-user"
        assert tags["stage"] == "dev"
        assert tags["env"] == "production"
    
    def test_parse_user_tags_invalid(self):
        """Test parsing invalid tag strings."""
        with pytest.raises(ValueError, match="Invalid tag format"):
            parse_user_tags(["invalid-tag"])
        
        with pytest.raises(ValueError, match="Key and value must not be empty"):
            parse_user_tags(["=value"])
        
        with pytest.raises(ValueError, match="Key and value must not be empty"):
            parse_user_tags(["key="])
    
    def test_add_ttl_tags(self):
        """Test adding TTL tags."""
        base = {"project": "arvo", "deployment_id": "d-12345"}
        tags_with_ttl = add_ttl_tags(base, 24)
        
        assert tags_with_ttl["ttl_hours"] == "24"
        assert "expires_at" in tags_with_ttl
        assert tags_with_ttl["expires_at"].endswith("Z")
    
    def test_is_expired(self):
        """Test expiration checking."""
        from datetime import datetime, timedelta
        
        # Not expired
        future_time = datetime.utcnow() + timedelta(hours=1)
        tags_not_expired = {"expires_at": future_time.isoformat() + "Z"}
        assert not is_expired(tags_not_expired)
        
        # Expired
        past_time = datetime.utcnow() - timedelta(hours=1)
        tags_expired = {"expires_at": past_time.isoformat() + "Z"}
        assert is_expired(tags_expired)
        
        # No expiration
        tags_no_ttl = {"project": "arvo"}
        assert not is_expired(tags_no_ttl)


class TestCost:
    """Test cost estimation functionality."""
    
    def test_format_cost_hint_with_cost(self):
        """Test formatting cost hint with cost data."""
        cost_data = {
            "method": "heuristic",
            "monthly_usd": 15.50,
            "hint": "EC2 t3.small instance"
        }
        
        hint = format_cost_hint(cost_data)
        assert "~$16/month" in hint  # Rounded to nearest dollar
        assert "EC2 t3.small instance" in hint
    
    def test_format_cost_hint_without_cost(self):
        """Test formatting cost hint without cost data."""
        cost_data = {
            "method": "heuristic",
            "monthly_usd": None,
            "hint": "Cost estimation not available"
        }
        
        hint = format_cost_hint(cost_data)
        assert "Cost estimation not available" in hint
    
    def test_should_show_cost_warning(self):
        """Test cost warning logic."""
        # Should show warning for high cost
        assert should_show_cost_warning(100.0, 50.0)
        
        # Should not show warning for low cost
        assert not should_show_cost_warning(25.0, 50.0)
        
        # Should not show warning if cost is None
        assert not should_show_cost_warning(None, 50.0)
    
    @patch('subprocess.run')
    def test_estimate_cost_infracost_success(self, mock_run):
        """Test cost estimation with Infracost success."""
        # Mock successful infracost run
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = '''
        {
            "projects": [
                {
                    "breakdown": {
                        "resources": [
                            {"monthlyCost": "15.50"},
                            {"monthlyCost": "3.25"}
                        ]
                    }
                }
            ]
        }
        '''
        mock_run.return_value = mock_result
        
        cost_data = estimate_cost("/fake/path")
        
        assert cost_data["method"] == "infracost"
        assert cost_data["monthly_usd"] == 18.75
    
    def test_estimate_cost_heuristic_ec2_simple(self):
        """Test heuristic cost estimation for EC2 with simple mocking."""
        # Test the heuristic function directly
        from arvo.cost import _heuristic_cost_estimate
        
        cost_data = _heuristic_cost_estimate("/fake/path/ec2_web", "us-west-2")
        
        assert cost_data["method"] == "heuristic"
        assert cost_data["monthly_usd"] is not None
        assert "EC2" in cost_data.get("hint", "")


class TestCleanupModels:
    """Test cleanup data models."""
    
    def test_found_resource(self):
        """Test FoundResource model."""
        resource = FoundResource(
            service="ec2",
            arn_or_id="i-1234567890abcdef0",
            tags={"project": "arvo", "deployment_id": "d-12345"},
            reason="Tagged with project=arvo"
        )
        
        assert resource.service == "ec2"
        assert resource.arn_or_id == "i-1234567890abcdef0"
        assert resource.tags["project"] == "arvo"
        assert resource.reason == "Tagged with project=arvo"
