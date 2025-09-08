# Arvo Orchestrator

A minimal CLI and REST API orchestrator that wraps your existing Terraform deployment flow with real-time event streaming and uniform JSON results.

## Installation

```bash
# Install in development mode
pip install -e .

# Or install dependencies directly
pip install click fastapi uvicorn requests pydantic
```

## CLI Usage

### Deploy an Application

```bash
# Deploy with real-time event streaming
e the lofs arvo deploy \
  --instructions "Deploy this Flask app on AWS" \
  --repo https://github.com/Arvo-AI/hello_world \
  --region us-west-2

# Output: Streams NDJSON events, ends with uniform result
# {"deployment_id": "d-20241201-143022-a1b2", "status": "healthy", "public_url": "http://1.2.3.4:8080", ...}
```

### Check Status

```bash
arvo status d-20241201-143022-a1b2
# {"deployment_id": "d-20241201-143022-a1b2", "status": "healthy", "public_url": "http://1.2.3.4:8080"}
```

### View Logs

```bash
# Show all logs
arvo logs d-20241201-143022-a1b2

# Follow logs in real-time
arvo logs d-20241201-143022-a1b2 --follow
```

### Get Outputs

```bash
arvo outputs d-20241201-143022-a1b2
# {"application_url": {"value": "http://1.2.3.4:8080"}, "public_ip": {"value": "1.2.3.4"}, ...}
```

### Destroy Deployment

```bash
arvo destroy d-20241201-143022-a1b2
# {"deployment_id": "d-20241201-143022-a1b2", "status": "destroyed"}
```

### List Deployments

```bash
arvo list
# [{"deployment_id": "d-20241201-143022-a1b2", "status": "healthy", ...}]
```

## REST API Usage

### Start the API Server

```bash
arvo serve --host 0.0.0.0 --port 7000
```

### API Endpoints

#### Start Deployment

```bash
curl -X POST http://localhost:7000/deployments \
  -H "Content-Type: application/json" \
  -d '{
    "instructions": "Deploy this Flask app on AWS",
    "repo": "https://github.com/Arvo-AI/hello_world",
    "region": "us-west-2"
  }'

# Response: {"deployment_id": "d-20241201-143022-a1b2"}
```

#### Get Status

```bash
curl http://localhost:7000/deployments/d-20241201-143022-a1b2
# {"deployment_id": "d-20241201-143022-a1b2", "status": "healthy", "public_url": "http://1.2.3.4:8080"}
```

#### Stream Events (Server-Sent Events)

```bash
curl -N http://localhost:7000/deployments/d-20241201-143022-a1b2/events
# data: {"ts": "2024-12-01T14:30:22", "type": "INIT", "data": {...}}
# data: {"ts": "2024-12-01T14:30:23", "type": "TF_INIT", "data": {...}}
# ...
```

#### Get Outputs

```bash
curl http://localhost:7000/deployments/d-20241201-143022-a1b2/outputs
# {"deployment_id": "d-20241201-143022-a1b2", "outputs": {...}}
```

#### Destroy Deployment

```bash
curl -X POST http://localhost:7000/deployments/d-20241201-143022-a1b2/destroy
# {"deployment_id": "d-20241201-143022-a1b2", "status": "destroying"}
```

#### List All Deployments

```bash
curl http://localhost:7000/deployments
# {"deployments": [{"deployment_id": "d-20241201-143022-a1b2", "status": "healthy", ...}]}
```

## Event Types

The orchestrator emits NDJSON events with these types:

- `INIT` - Deployment started
- `TF_INIT` - Terraform init completed
- `TF_PLAN` - Terraform plan completed (with resource counts)
- `TF_APPLY_START` - Terraform apply started
- `TF_APPLY_LINE` - Terraform apply output line
- `TF_APPLY_DONE` - Terraform apply completed
- `BOOTSTRAP_WAIT` - Waiting for application to bootstrap
- `VERIFY_OK` - Application verification successful
- `DONE` - Deployment completed successfully
- `ERROR` - Error occurred
- `DESTROY_START` - Destroy started
- `DESTROY_DONE` - Destroy completed

## Status State Machine

```
queued → init → tf_init → tf_plan → tf_apply → bootstrapping → verifying → healthy | failed
```

## Directory Structure

Each deployment creates a directory under `.arvo/<deployment_id>/`:

```
.arvo/
└── d-20241201-143022-a1b2/
    ├── env.json          # Input parameters
    ├── logs.ndjson       # Event stream
    ├── terraform.log     # Raw terraform output
    ├── outputs.json      # Terraform outputs
    ├── main.tf           # Terraform files
    ├── variables.tf
    ├── outputs.tf
    ├── bootstrap.sh
    └── terraform.tfstate # Terraform state
```

## Environment Variables

- `ARVO_HOME` - Override base directory (default: `.arvo`)

## Prerequisites

- Python 3.10+
- Terraform installed and in PATH
- AWS CLI configured with appropriate credentials
- Existing Terraform files (main.tf, variables.tf, outputs.tf, bootstrap.sh)

## Error Handling

The orchestrator provides helpful error messages:

- AWS credentials issues: "Run 'aws configure' for creds"
- Security group issues: "Check SG ingress 8080/tcp"
- Service startup issues: "Service not up; check bootstrap or security group"

## Acceptance Criteria ✅

All requirements are implemented:

- ✅ Single entrypoint with real-time event streaming
- ✅ Uniform JSON results
- ✅ Minimal REST service with SSE
- ✅ No infrastructure changes to existing Terraform
- ✅ NDJSON event logging
- ✅ Status state machine
- ✅ Terraform wrapper functions
- ✅ Verification step with polling
- ✅ CLI commands (deploy, status, logs, outputs, destroy)
- ✅ REST API endpoints
- ✅ Helpful error messages and hints
