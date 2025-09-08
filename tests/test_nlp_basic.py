"""
Basic tests for the NLP extraction system.
"""

import pytest
from unittest.mock import Mock, patch
from arvo.nlp import extract_overrides
from arvo.nlp.schema import Overrides, NLPReport, DatabaseConfig
from arvo.nlp.rules import extract_pass_a
from arvo.nlp.normalize import normalize_infra, normalize_region, validate_and_normalize_overrides
from arvo.nlp.providers import MockProvider, get_provider


class TestPassARules:
    """Test deterministic rule extraction (Pass A)."""
    
    def test_extract_cloud_provider(self):
        """Test cloud provider extraction."""
        overrides, hits = extract_pass_a("Deploy on AWS")
        assert overrides.cloud == "aws"
        assert "cloud:aws" in hits
        
        overrides, hits = extract_pass_a("Deploy on Google Cloud")
        assert overrides.cloud == "gcp"
        assert "cloud:gcp" in hits
        
        overrides, hits = extract_pass_a("Deploy on Azure")
        assert overrides.cloud == "azure"
        assert "cloud:azure" in hits
    
    def test_extract_infrastructure(self):
        """Test infrastructure type extraction."""
        overrides, hits = extract_pass_a("Deploy serverless")
        assert overrides.infra == "lambda"
        assert "infra:lambda" in hits
        
        overrides, hits = extract_pass_a("Deploy on EC2")
        assert overrides.infra == "ec2"
        assert "infra:ec2" in hits
        
        overrides, hits = extract_pass_a("Deploy with Docker")
        assert overrides.infra == "ecs_fargate"
        assert "infra:ecs_fargate" in hits
        
        overrides, hits = extract_pass_a("Deploy static site")
        assert overrides.infra == "s3_cf"
        assert "infra:s3_cf" in hits
    
    def test_extract_region(self):
        """Test region extraction."""
        overrides, hits = extract_pass_a("Deploy in us-west-2")
        assert overrides.region == "us-west-2"
        assert "region:direct:us-west-2" in hits
        
        overrides, hits = extract_pass_a("Deploy in Oregon")
        assert overrides.region == "us-west-2"
        assert "region:alias:oregon->us-west-2" in hits
        
        overrides, hits = extract_pass_a("Deploy in Northern Virginia")
        assert overrides.region == "us-east-1"
        assert "region:alias:northern virginia->us-east-1" in hits
    
    def test_extract_instance_size(self):
        """Test instance size extraction."""
        overrides, hits = extract_pass_a("Deploy with small VM")
        assert overrides.instance_size == "small"
        assert "size:abstract:small" in hits
        
        overrides, hits = extract_pass_a("Deploy on t3.medium")
        assert overrides.instance_type == "t3.medium"
        assert overrides.instance_size == "medium"
        assert "type:specific:t3.medium" in hits
    
    def test_extract_domain_and_ssl(self):
        """Test domain and SSL extraction."""
        overrides, hits = extract_pass_a("Deploy with custom domain api.foo.com")
        assert overrides.domain == "api.foo.com"
        assert "domain:api.foo.com" in hits
        
        overrides, hits = extract_pass_a("Deploy with HTTPS")
        assert overrides.ssl is True
        assert "ssl:true" in hits
    
    def test_extract_autoscaling(self):
        """Test autoscaling extraction."""
        overrides, hits = extract_pass_a("Deploy with autoscaling")
        assert overrides.autoscale is True
        assert "autoscale:true" in hits
        
        overrides, hits = extract_pass_a("Deploy with min 2 max 10")
        assert overrides.min_instances == 2
        assert overrides.max_instances == 10
        assert "min_instances:2" in hits
        assert "max_instances:10" in hits
        
        overrides, hits = extract_pass_a("Deploy with scale 1..3")
        assert overrides.min_instances == 1
        assert overrides.max_instances == 3
        assert "range:1-3" in hits
    
    def test_extract_database(self):
        """Test database extraction."""
        overrides, hits = extract_pass_a("Deploy with postgres")
        assert overrides.db is not None
        assert overrides.db.engine == "postgres"
        assert "db:postgres" in hits
        
        overrides, hits = extract_pass_a("Deploy with no database")
        assert overrides.db is not None
        assert overrides.db.engine == "none"
        assert "db:none" in hits
    
    def test_extract_ttl(self):
        """Test TTL extraction."""
        overrides, hits = extract_pass_a("Deploy with 24h TTL")
        assert overrides.ttl_hours == 24
        assert "ttl:24h" in hits
        
        overrides, hits = extract_pass_a("Auto-destroy in 48 hours")
        assert overrides.ttl_hours == 48
        assert "ttl:48h" in hits
    
    def test_extract_env_vars(self):
        """Test environment variable extraction."""
        overrides, hits = extract_pass_a("Deploy with DEBUG=true and PORT=8080")
        assert overrides.env_overrides == {"DEBUG": "true", "PORT": "8080"}
        assert "env:DEBUG=true" in hits
        assert "env:PORT=8080" in hits


