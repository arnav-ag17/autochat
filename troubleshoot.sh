#!/usr/bin/env bash
set -euo pipefail
echo "🔍 Arvo Deployment Troubleshooting"

if ! command -v terraform >/dev/null || [ ! -f "terraform.tfstate" ]; then
  echo "❌ Terraform not found or no state"; exit 1
fi

PUBLIC_IP=$(terraform output -raw public_ip)
APP_URL="http://$PUBLIC_IP:8080"
echo "📍 Public IP: $PUBLIC_IP"
echo "🌐 URL: $APP_URL"
echo

echo "1️⃣ TCP checks"
nc -vz "$PUBLIC_IP" 22 || true
nc -vz "$PUBLIC_IP" 8080 || true
echo

echo "2️⃣ HTTP check"
curl -v --max-time 5 "$APP_URL" || true
echo

echo "3️⃣ If SSH enabled, check service logs:"
echo "   ssh -i arvo-key.pem ec2-user@$PUBLIC_IP"
echo "   sudo systemctl status flask-app --no-pager"
echo "   sudo journalctl -u flask-app -n 100 --no-pager"
