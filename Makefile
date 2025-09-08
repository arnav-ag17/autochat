# Arvo Makefile
# Quick commands for development and deployment

.PHONY: help dev build-ui docker-api docker-all run-all clean test install

# Default target
help:
	@echo "Arvo - Automated Application Deployment System"
	@echo ""
	@echo "Available commands:"
	@echo "  make dev          - Run API locally with hot reload and serve UI"
	@echo "  make build-ui     - Build UI for production"
	@echo "  make docker-api   - Build API Docker image"
	@echo "  make docker-all   - Build all-in-one Docker image"
	@echo "  make run-all      - Run all-in-one container on http://localhost:8080"
	@echo "  make test         - Run all tests"
	@echo "  make install      - Install Arvo in development mode"
	@echo "  make clean        - Clean up build artifacts"
	@echo ""
	@echo "Quick start:"
	@echo "  make run-all      # Run everything in Docker"
	@echo "  make dev          # Run locally for development"

# Development mode - run API and UI separately
dev:
	@echo "🚀 Starting Arvo in development mode..."
	@echo "API will be available at: http://localhost:8080"
	@echo "UI will be available at: http://localhost:3000"
	@echo ""
	@echo "Press Ctrl+C to stop both servers"
	@echo ""
	@echo "Starting API server..."
	@API_BASE_URL=http://localhost:8080 python -m uvicorn arvo.api.app:app --host 0.0.0.0 --port 8080 --reload &
	@echo "Starting UI server..."
	@cd arvo/web && python -m http.server 3000 &
	@echo "Both servers started. Press Ctrl+C to stop."
	@wait

# Build UI for production (currently just copies files)
build-ui:
	@echo "📦 Building UI for production..."
	@mkdir -p arvo/web/dist
	@cp arvo/web/index.html arvo/web/dist/
	@echo "✅ UI built to arvo/web/dist/"

# Build API Docker image
docker-api:
	@echo "🐳 Building API Docker image..."
	docker build -f arvo/packaging/docker/api.Dockerfile -t arvo-api:latest .
	@echo "✅ API Docker image built: arvo-api:latest"

# Build all-in-one Docker image
docker-all:
	@echo "🐳 Building all-in-one Docker image..."
	docker build -f arvo/packaging/docker/all-in-one.Dockerfile -t arvo:latest .
	@echo "✅ All-in-one Docker image built: arvo:latest"

# Run all-in-one container
run-all:
	@echo "🚀 Starting Arvo all-in-one container..."
	@echo "Available at: http://localhost:8080"
	@echo "Press Ctrl+C to stop"
	@echo ""
	docker run --rm -p 8080:80 \
		-v ~/.aws:/root/.aws:ro \
		-e AWS_PROFILE \
		-e AWS_ACCESS_KEY_ID \
		-e AWS_SECRET_ACCESS_KEY \
		-e AWS_SESSION_TOKEN \
		-e AWS_DEFAULT_REGION \
		arvo:latest

# Run API container only
run-api:
	@echo "🚀 Starting Arvo API container..."
	@echo "Available at: http://localhost:8080"
	@echo "Press Ctrl+C to stop"
	@echo ""
	docker run --rm -p 8080:8080 \
		-v ~/.aws:/root/.aws:ro \
		-e AWS_PROFILE \
		-e AWS_ACCESS_KEY_ID \
		-e AWS_SECRET_ACCESS_KEY \
		-e AWS_SESSION_TOKEN \
		-e AWS_DEFAULT_REGION \
		arvo-api:latest

# Install Arvo in development mode
install:
	@echo "📦 Installing Arvo in development mode..."
	pip install -e .
	@echo "✅ Arvo installed successfully"

# Run tests
test:
	@echo "🧪 Running tests..."
	python -m pytest -v
	@echo "✅ All tests passed"

# Run specific test categories
test-nlp:
	@echo "🧪 Running NLP tests..."
	python -m pytest tests/test_nlp_basic.py -v

test-recipes:
	@echo "🧪 Running recipe tests..."
	python -m pytest tests/test_recipes_basic.py -v

test-obs:
	@echo "🧪 Running observability tests..."
	python -m pytest tests/test_obs_basic.py -v

# Clean up build artifacts
clean:
	@echo "🧹 Cleaning up build artifacts..."
	rm -rf arvo/web/dist/
	rm -rf .pytest_cache/
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "✅ Cleanup complete"

# Development helpers
lint:
	@echo "🔍 Running linter..."
	@echo "Note: Install flake8 or black for linting"
	@echo "pip install flake8 black"

format:
	@echo "🎨 Formatting code..."
	@echo "Note: Install black for formatting"
	@echo "pip install black && black arvo/ tests/"

# Docker helpers
docker-clean:
	@echo "🧹 Cleaning Docker images..."
	docker rmi arvo:latest arvo-api:latest 2>/dev/null || true
	@echo "✅ Docker cleanup complete"

# Show logs from running container
logs:
	@echo "📋 Showing logs from running Arvo container..."
	docker logs -f $$(docker ps -q --filter ancestor=arvo:latest) 2>/dev/null || \
	docker logs -f $$(docker ps -q --filter ancestor=arvo-api:latest) 2>/dev/null || \
	echo "No running Arvo container found"

# Quick deployment test
test-deploy:
	@echo "🧪 Testing deployment with hello world app..."
	@echo "This will deploy the hello world app and destroy it after 1 hour"
	arvo deploy --instructions "Deploy hello world Flask app" --repo "https://github.com/Arvo-AI/hello_world" --ttl-hours 1

# Show help for CLI
cli-help:
	@echo "📖 Arvo CLI Help:"
	@echo ""
	@echo "Deploy an application:"
	@echo "  arvo deploy --instructions 'Deploy Flask app' --repo 'https://github.com/user/repo'"
	@echo ""
	@echo "Check deployment status:"
	@echo "  arvo status <deployment-id>"
	@echo ""
	@echo "View deployment logs:"
	@echo "  arvo logs <deployment-id> --follow"
	@echo ""
	@echo "Destroy deployment:"
	@echo "  arvo destroy <deployment-id>"
	@echo ""
	@echo "For more help:"
	@echo "  arvo --help"
