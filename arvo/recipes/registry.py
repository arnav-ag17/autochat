"""
Recipe registry for selecting the best recipe based on DeploymentSpec and InfraPlan.
"""

from typing import List, Optional
import logging

from .base import Recipe
from .python_flask import FlaskRecipe
from .python_fastapi import FastAPIRecipe
from .python_django import DjangoRecipe
from .node_express import NodeExpressRecipe
from .next_static import NextStaticRecipe
from .dockerized import DockerizedRecipe

logger = logging.getLogger(__name__)


# Registry of all available recipes
AVAILABLE_RECIPES: List[Recipe] = [
    FlaskRecipe(),
    FastAPIRecipe(),
    DjangoRecipe(),
    NodeExpressRecipe(),
    NextStaticRecipe(),
    DockerizedRecipe()
]


def select_recipe(spec, infra_plan) -> Optional[Recipe]:
    """
    Select the best recipe based on DeploymentSpec and InfraPlan.
    
    Args:
        spec: DeploymentSpec from analyzer
        infra_plan: InfraPlan from selector
        
    Returns:
        Best matching Recipe, or None if no suitable recipe found
    """
    logger.info(f"Selecting recipe for {spec.runtime}/{spec.framework} app")
    
    # Score all recipes
    recipe_scores = []
    for recipe in AVAILABLE_RECIPES:
        score = recipe.applies(spec)
        recipe_scores.append((recipe, score))
        logger.debug(f"Recipe {recipe.__class__.__name__}: score {score}")
    
    # Sort by score (highest first)
    recipe_scores.sort(key=lambda x: x[1], reverse=True)
    
    # Get the best recipe
    if recipe_scores and recipe_scores[0][1] > 0:
        best_recipe, best_score = recipe_scores[0]
        logger.info(f"Selected recipe: {best_recipe.__class__.__name__} (score: {best_score})")
        return best_recipe
    
    logger.warning("No suitable recipe found for deployment spec")
    return None


def list_available_recipes() -> List[str]:
    """List all available recipe names."""
    return [recipe.__class__.__name__ for recipe in AVAILABLE_RECIPES]


def get_recipe_by_name(name: str) -> Optional[Recipe]:
    """Get a specific recipe by name."""
    for recipe in AVAILABLE_RECIPES:
        if recipe.__class__.__name__.lower().replace("recipe", "") == name.lower():
            return recipe
    return None
