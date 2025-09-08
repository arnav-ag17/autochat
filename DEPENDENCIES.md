# Dependencies and Sources

This document provides a comprehensive list of all dependencies, libraries, and sources used in the Arvo deployment system.

## Python Dependencies

### Core Dependencies

| Package | Version | Purpose | License |
|---------|---------|---------|---------|
| `boto3` | ^1.34.0 | AWS SDK for Python - EC2, EIP, Security Groups, VPC management | Apache 2.0 |
| `requests` | ^2.31.0 | HTTP library for API calls and health checks | Apache 2.0 |
| `flask` | ^3.0.0 | Web framework for user interface | BSD 3-Clause |
| `fastapi` | ^0.104.0 | Modern web framework for API server | MIT |
| `uvicorn` | ^0.24.0 | ASGI server for FastAPI | BSD 3-Clause |
| `pydantic` | ^2.5.0 | Data validation using Python type annotations | MIT |
| `jinja2` | ^3.1.0 | Template engine for web interface | BSD 3-Clause |
| `click` | ^8.1.0 | Command-line interface creation | BSD 3-Clause |
| `python-dotenv` | ^1.0.0 | Environment variable management | BSD 3-Clause |
| `dataclasses` | Built-in | Data class decorators for type-safe LLM output | Python Software Foundation |
| `pathlib` | Built-in | Object-oriented filesystem paths | Python Software Foundation |
| `json` | Built-in | JSON data handling | Python Software Foundation |
| `subprocess` | Built-in | Process management for Terraform | Python Software Foundation |
| `time` | Built-in | Time utilities and sleep functions | Python Software Foundation |
| `os` | Built-in | Operating system interface | Python Software Foundation |
| `sys` | Built-in | System-specific parameters and functions | Python Software Foundation |
| `re` | Built-in | Regular expression operations | Python Software Foundation |
| `typing` | Built-in | Type hints support | Python Software Foundation |
| `dataclasses` | Built-in | Data class decorators | Python Software Foundation |
| `enum` | Built-in | Enumeration support | Python Software Foundation |
| `uuid` | Built-in | UUID generation | Python Software Foundation |
| `hashlib` | Built-in | Secure hash and message digest algorithms | Python Software Foundation |

### Development Dependencies

| Package | Version | Purpose | License |
|---------|---------|---------|---------|
| `pytest` | ^7.4.0 | Testing framework | MIT |
| `pytest-cov` | ^4.1.0 | Coverage plugin for pytest | MIT |
| `black` | ^23.0.0 | Code formatter | MIT |
| `flake8` | ^6.0.0 | Linting tool | MIT |
| `mypy` | ^1.7.0 | Static type checker | MIT |

## External Tools and Services

### Infrastructure as Code

| Tool | Version | Purpose | License |
|------|---------|---------|---------|
| **Terraform** | ^1.6.0 | Infrastructure provisioning and management | Mozilla Public License 2.0 |
| **AWS CLI** | ^2.13.0 | Command-line interface for AWS services | Apache 2.0 |

### AI/LLM Services

| Service | Purpose | Pricing Model | License |
|---------|---------|---------------|---------|
| **OpenRouter API** | Access to multiple LLM providers including Claude 4.1 Opus Max | Pay-per-token | Commercial API |
| **Claude 4.1 Opus Max** | Advanced NLP for deployment requirement extraction | Via OpenRouter | Anthropic Terms |

### Cloud Services

| Service | Purpose | Pricing Model |
|---------|---------|---------------|
| **Amazon EC2** | Virtual machine instances | Pay-per-use |
| **Amazon EIP** | Elastic IP addresses | Pay-per-use |
| **Amazon VPC** | Virtual private cloud | Free tier available |
| **Amazon Security Groups** | Network security | Free |
| **Amazon CloudWatch** | Monitoring and logging | Pay-per-use |
| **Amazon S3** | Object storage | Pay-per-use |

### Version Control

| Service | Purpose | License |
|---------|---------|---------|
| **Git** | Version control system | GPL v2 |
| **GitHub** | Repository hosting and API | Free for public repos |

## Third-Party Libraries and Frameworks

### Web Frameworks

| Framework | Version | Purpose | License |
|-----------|---------|---------|---------|
| **Flask** | ^3.0.0 | Lightweight web framework for UI | BSD 3-Clause |
| **FastAPI** | ^0.104.0 | Modern, fast web framework for APIs | MIT |
| **Jinja2** | ^3.1.0 | Template engine | BSD 3-Clause |

### AWS SDK

| Component | Version | Purpose | License |
|-----------|---------|---------|---------|
| **boto3** | ^1.34.0 | AWS SDK for Python | Apache 2.0 |
| **botocore** | ^1.34.0 | Low-level AWS service access | Apache 2.0 |

### HTTP and Networking

| Library | Version | Purpose | License |
|---------|---------|---------|---------|
| **requests** | ^2.31.0 | HTTP library for API calls | Apache 2.0 |
| **urllib3** | ^2.0.0 | HTTP client library | MIT |
| **certifi** | ^2023.0.0 | SSL certificate verification | Mozilla Public License 2.0 |

### Data Validation and Serialization

