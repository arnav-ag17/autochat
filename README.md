# Arvo - AI-Powered Application Deployment System

## 🚀 Overview

Arvo is an intelligent deployment system that automates the process of deploying applications based on natural language input and code repositories. The system uses **Claude 4.1 Opus Max via OpenRouter API** to analyze repositories, extract deployment requirements using advanced NLP, and dynamically provisions cloud infrastructure to deploy applications with minimal user intervention.

## ✨ Features

- **Advanced NLP with Claude 4.1 Opus Max**: Understands complex deployment requirements from natural language
- **OpenRouter API Integration**: Leverages state-of-the-art LLM capabilities via OpenRouter
- **Intelligent Repository Analysis**: Automatically detects application types (Flask, Django, Node.js, etc.)
- **Infrastructure Provisioning**: Uses Terraform to provision AWS resources
- **Multi-Framework Support**: Supports Python (Flask, Django, FastAPI), Node.js, and more
- **Web Interface**: User-friendly web UI for deployment management
- **CLI Tools**: Command-line interface for developers
- **Real-time Logging**: Comprehensive deployment logs and status tracking
- **Auto-Configuration**: Automatically fixes common deployment issues (localhost references, port binding, etc.)
- **Type-Safe Extraction**: Prevents common LLM integration errors with robust validation
- **Automatic Fallback**: Falls back to regex system if LLM fails

## 🎯 Project Requirements Compliance

This project fulfills all requirements from the Autodeployment Chat System challenge:

✅ **Natural Language Input**: Accepts plain English deployment instructions  
✅ **Repository Analysis**: Analyzes GitHub repositories and zip files  
✅ **Infrastructure Determination**: Automatically selects appropriate deployment type (VM, Serverless, Kubernetes)  
✅ **Terraform Provisioning**: Uses Terraform for infrastructure as code  
✅ **Minimal Intervention**: Fully automated deployment process  
✅ **Logging**: Comprehensive deployment logs and status tracking  
✅ **Generalizable**: Supports multiple application types and frameworks  
✅ **Command-line Tool**: CLI interface for deployment automation  
✅ **Backend API**: RESTful API for chatbot integration  

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Web Interface │    │   CLI Tools      │    │   API Server    │
│   (Flask)       │    │   (Python)       │    │   (FastAPI)     │
└─────────┬───────┘    └─────────┬────────┘    └─────────┬───────┘
          │                      │                       │
          └──────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────▼──────────────┐
                    │     Deployment Engine      │
                    │  (simple_deploy.py)        │
                    └─────────────┬──────────────┘
                                  │
                    ┌─────────────▼──────────────┐
                    │   Repository Analyzer      │
                    │  (simple_analyzer.py)      │
                    └─────────────┬──────────────┘
                                  │
                    ┌─────────────▼──────────────┐
                    │   OpenRouter NLP Engine    │
                    │  (openrouter_nlp.py)       │
                    │  Claude 4.1 Opus Max       │
                    └─────────────┬──────────────┘
                                  │
                    ┌─────────────▼──────────────┐
                    │    Terraform Engine        │
                    │   (terraform.py)           │
                    └─────────────┬──────────────┘
                                  │
                    ┌─────────────▼──────────────┐
                    │      AWS Resources         │
                    │   (EC2, EIP, Security      │
                    │    Groups, VPC, etc.)      │
                    └────────────────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- AWS CLI configured with credentials
- Terraform installed
- Git
- OpenRouter API key (for Claude 4.1 Opus Max access)

### Installation

1. **Clone the repository:**
```bash
git clone https://github.com/your-username/arvo.git
cd arvo
```

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

3. **Configure AWS credentials:**
```bash
aws configure
# Enter your AWS Access Key ID, Secret Access Key, and default region
```

4. **Configure OpenRouter API key:**
```bash
# The OpenRouter API key is already configured in the code
# For production use, set it as an environment variable:
export OPENROUTER_API_KEY="your_openrouter_api_key_here"
```

### Usage

#### Web Interface (Recommended for Demo)

1. **Start the web interface:**
```bash
python3 -m arvo.web_interface
```

2. **Open your browser:**
Navigate to `http://localhost:5001`

3. **Deploy an application:**
- Enter deployment instructions: "Deploy this Flask application on AWS"
- Enter repository URL: `https://github.com/Arvo-AI/hello_world`
- Click "Deploy Application"

