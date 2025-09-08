#!/usr/bin/env bash
set -euo pipefail

echo "🚀 Starting Arvo Baseline Deployment"
echo "=================================="
echo "📦 Repository: https://github.com/Arvo-AI/hello_world"
echo "🎯 Features: Frontend + Backend REST API"
echo

command -v terraform >/dev/null || { echo "❌ Terraform not installed"; exit 1; }
aws sts get-caller-identity >/dev/null || { echo "❌ AWS CLI not configured. Run 'aws configure'."; exit 1; }

# Create key if it doesn't exist (idempotent attempt)
if ! aws ec2 describe-key-pairs --key-names "arvo-key" --output text >/dev/null 2>&1; then
  echo "🔑 Creating EC2 key pair arvo-key..."
  aws ec2 create-key-pair --key-name arvo-key \
    --query 'KeyMaterial' --output text > arvo-key.pem
  chmod 400 arvo-key.pem
fi

[ -d .terraform ] || terraform init -upgrade

echo "📋 Planning deployment..."
terraform plan

read -p "🤔 Do you want to proceed with the deployment? (y/N): " -r ANSW
[[ "$ANSW" =~ ^[Yy]$ ]] || { echo "❌ Deployment cancelled"; exit 0; }

echo "🏗️  Applying..."
terraform apply -auto-approve -compact-warnings

APP_URL=$(terraform output -raw application_url)
PUBLIC_IP=$(terraform output -raw public_ip)

echo
echo "🎉 Deployment completed successfully!"
echo "🌐 Application URL: $APP_URL"
echo "📍 Public IP: $PUBLIC_IP"
echo "⏳ Waiting ~30s for service warm-up..."
sleep 30

echo "🧪 Probing root endpoint..."
if curl -fsS --max-time 5 "$APP_URL" >/dev/null; then
  echo "✅ App is reachable at $APP_URL"
  echo ""
  echo "🔍 For detailed testing, run: ./test_deployment.sh"
  echo "💡 Try clicking the button on the page to test the REST API!"
else
  echo "⚠️  App not responding yet. Try again in ~30s:"
  echo "    curl $APP_URL"
  echo "    Or run: ./test_deployment.sh"
fi
