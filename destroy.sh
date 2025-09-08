#!/usr/bin/env bash
set -euo pipefail

echo "🗑️  Destroying Arvo baseline infrastructure"
echo "=========================================="
command -v terraform >/dev/null || { echo "❌ Terraform not installed"; exit 1; }
aws sts get-caller-identity >/dev/null || { echo "❌ AWS CLI not configured"; exit 1; }

if [ ! -f "terraform.tfstate" ] && [ ! -d ".terraform" ]; then
  echo "❌ No Terraform state found. Nothing to destroy."
  exit 0
fi

echo "📋 Plan (destroy)..."
terraform plan -destroy

read -p "🤔 Are you sure you want to destroy the infrastructure? (y/N): " -r ANSW
[[ "$ANSW" =~ ^[Yy]$ ]] || { echo "❌ Destruction cancelled"; exit 0; }

echo "💥 Destroying..."
terraform destroy -auto-approve
echo "🎉 Infrastructure destroyed successfully!"
echo "💡 To deploy again, run: ./deploy.sh"