#### Command Line Interface

```bash
# Quick deployment
python3 -m arvo.quick_deploy "Deploy this Flask application on AWS" https://github.com/Arvo-AI/hello_world

# Full CLI with options
python3 -m arvo.cli_tool deploy --instructions "Deploy this Django app on AWS" --repo https://github.com/example/django-app --region us-west-2
```

#### API Server

```bash
# Start the API server
python3 -m arvo.api_server

# Deploy via API
curl -X POST http://localhost:8081/deploy \
  -H "Content-Type: application/json" \
  -d '{
    "instructions": "Deploy this Flask application on AWS",
    "repo_url": "https://github.com/Arvo-AI/hello_world",
    "region": "us-west-2"
  }'
```

## 📁 Project Structure

```
arvo/
├── web_interface.py          # Flask web UI
├── api_server.py            # FastAPI backend
├── cli_tool.py              # Command-line interface
├── quick_deploy.py          # Quick deployment CLI
├── simple_deploy.py         # Core deployment engine
├── simple_analyzer.py       # Repository analysis
├── openrouter_nlp.py        # OpenRouter + Claude 4.1 Opus Max NLP
├── simple_nlp.py           # Regex-based NLP (fallback)
├── terraform.py            # Terraform management
├── recipes/                # Application-specific deployment recipes
│   ├── base.py
│   ├── flask.py
│   ├── django.py
│   ├── nodejs.py
│   └── ...
├── templates/              # Web interface templates
│   └── index.html
├── log_viewer.py           # Deployment log viewer
├── infrastructure_types.py # Infrastructure type definitions
└── switch_nlp_system.py    # System switcher utility
```

## 🎬 Demo Video

**Demo Repository:** https://github.com/Arvo-AI/hello_world

**Demo Instructions:** "Deploy this Flask application on AWS with a public IP address"

**Expected Results:**
- Deployment time: ~60-90 seconds
- Application accessible at: `http://[PUBLIC_IP]:5000`
- Response: "Hello, World! This is a simple Flask application."

## 🔧 Supported Application Types

### Python Applications
- **Flask**: Automatic detection, virtual environment setup, systemd service
- **Django**: Database configuration, static file serving, WSGI setup
- **FastAPI**: ASGI server configuration, automatic dependency installation

### Node.js Applications
- **Express**: Package.json detection, npm install, PM2 process management
- **Next.js**: Build process, static file serving, production optimization
- **React**: Build and serve static files

### Containerized Applications
- **Docker**: Dockerfile detection, container orchestration
- **Docker Compose**: Multi-container deployment

## 🌐 Infrastructure Types

### Virtual Machine (VM)
- **EC2 Instances**: Auto-scaling groups, load balancers
- **Networking**: VPC, subnets, security groups
- **Storage**: EBS volumes, S3 buckets
- **Monitoring**: CloudWatch logs and metrics

### Serverless (Future)
- **AWS Lambda**: Function deployment and configuration
- **API Gateway**: RESTful API endpoints
- **DynamoDB**: NoSQL database integration

### Kubernetes (Future)
- **EKS**: Managed Kubernetes clusters
- **Helm Charts**: Application packaging and deployment
- **Ingress**: Load balancing and SSL termination

## 📊 Deployment Process

1. **Input Processing**: Parse natural language instructions
2. **Repository Analysis**: Clone and analyze code structure
3. **Requirement Extraction**: Identify dependencies and configuration needs
4. **Infrastructure Planning**: Determine optimal deployment strategy
5. **Terraform Provisioning**: Create and configure AWS resources
6. **Application Deployment**: Install dependencies and start services
7. **Health Checks**: Verify application is running correctly
8. **URL Generation**: Provide accessible application URL

## 🤖 OpenRouter + Claude 4.1 Opus Max Integration

### **Advanced NLP Capabilities**

The system uses **Claude 4.1 Opus Max via OpenRouter API** for intelligent deployment requirement extraction:

- **Complex Instruction Understanding**: Handles ambiguous and complex deployment requirements
- **Context-Aware Extraction**: Understands relationships between different requirements
- **Intelligent Inference**: Makes smart assumptions about missing requirements
- **Type-Safe Output**: Prevents common LLM integration errors with robust validation

