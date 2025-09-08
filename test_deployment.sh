#!/bin/bash
# Test script to verify the deployment works correctly
set -euo pipefail

echo "🧪 Testing Arvo Deployment"
echo "========================="

# Get public IP from Terraform
if ! command -v terraform >/dev/null || [ ! -f "terraform.tfstate" ]; then
    echo "❌ Terraform not found or no state file"
    exit 1
fi

PUBLIC_IP=$(terraform output -raw public_ip)
APP_URL="http://$PUBLIC_IP:8080"
API_URL="http://$PUBLIC_IP:8080/api/message"

echo "📍 Public IP: $PUBLIC_IP"
echo "🌐 App URL: $APP_URL"
echo "🔗 API URL: $API_URL"
echo ""

# Test 1: Basic connectivity
echo "1️⃣ Testing basic connectivity..."
if curl -f -s --connect-timeout 10 "$APP_URL" > /dev/null; then
    echo "✅ Application is accessible"
else
    echo "❌ Application is not accessible"
    echo "💡 Check if EC2 instance is running and security group allows port 8080"
    exit 1
fi

# Test 2: API endpoint
echo ""
echo "2️⃣ Testing API endpoint..."
API_RESPONSE=$(curl -s --connect-timeout 10 "$API_URL" 2>/dev/null || echo "ERROR")
if [ "$API_RESPONSE" != "ERROR" ] && [ -n "$API_RESPONSE" ]; then
    echo "✅ API endpoint is responding"
    echo "📄 Response: $API_RESPONSE"
else
    echo "❌ API endpoint is not responding"
    echo "💡 This will cause 'error fetching message' in the frontend"
fi

# Test 3: CORS headers
echo ""
echo "3️⃣ Testing CORS headers..."
CORS_HEADERS=$(curl -s -I --connect-timeout 10 "$API_URL" 2>/dev/null | grep -i "access-control" || echo "No CORS headers")
echo "📋 CORS headers: $CORS_HEADERS"

# Test 4: Frontend content
echo ""
echo "4️⃣ Checking frontend content..."
FRONTEND_CONTENT=$(curl -s --connect-timeout 10 "$APP_URL" | grep -i "fetch\|api\|button" | head -3 || echo "No frontend content found")
echo "🔍 Frontend content: $FRONTEND_CONTENT"

echo ""
echo "📊 Test Summary"
echo "==============="
echo "🌐 Application URL: $APP_URL"
echo "🔗 API URL: $API_URL"
echo ""
echo "💡 If you see 'error fetching message' in the browser:"
echo "   1. Check that the API endpoint test above passed"
echo "   2. Check that CORS headers are present"
echo "   3. Open browser developer tools and check the Network tab"
echo "   4. Look for failed requests to the API endpoint"
echo ""
echo "🔧 To debug further:"
echo "   ssh -i your-key.pem ec2-user@$PUBLIC_IP"
echo "   sudo journalctl -u flask-app -f"