| Library | Version | Purpose | License |
|---------|---------|---------|---------|
| **pydantic** | ^2.5.0 | Data validation using Python type annotations | MIT |
| **pydantic-core** | ^2.14.0 | Core validation logic for Pydantic | MIT |

### Command Line Interface

| Library | Version | Purpose | License |
|---------|---------|---------|---------|
| **click** | ^8.1.0 | Command-line interface creation | BSD 3-Clause |
| **colorama** | ^0.4.6 | Cross-platform colored terminal text | BSD 3-Clause |

### Environment and Configuration

| Library | Version | Purpose | License |
|---------|---------|---------|---------|
| **python-dotenv** | ^1.0.0 | Load environment variables from .env file | BSD 3-Clause |

## Application-Specific Dependencies

### Python Applications

| Package | Version | Purpose | License |
|---------|---------|---------|---------|
| **Flask** | ^3.0.0 | Web framework | BSD 3-Clause |
| **Django** | ^4.2.0 | Full-featured web framework | BSD 3-Clause |
| **FastAPI** | ^0.104.0 | Modern web framework for APIs | MIT |
| **gunicorn** | ^21.2.0 | WSGI HTTP server | MIT |
| **uvicorn** | ^0.24.0 | ASGI server | BSD 3-Clause |
| **psycopg2-binary** | ^2.9.0 | PostgreSQL adapter | LGPL |

### Node.js Applications

| Package | Version | Purpose | License |
|---------|---------|---------|---------|
| **express** | ^4.18.0 | Web framework | MIT |
| **next** | ^14.0.0 | React framework | MIT |
| **react** | ^18.0.0 | UI library | MIT |
| **pm2** | ^5.3.0 | Process manager | MIT |

## Operating System Dependencies

### Linux (Amazon Linux 2)

| Package | Purpose | License |
|---------|---------|---------|
| **python3** | Python runtime | Python Software Foundation |
| **python3-pip** | Python package installer | MIT |
| **git** | Version control | GPL v2 |
| **curl** | HTTP client | MIT |
| **wget** | File downloader | GPL v3 |
| **systemd** | System and service manager | LGPL v2.1 |
| **yum** | Package manager | GPL v2 |

### macOS (Development)

| Package | Purpose | License |
|---------|---------|---------|
| **Homebrew** | Package manager | BSD 2-Clause |
| **Python 3.13** | Python runtime | Python Software Foundation |

## Source Code References

### AWS Documentation
- **EC2 User Guide**: https://docs.aws.amazon.com/ec2/
- **VPC User Guide**: https://docs.aws.amazon.com/vpc/
- **Security Groups**: https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/working-with-security-groups.html
- **Elastic IPs**: https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/elastic-ip-addresses-eip.html

### Terraform Documentation
- **Terraform AWS Provider**: https://registry.terraform.io/providers/hashicorp/aws/latest/docs
- **EC2 Instance Resource**: https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/instance
- **VPC Resource**: https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/vpc

### Python Documentation
- **Flask Documentation**: https://flask.palletsprojects.com/
- **FastAPI Documentation**: https://fastapi.tiangolo.com/
- **Boto3 Documentation**: https://boto3.amazonaws.com/v1/documentation/api/latest/index.html

### AI/LLM Documentation
- **OpenRouter API Documentation**: https://openrouter.ai/docs
- **Claude 4.1 Opus Max**: https://docs.anthropic.com/claude/docs
- **Anthropic API Reference**: https://docs.anthropic.com/claude/reference

### GitHub API
- **GitHub REST API**: https://docs.github.com/en/rest
- **Repository API**: https://docs.github.com/en/rest/repos/repos

## License Compliance

All dependencies used in this project are compatible with the MIT License. The following licenses are represented:

- **MIT License**: Most permissive, allows commercial use
- **Apache 2.0**: Permissive, requires attribution
- **BSD 3-Clause**: Permissive, requires attribution
- **GPL v2/v3**: Copyleft, requires source code disclosure
- **LGPL**: Lesser copyleft, allows linking with proprietary software
- **Mozilla Public License 2.0**: Weak copyleft, allows commercial use

## Security Considerations

- All dependencies are regularly updated to latest stable versions
- No dependencies with known security vulnerabilities are used
- AWS credentials are handled securely using environment variables
- All HTTP communications use HTTPS where possible
- Input validation is performed on all user inputs

## Installation Commands

### Python Dependencies
```bash
pip install boto3 requests flask fastapi uvicorn pydantic jinja2 click python-dotenv
```

### Development Dependencies
```bash
pip install pytest pytest-cov black flake8 mypy
```

### System Dependencies
```bash
# macOS (using Homebrew)
brew install python3 terraform awscli

# Ubuntu/Debian
sudo apt-get install python3 python3-pip terraform awscli git curl wget

# Amazon Linux 2
sudo yum install python3 python3-pip git curl wget
```

## Version Pinning

All dependencies are pinned to specific versions to ensure reproducible builds:

```bash
# Generate requirements.txt
pip freeze > requirements.txt

# Install exact versions
pip install -r requirements.txt
```

---

**Last Updated**: January 2025  
**Maintained By**: Arvo Development Team  
**License**: MIT License