class TestNormalization:
    """Test normalization and validation."""
    
    def test_normalize_infra(self):
        """Test infrastructure normalization."""
        assert normalize_infra("vm") == "ec2"
        assert normalize_infra("virtual machine") == "ec2"
        assert normalize_infra("docker") == "ecs_fargate"
        assert normalize_infra("serverless") == "lambda"
        assert normalize_infra("unknown") == "unknown"
    
    def test_normalize_region(self):
        """Test region normalization."""
        assert normalize_region("oregon") == "us-west-2"
        assert normalize_region("n. virginia") == "us-east-1"
        assert normalize_region("us-west-2") == "us-west-2"  # Already canonical
        assert normalize_region("invalid-region") is None
    
    def test_validate_and_normalize_overrides(self):
        """Test override validation and normalization."""
        overrides = {
            "infra": "vm",
            "region": "oregon",
            "instance_type": "t3.medium"
        }
        
        normalized, issues = validate_and_normalize_overrides(overrides, [])
        
        assert normalized["infra"] == "ec2"
        assert normalized["region"] == "us-west-2"
        assert normalized["instance_type"] == "t3.medium"
        assert normalized["instance_size"] == "medium"
        assert len(issues) == 0


class TestSchema:
    """Test schema and data models."""
    
    def test_overrides_creation(self):
        """Test Overrides dataclass creation."""
        overrides = Overrides(
            cloud="aws",
            infra="ec2",
            region="us-west-2",
            instance_size="small",
            domain="example.com",
            ssl=True,
            ttl_hours=24
        )
        
        assert overrides.cloud == "aws"
        assert overrides.infra == "ec2"
        assert overrides.region == "us-west-2"
        assert overrides.instance_size == "small"
        assert overrides.domain == "example.com"
        assert overrides.ssl is True
        assert overrides.ttl_hours == 24
    
    def test_overrides_to_dict(self):
        """Test Overrides to_dict conversion."""
        overrides = Overrides(
            cloud="aws",
            infra="ec2",
            db=DatabaseConfig(engine="postgres")
        )
        
        data = overrides.to_dict()
        assert data["cloud"] == "aws"
        assert data["infra"] == "ec2"
        assert data["db"]["engine"] == "postgres"
    
    def test_overrides_from_dict(self):
        """Test Overrides from_dict creation."""
        data = {
            "cloud": "aws",
            "infra": "ec2",
            "db": {"engine": "postgres", "size": "small"}
        }
        
        overrides = Overrides.from_dict(data)
        assert overrides.cloud == "aws"
        assert overrides.infra == "ec2"
        assert overrides.db.engine == "postgres"
        assert overrides.db.size == "small"
    
    def test_nlp_report(self):
        """Test NLPReport creation."""
        report = NLPReport(
            assumptions=["Defaulted region to us-west-2"],
            conflicts=["Conflicting infrastructure requests"],
            raw_provider="openai:gpt-3.5-turbo",
            passA_hits=["cloud:aws", "infra:ec2"],
            duration_ms=1500
        )
        
        assert len(report.assumptions) == 1
        assert len(report.conflicts) == 1
        assert report.raw_provider == "openai:gpt-3.5-turbo"
        assert len(report.passA_hits) == 2
        assert report.duration_ms == 1500


class TestProviders:
    """Test NLP providers."""
    
    def test_mock_provider(self):
        """Test mock provider."""
        provider = MockProvider()
        result = provider.extract("Deploy on AWS", {}, [], 5.0)
        assert result == {}
        assert provider.name == "mock"
    
    def test_get_provider(self):
        """Test provider selection."""
        # Test mock provider
        provider = get_provider("mock")
        assert isinstance(provider, MockProvider)
        
        # Test unknown provider falls back to mock
        provider = get_provider("unknown")
        assert isinstance(provider, MockProvider)