### **Example Complex Instructions**

```bash
# These complex instructions are handled intelligently by Claude 4.1 Opus Max:

"Deploy this Django application with a database, auto-scaling, and monitoring. 
Use a medium-sized instance and make it highly available"

"Deploy this Flask app that can handle lots of traffic, make it secure with HTTPS, 
and put it in the US West region"

"I want to run this Node.js app on AWS, but I'm not sure about the infrastructure. 
It needs to be cost-effective but reliable."
```

### **System Reliability**

- **Automatic Fallback**: Falls back to regex system if OpenRouter fails
- **Type Safety**: Dataclass validation prevents boolean errors
- **Error Isolation**: LLM errors don't crash the deployment system
- **Easy Switching**: Use `switch_nlp_system.py` to toggle between systems

## 🔍 Monitoring and Logging

- **Real-time Logs**: View deployment progress in web interface
- **Status Tracking**: Monitor deployment success/failure
- **Health Checks**: Automatic application health verification
- **Error Handling**: Comprehensive error reporting and recovery
- **OpenRouter Logs**: Track Claude 4.1 Opus Max extraction results

## 🛠️ Development

### Running Tests

```bash
# Run unit tests
python -m pytest tests/

# Run integration tests
python -m pytest tests/integration/
```

### Adding New Application Types

1. Create a new recipe in `arvo/recipes/`
2. Add detection logic in `arvo/simple_analyzer.py`
3. Update NLP patterns in `arvo/simple_nlp.py`
4. Test with sample applications

### Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 🚀 Potential Improvements

### **Short-term Enhancements**

1. **Multi-Cloud Support**
   - Add support for Google Cloud Platform (GCP) and Microsoft Azure
   - Implement cloud-agnostic infrastructure provisioning
   - Add cloud-specific optimization features

2. **Enhanced LLM Integration**
   - Support for multiple LLM providers (OpenAI GPT-4, Anthropic Claude, Google Gemini)
   - Implement LLM response caching for faster repeated deployments
   - Add confidence scoring for extracted requirements

3. **Advanced Infrastructure Types**
   - Kubernetes (EKS) deployment support
   - Serverless (Lambda) deployment capabilities
   - Container orchestration with Docker Swarm

4. **Improved User Experience**
   - Real-time deployment progress streaming
   - Interactive deployment configuration wizard
   - Deployment templates and presets

### **Medium-term Improvements**

1. **Intelligent Cost Optimization**
   - Automatic instance type selection based on application requirements
   - Cost estimation before deployment
   - Auto-scaling policies based on usage patterns

2. **Advanced Monitoring & Observability**
   - Integration with CloudWatch, Datadog, New Relic
   - Custom metrics and alerting
   - Performance optimization recommendations

3. **Security Enhancements**
   - Automatic SSL certificate management
   - Security group optimization
   - Vulnerability scanning integration

4. **CI/CD Integration**
   - GitHub Actions integration
   - GitLab CI/CD support
   - Automated testing and deployment pipelines

### **Long-term Vision**

1. **AI-Powered Infrastructure Management**
   - Predictive scaling based on historical data
   - Automatic performance optimization
   - Self-healing infrastructure

2. **Multi-Environment Management**
   - Staging and production environment management
   - Blue-green deployment support
   - Canary deployment capabilities

3. **Enterprise Features**
   - Multi-tenant support
   - Role-based access control
   - Audit logging and compliance

4. **Advanced Application Support**
   - Microservices architecture deployment
   - Service mesh integration
   - Database migration automation

### **Technical Debt & Optimization**

1. **Performance Improvements**
   - Parallel deployment processing
   - Terraform state management optimization
   - Caching layer implementation

2. **Code Quality**
   - Comprehensive test coverage
   - API documentation with OpenAPI/Swagger
   - Code quality metrics and monitoring

3. **Scalability**
   - Horizontal scaling support
   - Load balancing for web interface
   - Database optimization for deployment history

## 📞 Support

For support, please open an issue in the GitHub repository or contact the development team.

---

**GitHub Repository:** https://github.com/arnav-ag17/autochat

**Demo Video:** [Link to your Loom video]

**Dependencies:** See [DEPENDENCIES.md](DEPENDENCIES.md) for a complete list of all sources and dependencies used.