"""
Next.js static export recipe for S3 + CloudFront deployment.
"""

from typing import Dict, List, Any
import os
import subprocess
import shutil
from pathlib import Path
from .base import Recipe, RecipePlan


class NextStaticRecipe(Recipe):
    """Recipe for Next.js static export to S3 + CloudFront."""
    
    def applies(self, spec) -> int:
        """Score how well this recipe fits the Next.js static spec."""
        score = 0
        
        # Check runtime
        if spec.runtime == "node":
            score += 30
        elif spec.runtime == "unknown":
            score += 10
        
        # Check framework
        if spec.framework == "nextjs":
            score += 50
        elif spec.framework is None:
            # Check for Next.js in manifests
            if "next" in spec.manifests.get("package.json", "").lower():
                score += 40
        
        # Check for Next.js specific files
        if "next.config.js" in spec.manifests or "next.config.ts" in spec.manifests:
            score += 20
        
        # Check for Next.js imports in code
        if any("from 'next'" in content or "import next" in content 
               for content in spec.manifests.values()):
            score += 20
        
        # Prefer static export capability
        if any("export" in content.lower() for content in spec.manifests.values()):
            score += 10
        
        return min(score, 100)
    
    def plan(self, spec, infra_plan, patch_result, env_inject, repo_url: str = None) -> RecipePlan:
        """Create deployment plan for Next.js static export."""
        # Build and export the Next.js app locally
        static_dir = self._build_nextjs_static(spec.app_path)
        
        # Terraform variables for static site
        tf_vars = {
            "app_name": "nextjs-static",
            "region": "us-west-2",  # Default region, will be overridden by orchestrator
            "static_dir": static_dir,
            "index_document": "index.html",
            "error_document": "404.html"
        }
        
        # Smoke checks
        smoke_checks = [
            {"path": "/", "expect": 200, "contains": "Next.js"},
            {"path": "/_next/static/", "expect": 200}  # Next.js static assets
        ]
        
        return RecipePlan(
            name="next_static",
            target="s3_cf",
            vars=tf_vars,
            user_data=None,
            container_cmd=None,
            container_entrypoint=None,
            static_dir=static_dir,
            preflight_notes=[
                "Next.js app will be built and exported to static files",
                "Static files will be uploaded to S3 and served via CloudFront",
                "Build process runs locally in orchestrator workspace",
                "No server-side rendering - pure static export"
            ],
            rationale=[
                "Detected Next.js framework with static export capability",
                "Static export is ideal for S3 + CloudFront deployment",
                "Local build ensures consistent deployment artifacts"
            ],
            smoke_checks=smoke_checks
        )
    
    def _build_nextjs_static(self, app_path: str) -> str:
        """Build Next.js app and export to static files."""
        app_dir = Path(app_path)
        build_dir = app_dir / "build_output"
        
        try:
            # Ensure we're in the app directory
            original_cwd = os.getcwd()
            os.chdir(app_dir)
            
            # Install dependencies
            if (app_dir / "package-lock.json").exists():
                subprocess.run(["npm", "ci"], check=True)
            else:
                subprocess.run(["npm", "install"], check=True)
            
            # Build the app
            subprocess.run(["npm", "run", "build"], check=True)
            
            # Export to static
            subprocess.run(["npm", "run", "export"], check=True)
            
            # Move export to build directory
            export_dir = app_dir / "out"
            if export_dir.exists():
                if build_dir.exists():
                    shutil.rmtree(build_dir)
                shutil.move(str(export_dir), str(build_dir))
            else:
                # Fallback: copy dist or build directory
                for fallback_dir in ["dist", "build"]:
                    if (app_dir / fallback_dir).exists():
                        if build_dir.exists():
                            shutil.rmtree(build_dir)
                        shutil.copytree(str(app_dir / fallback_dir), str(build_dir))
                        break
                else:
                    raise RuntimeError("No export output found (expected 'out', 'dist', or 'build' directory)")
            
            return str(build_dir)
            
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Next.js build failed: {e}")
        except Exception as e:
            raise RuntimeError(f"Failed to build Next.js static export: {e}")
        finally:
            os.chdir(original_cwd)
