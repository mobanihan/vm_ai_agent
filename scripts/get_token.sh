#!/bin/bash
#
# Simple script to obtain provisioning tokens from AI-Infra backend
# Usage: ./get_token.sh <backend_url> <username> <organization_id>
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# Check dependencies
if ! command -v curl &> /dev/null; then
    print_error "curl is required but not installed"
    exit 1
fi

if ! command -v jq &> /dev/null; then
    print_error "jq is required but not installed. Please install jq first."
    exit 1
fi

# Parse arguments
BACKEND_URL="${1}"
USERNAME="${2}"
ORG_ID="${3}"

if [ -z "$BACKEND_URL" ]; then
    echo "Usage: $0 <backend_url> [username] [organization_id]"
    echo ""
    echo "Examples:"
    echo "  $0 https://api.ai-infra.com"
    echo "  $0 https://api.ai-infra.com admin org-123"
    echo ""
    print_info "If username and org_id are not provided, interactive mode will be used"
    exit 1
fi

# Remove trailing slash from URL
BACKEND_URL="${BACKEND_URL%/}"

# Get credentials
if [ -z "$USERNAME" ]; then
    read -p "Username: " USERNAME
fi

read -s -p "Password: " PASSWORD
echo ""

# Authenticate and get access token
print_info "Authenticating with backend..."

AUTH_RESPONSE=$(curl -s -w "%{http_code}" \
    -X POST \
    -H "Content-Type: application/json" \
    -d "{\"username\":\"$USERNAME\",\"password\":\"$PASSWORD\"}" \
    "$BACKEND_URL/api/v1/auth/login" \
    -o /tmp/auth_response.json)

HTTP_CODE="${AUTH_RESPONSE: -3}"
if [ "$HTTP_CODE" -ne 200 ]; then
    print_error "Authentication failed (HTTP $HTTP_CODE)"
    if [ -f /tmp/auth_response.json ]; then
        cat /tmp/auth_response.json
    fi
    exit 1
fi

ACCESS_TOKEN=$(jq -r '.access_token' /tmp/auth_response.json 2>/dev/null)
if [ -z "$ACCESS_TOKEN" ] || [ "$ACCESS_TOKEN" = "null" ]; then
    print_error "Failed to extract access token from response"
    exit 1
fi

print_success "Authentication successful"

# If no org ID provided, list organizations
if [ -z "$ORG_ID" ]; then
    print_info "Fetching available organizations..."
    
    ORG_RESPONSE=$(curl -s -w "%{http_code}" \
        -H "Authorization: Bearer $ACCESS_TOKEN" \
        "$BACKEND_URL/api/v1/organizations" \
        -o /tmp/orgs_response.json)
    
    HTTP_CODE="${ORG_RESPONSE: -3}"
    if [ "$HTTP_CODE" -ne 200 ]; then
        print_error "Failed to fetch organizations (HTTP $HTTP_CODE)"
        exit 1
    fi
    
    # Display organizations
    echo ""
    echo "📋 Available Organizations:"
    echo "=========================="
    
    ORGS=$(jq -r '.organizations[] | "\(.id) - \(.name)"' /tmp/orgs_response.json)
    if [ -z "$ORGS" ]; then
        print_error "No organizations found"
        exit 1
    fi
    
    echo "$ORGS"
    echo ""
    read -p "Enter Organization ID: " ORG_ID
fi

# Get token parameters
echo ""
read -p "Token name (optional): " TOKEN_NAME
read -p "Token description (optional): " TOKEN_DESC
read -p "Token validity in hours (default: 24): " EXPIRES_HOURS
read -p "Maximum uses (default: 1): " MAX_USES

# Set defaults
TOKEN_NAME="${TOKEN_NAME:-Manual token - $(date '+%Y-%m-%d %H:%M')}"
TOKEN_DESC="${TOKEN_DESC:-Manually generated provisioning token}"
EXPIRES_HOURS="${EXPIRES_HOURS:-24}"
MAX_USES="${MAX_USES:-1}"

# Calculate expiration time
if command -v date &> /dev/null; then
    if date --version >/dev/null 2>&1; then
        # GNU date
        EXPIRES_AT=$(date -u -d "+${EXPIRES_HOURS} hours" +"%Y-%m-%dT%H:%M:%SZ")
    else
        # BSD date (macOS)
        EXPIRES_AT=$(date -u -v+"${EXPIRES_HOURS}"H +"%Y-%m-%dT%H:%M:%SZ")
    fi
else
    print_warning "Cannot calculate expiration time. Using 24 hours from now."
    EXPIRES_AT=$(python3 -c "from datetime import datetime, timedelta; print((datetime.utcnow() + timedelta(hours=$EXPIRES_HOURS)).isoformat() + 'Z')")
fi

# Create provisioning token
print_info "Creating provisioning token..."

TOKEN_DATA=$(cat <<EOF
{
    "organization_id": "$ORG_ID",
    "name": "$TOKEN_NAME",
    "description": "$TOKEN_DESC",
    "expires_at": "$EXPIRES_AT",
    "max_uses": $MAX_USES,
    "metadata": {}
}
EOF
)

TOKEN_RESPONSE=$(curl -s -w "%{http_code}" \
    -X POST \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -H "Content-Type: application/json" \
    -d "$TOKEN_DATA" \
    "$BACKEND_URL/api/v1/organizations/$ORG_ID/provisioning-tokens" \
    -o /tmp/token_response.json)

HTTP_CODE="${TOKEN_RESPONSE: -3}"
if [ "$HTTP_CODE" -ne 201 ]; then
    print_error "Failed to create token (HTTP $HTTP_CODE)"
    if [ -f /tmp/token_response.json ]; then
        cat /tmp/token_response.json
    fi
    exit 1
fi

# Extract and display token
TOKEN=$(jq -r '.token' /tmp/token_response.json)
TOKEN_ID=$(jq -r '.id' /tmp/token_response.json)

if [ -z "$TOKEN" ] || [ "$TOKEN" = "null" ]; then
    print_error "Failed to extract token from response"
    exit 1
fi

print_success "Provisioning token created successfully!"
echo ""
echo "================================"
echo "🔑 PROVISIONING TOKEN"
echo "================================"
echo "Token ID: $TOKEN_ID"
echo "Name: $TOKEN_NAME"
echo "Organization: $ORG_ID"
echo "Expires: $EXPIRES_AT"
echo "Max Uses: $MAX_USES"
echo ""
echo "TOKEN: $TOKEN"
echo "================================"
echo ""
echo "💡 Usage:"
echo "sudo vm-agent-install --orchestrator-url $BACKEND_URL --provisioning-token '$TOKEN'"
echo ""

# Option to save to file
read -p "Save token to file? (y/N): " SAVE_FILE
if [ "$SAVE_FILE" = "y" ] || [ "$SAVE_FILE" = "Y" ]; then
    FILENAME="provisioning_token_$(date +%Y%m%d_%H%M%S).txt"
    
    cat > "$FILENAME" <<EOF
# Provisioning Token for Organization $ORG_ID
# Created: $(date)
# Expires: $EXPIRES_AT
# Token ID: $TOKEN_ID

TOKEN=$TOKEN

# Installation command:
# sudo vm-agent-install --orchestrator-url $BACKEND_URL --provisioning-token '$TOKEN'
EOF
    
    print_success "Token saved to: $FILENAME"
fi

# Cleanup temporary files
rm -f /tmp/auth_response.json /tmp/orgs_response.json /tmp/token_response.json

print_success "Done!" 