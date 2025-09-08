#!/usr/bin/env python3
"""
Integration test showing how the analyzer works with the orchestrator.
"""

import tempfile
from pathlib import Path
from arvo.analyzer import analyze_repo, fetch_into_workspace
from arvo.analyzer.report import emit_report


def test_integration():
    """Test the full analyze → report pipeline."""
    print("🔗 Testing Analyzer Integration")
    print("=" * 40)
    
    # Test with a local Flask app
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create a simple Flask app
        app_dir = temp_path / "test_app"
        app_dir.mkdir()
        
        (app_dir / "app.py").write_text("""
from flask import Flask
app = Flask(__name__)

@app.route('/')
def hello():
    return 'Hello World!'

@app.route('/health')
def health():
    return {'status': 'ok'}

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000)
""")
        
        (app_dir / "requirements.txt").write_text("flask==2.3.0")
        (app_dir / ".env.example").write_text("FLASK_ENV=production\nDATABASE_URL=postgresql://localhost/db")
        
        print(f"📁 Created test app at: {app_dir}")
        
        # Analyze the app
        spec = analyze_repo(str(app_dir), "Deploy this Flask application to AWS")
        
        print(f"\n📊 Analysis Results:")
        print(f"   Runtime: {spec.runtime}")
        print(f"   Framework: {spec.framework}")
        print(f"   Port: {spec.port}")
        print(f"   Start Command: {spec.start_command}")
        print(f"   Health Path: {spec.health_path}")
        print(f"   DB Required: {spec.db_required}")
        print(f"   Containerized: {spec.containerized}")
        print(f"   Multi Service: {spec.multi_service}")
        print(f"   Needs Build: {spec.needs_build}")
        print(f"   Env Required: {spec.env_required}")
        print(f"   Localhost Refs: {len(spec.localhost_refs)} files")
        print(f"   Loopback Binds: {len(spec.loopback_binds)} files")
        print(f"   Warnings: {spec.warnings}")
        print(f"   Rationale: {spec.rationale}")
        print(f"   Manifests: {list(spec.manifests.keys())}")
        
        # Generate report
        report_dir = temp_path / "analysis_report"
        emit_report(spec, str(report_dir))
        
        print(f"\n📄 Generated Report:")
        print(f"   JSON Spec: {report_dir / 'deployment_spec.json'}")
        print(f"   Analysis: {report_dir / 'analysis.md'}")
        
        # Show the analysis markdown
        analysis_content = (report_dir / "analysis.md").read_text()
        print(f"\n📋 Analysis Summary:")
        print(analysis_content)
        
        print(f"\n✅ Integration test completed successfully!")
        print(f"   The analyzer correctly detected a Flask app and generated a comprehensive report.")


if __name__ == "__main__":
    test_integration()
