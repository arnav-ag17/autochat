"""
Basic tests for the recipes system.
"""

import pytest
from unittest.mock import Mock, patch
from arvo.recipes import select_recipe, run_smoke_test
from arvo.recipes.base import RecipePlan
from arvo.recipes.python_flask import FlaskRecipe
from arvo.recipes.python_fastapi import FastAPIRecipe
from arvo.recipes.python_django import DjangoRecipe
from arvo.recipes.registry import AVAILABLE_RECIPES
from arvo.analyzer.spec import DeploymentSpec
from arvo.selector import InfraPlan


class TestRecipeSelection:
    """Test recipe selection logic."""
    
    def test_flask_recipe_selection(self):
        """Test Flask recipe selection."""
        spec = DeploymentSpec(
            app_path=".", runtime="python", framework="flask",
            containerized=False, multi_service=False,
            start_command="flask run", port=5000,
            health_path="/", needs_build=False, build_command=None,
            static_assets=None, db_required=False,
            env_required=[], env_example_path=None,
            localhost_refs=[], loopback_binds=[], warnings=[], rationale=[],
            manifests={"requirements.txt": "Flask==2.3.3"}, extra={}
        )
        
        infra_plan = InfraPlan(
            target="ec2", module_hint="ec2_web", parameters={},
            rationale=["Test"], warnings=[], confidence=0.8, fallback_used=False
        )
        
        recipe = select_recipe(spec, infra_plan)
        assert recipe is not None
        assert isinstance(recipe, FlaskRecipe)
    
    def test_fastapi_recipe_selection(self):
        """Test FastAPI recipe selection."""
        spec = DeploymentSpec(
            app_path=".", runtime="python", framework="fastapi",
            containerized=False, multi_service=False,
            start_command="uvicorn main:app", port=8000,
            health_path="/", needs_build=False, build_command=None,
            static_assets=None, db_required=False,
            env_required=[], env_example_path=None,
            localhost_refs=[], loopback_binds=[], warnings=[], rationale=[],
            manifests={"requirements.txt": "fastapi==0.104.1"}, extra={}
        )
        
        infra_plan = InfraPlan(
            target="ec2", module_hint="ec2_web", parameters={},
            rationale=["Test"], warnings=[], confidence=0.8, fallback_used=False
        )
        
        recipe = select_recipe(spec, infra_plan)
        assert recipe is not None
        assert isinstance(recipe, FastAPIRecipe)
    
    def test_django_recipe_selection(self):
        """Test Django recipe selection."""
        spec = DeploymentSpec(
            app_path=".", runtime="python", framework="django",
            containerized=False, multi_service=False,
            start_command="python manage.py runserver", port=8000,
            health_path="/", needs_build=False, build_command=None,
            static_assets=None, db_required=False,
            env_required=[], env_example_path=None,
            localhost_refs=[], loopback_binds=[], warnings=[], rationale=[],
            manifests={"requirements.txt": "Django==4.2.0", "manage.py": "#!/usr/bin/env python"}, extra={}
        )
        
        infra_plan = InfraPlan(
            target="ec2", module_hint="ec2_web", parameters={},
            rationale=["Test"], warnings=[], confidence=0.8, fallback_used=False
        )
        
        recipe = select_recipe(spec, infra_plan)
        assert recipe is not None
        assert isinstance(recipe, DjangoRecipe)
    
    def test_no_suitable_recipe(self):
        """Test when no suitable recipe is found."""
        spec = DeploymentSpec(
            app_path=".", runtime="unknown", framework=None,
            containerized=False, multi_service=False,
            start_command=None, port=None,
            health_path="/", needs_build=False, build_command=None,
            static_assets=None, db_required=False,
            env_required=[], env_example_path=None,
            localhost_refs=[], loopback_binds=[], warnings=[], rationale=[],
            manifests={}, extra={}
        )
        
        infra_plan = InfraPlan(
            target="ec2", module_hint="ec2_web", parameters={},
            rationale=["Test"], warnings=[], confidence=0.8, fallback_used=False
        )
        
        recipe = select_recipe(spec, infra_plan)
        # Some recipe will be selected (Flask gets 10 points for unknown runtime)
        # but it should be a low-scoring match
        assert recipe is not None
        score = recipe.applies(spec)
        assert score <= 20  # Low score for unknown spec


