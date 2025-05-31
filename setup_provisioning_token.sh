#!/bin/bash
# Script to help get provisioning tokens from the orchestrator
# This demonstrates the full flow for setting up VM agents

set -e

ORCHESTRATOR_URL="${ORCHESTRATOR_URL:-https://80a6-188-123-163-160.ngrok-free.app}"

echo "🔐 VM Agent Provisioning Token Setup"
echo "===================================="
echo
echo "This script helps you get a provisioning token from the orchestrator"
echo "that can be used to automatically install and register VM agents."
echo
echo "Prerequisites:"
echo "1. You must have an account on the orchestrator"
echo "2. You must be a member of an organization with agent permissions"
echo "3. You need to authenticate and get your API token"
echo

# Step 1: Authenticate with orchestrator
echo "Step 1: Authentication"
echo "---------------------"
echo "First, you need to login to get your API token."
echo "Visit: $ORCHESTRATOR_URL/login"
echo
read -p "Enter your API token (from the orchestrator dashboard): " API_TOKEN

if [[ -z "$API_TOKEN" ]]; then
    echo "❌ API token is required"
    exit 1
fi

# Step 2: List organizations
echo
echo "Step 2: Get Organization ID"
echo "---------------------------"
echo "Fetching your organizations..."

ORGS_RESPONSE=$(curl -s -H "Authorization: Bearer $API_TOKEN" \
    "$ORCHESTRATOR_URL/api/v1/organizations/" || echo "failed")

if [[ "$ORGS_RESPONSE" == "failed" ]] || echo "$ORGS_RESPONSE" | grep -q "error"; then
    echo "❌ Failed to fetch organizations. Please check your API token."
    echo "Response: $ORGS_RESPONSE"
    exit 1
fi

echo "Available organizations:"
echo "$ORGS_RESPONSE" | grep -o '"id":"[^"]*"' | cut -d'"' -f4 | while read org_id; do
    echo "  - $org_id"
done

echo
read -p "Enter the Organization ID you want to use: " ORG_ID

if [[ -z "$ORG_ID" ]]; then
    echo "❌ Organization ID is required"
    exit 1
fi

# Step 3: Create provisioning token
echo
echo "Step 3: Create Provisioning Token"
echo "--------------------------------"
echo "Creating a new provisioning token for VM agent installation..."

TOKEN_PAYLOAD='{
    "expires_hours": 24,
    "metadata": {
        "purpose": "VM Agent Installation",
        "created_by_script": true
    }
}'

TOKEN_RESPONSE=$(curl -s -X POST \
    -H "Authorization: Bearer $API_TOKEN" \
    -H "Content-Type: application/json" \
    -d "$TOKEN_PAYLOAD" \
    "$ORCHESTRATOR_URL/api/v1/agents/organizations/$ORG_ID/provisioning-tokens" || echo "failed")

if [[ "$TOKEN_RESPONSE" == "failed" ]] || echo "$TOKEN_RESPONSE" | grep -q "error"; then
    echo "❌ Failed to create provisioning token."
    echo "Response: $TOKEN_RESPONSE"
    exit 1
fi

PROVISIONING_TOKEN=$(echo "$TOKEN_RESPONSE" | grep -o '"token":"[^"]*"' | cut -d'"' -f4)
EXPIRES_AT=$(echo "$TOKEN_RESPONSE" | grep -o '"expires_at":"[^"]*"' | cut -d'"' -f4)

if [[ -z "$PROVISIONING_TOKEN" ]]; then
    echo "❌ Failed to extract provisioning token from response"
    echo "Response: $TOKEN_RESPONSE"
    exit 1
fi

# Step 4: Provide installation instructions
echo
echo "✅ Provisioning Token Created Successfully!"
echo "=========================================="
echo
echo "Token: $PROVISIONING_TOKEN"
echo "Expires: $EXPIRES_AT"
echo
echo "🚀 Installation Instructions:"
echo "=============================="
echo
echo "1. Copy the enhanced installation script to your target VM:"
echo "   scp enhanced_install_vm_agent.sh user@target-vm:/tmp/"
echo
echo "2. Run the installation script on the target VM:"
echo "   sudo ORCHESTRATOR_URL=\"$ORCHESTRATOR_URL\" \\"
echo "        PROVISIONING_TOKEN=\"$PROVISIONING_TOKEN\" \\"
echo "        /tmp/enhanced_install_vm_agent.sh"
echo
echo "3. Alternative: Use the VM Agent CLI (if already installed):"
echo "   vm-agent provision --orchestrator-url \"$ORCHESTRATOR_URL\" \\"
echo "                      --provisioning-token \"$PROVISIONING_TOKEN\""
echo
echo "4. Alternative: One-liner for quick setup:"
echo "   curl -L https://your-repo.com/enhanced_install_vm_agent.sh | \\"
echo "   ORCHESTRATOR_URL=\"$ORCHESTRATOR_URL\" \\"
echo "   PROVISIONING_TOKEN=\"$PROVISIONING_TOKEN\" sudo bash"
echo
echo "📋 Post-Installation:"
echo "===================="
echo "• The agent will automatically register with the orchestrator"
echo "• You should see the new agent in your orchestrator dashboard"
echo "• The agent will start sending heartbeats every 30 seconds"
echo "• You can execute commands on the agent from the orchestrator"
echo
echo "🔍 Verification:"
echo "==============="
echo "• Check agent status: sudo systemctl status vm-agent"
echo "• View agent logs: sudo journalctl -u vm-agent -f"
echo "• Test health endpoint: curl http://localhost:8080/health"
echo "• Check orchestrator dashboard for the new agent"
echo
echo "⚠️  Security Notes:"
echo "=================="
echo "• The provisioning token expires in 24 hours"
echo "• Keep the token secure and don't share it"
echo "• After registration, the agent uses mTLS certificates"
echo "• The provisioning token cannot be reused after successful registration"
echo

# Optional: Save to file
read -p "Save these instructions to a file? (y/N): " SAVE_FILE
if [[ "$SAVE_FILE" =~ ^[Yy]$ ]]; then
    INSTRUCTIONS_FILE="vm_agent_setup_$(date +%Y%m%d_%H%M%S).txt"
    cat > "$INSTRUCTIONS_FILE" << EOF
VM Agent Installation Instructions
Generated: $(date)

Orchestrator URL: $ORCHESTRATOR_URL
Organization ID: $ORG_ID
Provisioning Token: $PROVISIONING_TOKEN
Token Expires: $EXPIRES_AT

Installation Command:
sudo ORCHESTRATOR_URL="$ORCHESTRATOR_URL" \\
     PROVISIONING_TOKEN="$PROVISIONING_TOKEN" \\
     ./enhanced_install_vm_agent.sh

Alternative CLI Command:
vm-agent provision --orchestrator-url "$ORCHESTRATOR_URL" \\
                   --provisioning-token "$PROVISIONING_TOKEN"

Post-installation verification:
- sudo systemctl status vm-agent
- sudo journalctl -u vm-agent -f
- curl http://localhost:8080/health
EOF
    echo "✅ Instructions saved to: $INSTRUCTIONS_FILE"
fi

echo
echo "🎉 Setup complete! You can now install VM agents using the provisioning token." 