from arvo.analyzer import analyze_repo
from pathlib import Path
import tempfile

def test_analyzer_flask_detects_python_flask():
    with tempfile.TemporaryDirectory() as td:
        p = Path(td)
        (p/"app.py").write_text("from flask import Flask\napp=Flask(__name__)\n")
        (p/"requirements.txt").write_text("flask==2.3.0\n")
        spec = analyze_repo(str(p))
        assert spec.runtime == "python"
        assert spec.framework == "flask"
        assert spec.port in (5000, None)


def test_analyzer_next_detects_node_nextjs():
    with tempfile.TemporaryDirectory() as td:
        p = Path(td)
        (p/"package.json").write_text('{"name":"x","scripts":{"build":"next build","start":"next start"},"dependencies":{"next":"13.0.0","react":"18.0.0"}}')
        spec = analyze_repo(str(p))
        assert spec.runtime == "node"
        assert spec.framework == "nextjs"
        assert spec.needs_build is True