class TestRecipeScoring:
    """Test recipe scoring logic."""
    
    def test_flask_recipe_scoring(self):
        """Test Flask recipe scoring."""
        recipe = FlaskRecipe()
        
        # Perfect Flask match
        spec = DeploymentSpec(
            app_path=".", runtime="python", framework="flask",
            containerized=False, multi_service=False,
            start_command="flask run", port=5000,
            health_path="/", needs_build=False, build_command=None,
            static_assets=None, db_required=False,
            env_required=[], env_example_path=None,
            localhost_refs=[], loopback_binds=[], warnings=[], rationale=[],
            manifests={"requirements.txt": "Flask==2.3.3"}, extra={}
        )
        
        score = recipe.applies(spec)
        assert score >= 80  # Should be high score for perfect match
        
        # Partial Flask match
        spec_partial = DeploymentSpec(
            app_path=".", runtime="unknown", framework=None,
            containerized=False, multi_service=False,
            start_command=None, port=None,
            health_path="/", needs_build=False, build_command=None,
            static_assets=None, db_required=False,
            env_required=[], env_example_path=None,
            localhost_refs=[], loopback_binds=[], warnings=[], rationale=[],
            manifests={"requirements.txt": "Flask==2.3.3"}, extra={}
        )
        
        score_partial = recipe.applies(spec_partial)
        assert 0 < score_partial < score  # Should be lower than perfect match
        
        # No Flask match
        spec_no_flask = DeploymentSpec(
            app_path=".", runtime="node", framework="express",
            containerized=False, multi_service=False,
            start_command="npm start", port=3000,
            health_path="/", needs_build=False, build_command=None,
            static_assets=None, db_required=False,
            env_required=[], env_example_path=None,
            localhost_refs=[], loopback_binds=[], warnings=[], rationale=[],
            manifests={"package.json": '{"dependencies": {"express": "^4.18.2"}}'}, extra={}
        )
        
        score_no_flask = recipe.applies(spec_no_flask)
        assert score_no_flask <= 20  # Should be low score for non-Flask


class TestRecipePlanning:
    """Test recipe planning logic."""
    
    def test_flask_recipe_plan(self):
        """Test Flask recipe planning."""
        recipe = FlaskRecipe()
        
        spec = DeploymentSpec(
            app_path=".", runtime="python", framework="flask",
            containerized=False, multi_service=False,
            start_command="flask run", port=5000,
            health_path="/", needs_build=False, build_command=None,
            static_assets=None, db_required=False,
            env_required=[], env_example_path=None,
            localhost_refs=[], loopback_binds=[], warnings=[], rationale=[],
            manifests={"requirements.txt": "Flask==2.3.3"}, extra={}
        )
        
        infra_plan = InfraPlan(
            target="ec2", module_hint="ec2_web", parameters={},
            rationale=["Test"], warnings=[], confidence=0.8, fallback_used=False
        )
        
        patch_result = {"patched": True, "notes": ["Test patching"]}
        env_inject = {"injected": True, "env_count": 0}
        
        plan = recipe.plan(spec, infra_plan, patch_result, env_inject)
        
        assert isinstance(plan, RecipePlan)
        assert plan.name == "flask"
        assert plan.target == "ec2"
        assert "app_name" in plan.vars
        assert "port" in plan.vars
        assert "health_path" in plan.vars
        assert plan.user_data is not None
        assert len(plan.smoke_checks) > 0
        assert len(plan.rationale) > 0


class TestSmokeTesting:
    """Test smoke testing functionality."""
    
    def test_smoke_test_success(self):
        """Test successful smoke test."""
        smoke_checks = [
            {"path": "/", "expect": 200},
            {"path": "/health", "expect": 200, "contains": "ok"}
        ]
        
        # Mock successful requests
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.text = '{"status": "ok", "health": "healthy"}'
            mock_get.return_value = mock_response
            
            result = run_smoke_test("http://example.com", smoke_checks, max_retries=1, retry_delay=0)
            
            assert result.success is True
            assert "passed" in result.message.lower()
    
    def test_smoke_test_failure(self):
        """Test failed smoke test."""
        smoke_checks = [
            {"path": "/", "expect": 200},
            {"path": "/health", "expect": 200, "contains": "ok"}
        ]
        
        # Mock failed requests
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 404
            mock_response.text = 'Not Found'
            mock_get.return_value = mock_response
            
            result = run_smoke_test("http://example.com", smoke_checks, max_retries=1, retry_delay=0)
            
            assert result.success is False
            assert "failed" in result.message.lower()
    
    def test_smoke_test_no_checks(self):
        """Test smoke test with no checks."""
        result = run_smoke_test("http://example.com", [], max_retries=1, retry_delay=0)
        
        assert result.success is True
        assert "no smoke checks" in result.message.lower()


class TestRecipeRegistry:
    """Test recipe registry functionality."""
    
    def test_available_recipes(self):
        """Test that all expected recipes are available."""
        recipe_names = [recipe.__class__.__name__ for recipe in AVAILABLE_RECIPES]
        
        expected_recipes = [
            "FlaskRecipe",
            "FastAPIRecipe", 
            "DjangoRecipe",
            "NodeExpressRecipe",
            "NextStaticRecipe",
            "DockerizedRecipe"
        ]
        
        for expected in expected_recipes:
            assert expected in recipe_names
    
    def test_recipe_interface(self):
        """Test that all recipes implement the required interface."""
        for recipe in AVAILABLE_RECIPES:
            # Test that recipes have required methods
            assert hasattr(recipe, 'applies')
            assert hasattr(recipe, 'plan')
            
            # Test that applies returns an integer
            spec = DeploymentSpec(
                app_path=".", runtime="unknown", framework=None,
                containerized=False, multi_service=False,
                start_command=None, port=None,
                health_path="/", needs_build=False, build_command=None,
                static_assets=None, db_required=False,
                env_required=[], env_example_path=None,
                localhost_refs=[], loopback_binds=[], warnings=[], rationale=[],
                manifests={}, extra={}
            )
            
            score = recipe.applies(spec)
            assert isinstance(score, int)
            assert 0 <= score <= 100