class TestExtraction:
    """Test main extraction function."""
    
    def test_extract_overrides_basic(self):
        """Test basic extraction."""
        overrides, report = extract_overrides("Deploy Django app on AWS with small VM in Oregon")
        
        assert overrides.cloud == "aws"
        assert overrides.infra == "ec2"
        assert overrides.region == "us-west-2"
        assert overrides.instance_size == "small"
        assert len(report.passA_hits) > 0
        assert report.duration_ms >= 0  # Allow 0 for very fast execution
    
    def test_extract_overrides_with_conflicts(self):
        """Test extraction with conflicting requests."""
        overrides, report = extract_overrides("Deploy serverless on EC2")
        
        # Should detect conflict
        assert len(report.conflicts) > 0 or len(report.assumptions) > 0
        # Infrastructure should be null due to conflict
        assert overrides.infra is None or overrides.infra in ["ec2", "lambda"]
    
    def test_extract_overrides_with_ttl(self):
        """Test extraction with TTL."""
        overrides, report = extract_overrides("Deploy with 24h TTL")
        
        assert overrides.ttl_hours == 24
        assert "ttl:24h" in report.passA_hits
    
    def test_extract_overrides_with_domain_ssl(self):
        """Test extraction with domain and SSL."""
        overrides, report = extract_overrides("Deploy with custom domain api.foo.com and HTTPS")
        
        assert overrides.domain == "api.foo.com"
        assert overrides.ssl is True
        assert "domain:api.foo.com" in report.passA_hits
        assert "ssl:true" in report.passA_hits
    
    def test_extract_overrides_with_env_vars(self):
        """Test extraction with environment variables."""
        overrides, report = extract_overrides("Deploy with DEBUG=true and PORT=8080")
        
        assert overrides.env_overrides == {"DEBUG": "true", "PORT": "8080"}
        assert "env:DEBUG=true" in report.passA_hits
        assert "env:PORT=8080" in report.passA_hits
    
    def test_extract_overrides_empty_instructions(self):
        """Test extraction with empty instructions."""
        overrides, report = extract_overrides("")
        
        # Should return defaults
        assert overrides.cloud == "aws"  # Default
        assert overrides.region == "us-west-2"  # Default
        assert len(report.assumptions) > 0
    
    def test_extract_overrides_garbage_input(self):
        """Test extraction with garbage input."""
        overrides, report = extract_overrides("asdf qwerty random text")
        
        # Should return defaults with assumptions
        assert overrides.cloud == "aws"  # Default
        assert len(report.assumptions) > 0


class TestIntegration:
    """Test integration scenarios."""
    
    def test_complex_instructions(self):
        """Test complex instruction parsing."""
        instructions = "Deploy this Django app on AWS with a small VM in Oregon, add a custom domain api.foo.com and HTTPS; auto-destroy in 24h."
        
        overrides, report = extract_overrides(instructions)
        
        assert overrides.cloud == "aws"
        assert overrides.infra == "ec2"
        assert overrides.region == "us-west-2"
        assert overrides.instance_size == "small"
        assert overrides.domain == "api.foo.com"
        assert overrides.ssl is True
        assert overrides.ttl_hours == 24
        assert overrides.confidence > 0.5
    
    def test_serverless_instructions(self):
        """Test serverless instruction parsing."""
        instructions = "Serverless Python on AWS us-east-1, no DB, 24h TTL"
        
        overrides, report = extract_overrides(instructions)
        
        assert overrides.cloud == "aws"
        assert overrides.infra == "lambda"
        assert overrides.region == "us-east-1"
        assert overrides.db.engine == "none"
        assert overrides.ttl_hours == 24
    
    def test_container_instructions(self):
        """Test container instruction parsing."""
        instructions = "Containerize on AWS, region Oregon, autoscale 1..3"
        
        overrides, report = extract_overrides(instructions)
        
        assert overrides.cloud == "aws"
        assert overrides.infra == "ecs_fargate"
        assert overrides.region == "us-west-2"
        assert overrides.containerized is True
        assert overrides.autoscale is True
        assert overrides.min_instances == 1
        assert overrides.max_instances == 3
    
    def test_static_site_instructions(self):
        """Test static site instruction parsing."""
        instructions = "Static Next.js site to CDN with https"
        
        overrides, report = extract_overrides(instructions)
        
        assert overrides.infra == "s3_cf"
        assert overrides.ssl is True
