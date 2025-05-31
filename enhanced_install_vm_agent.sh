#!/bin/bash
# Enhanced VM Agent Installation with Full Orchestrator Integration
# This script handles the complete flow: provisioning token → registration → certificate setup → service start

set -e

# Configuration
ORCHESTRATOR_URL="${ORCHESTRATOR_URL:-https://80a6-188-123-163-160.ngrok-free.app}"
PROVISIONING_TOKEN="${PROVISIONING_TOKEN:-}"
ORGANIZATION_ID="${ORGANIZATION_ID:-}"
INSTALL_DIR="/opt/vm-agent"
SERVICE_NAME="vm-agent"
USER="vm-agent"
GROUP="vm-agent"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root (use sudo)"
        exit 1
    fi
}

# Validate required parameters
validate_params() {
    if [[ -z "$ORCHESTRATOR_URL" ]]; then
        log_error "ORCHESTRATOR_URL is required"
        echo "Usage: ORCHESTRATOR_URL=https://your-orchestrator.com PROVISIONING_TOKEN=token sudo $0"
        exit 1
    fi

    if [[ -z "$PROVISIONING_TOKEN" && -z "$ORGANIZATION_ID" ]]; then
        log_error "Either PROVISIONING_TOKEN or ORGANIZATION_ID must be provided"
        echo "Usage: ORCHESTRATOR_URL=https://your-orchestrator.com PROVISIONING_TOKEN=token sudo $0"
        echo "   or: ORCHESTRATOR_URL=https://your-orchestrator.com ORGANIZATION_ID=org_id sudo $0"
        exit 1
    fi

    log_info "Configuration validated"
    log_info "Orchestrator URL: $ORCHESTRATOR_URL"
    if [[ -n "$PROVISIONING_TOKEN" ]]; then
        log_info "Using provisioning token: ${PROVISIONING_TOKEN:0:8}..."
    else
        log_info "Using organization ID: $ORGANIZATION_ID"
    fi
}

# Check system requirements
check_requirements() {
    log_info "Checking system requirements..."
    
    # Check Python 3.8+
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 is required but not installed"
        exit 1
    fi
    
    local python_version=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
    if [[ $(echo "$python_version < 3.8" | bc -l) -eq 1 ]]; then
        log_error "Python 3.8+ is required, found $python_version"
        exit 1
    fi
    
    # Check systemd
    if ! command -v systemctl &> /dev/null; then
        log_error "systemd is required but not found"
        exit 1
    fi
    
    # Check curl
    if ! command -v curl &> /dev/null; then
        log_error "curl is required but not installed"
        exit 1
    fi
    
    # Check openssl
    if ! command -v openssl &> /dev/null; then
        log_error "openssl is required but not installed"
        exit 1
    fi
    
    log_success "System requirements met"
}

# Test orchestrator connectivity
test_orchestrator() {
    log_info "Testing orchestrator connectivity..."
    
    local status_code=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 10 "$ORCHESTRATOR_URL/api/v1/docs" || echo "000")
    
    if [[ "$status_code" == "200" ]]; then
        log_success "Orchestrator is reachable"
    else
        log_error "Cannot reach orchestrator at $ORCHESTRATOR_URL (HTTP $status_code)"
        log_error "Please check the URL and network connectivity"
        exit 1
    fi
}

# Stop existing service
stop_existing_service() {
    log_info "Stopping existing service if running..."
    systemctl stop vm-agent 2>/dev/null || true
    systemctl disable vm-agent 2>/dev/null || true
    log_success "Existing service stopped"
}

# Create system user
create_user() {
    log_info "Creating system user..."
    
    # Check if user already exists
    if id "$USER" &>/dev/null; then
        log_success "User $USER already exists"
        return
    fi
    
    # Create group
    groupadd --system "$GROUP" 2>/dev/null || true
    
    # Create user
    useradd --system --gid "$GROUP" \
        --home-dir "$INSTALL_DIR" \
        --no-create-home \
        --shell /bin/false \
        "$USER"
    
    log_success "Created system user $USER"
}

# Create directory structure
create_directories() {
    log_info "Creating directory structure..."
    
    # Create main directories
    mkdir -p "$INSTALL_DIR"/{src,config,security,tenant,logs}
    mkdir -p /var/log/vm-agent
    
    # Create log files
    touch /var/log/vm-agent.log
    touch /var/log/vm-agent/agent.log
    
    # Set ownership
    chown -R "$USER:$GROUP" "$INSTALL_DIR"
    chown -R "$USER:$GROUP" /var/log/vm-agent
    chown "$USER:$GROUP" /var/log/vm-agent.log
    
    # Set permissions
    chmod 755 "$INSTALL_DIR"
    chmod 700 "$INSTALL_DIR/security"
    chmod 700 "$INSTALL_DIR/tenant"
    chmod 755 "$INSTALL_DIR/config"
    chmod 755 "$INSTALL_DIR/logs"
    chmod 644 /var/log/vm-agent.log
    chmod 644 /var/log/vm-agent/agent.log
    
    log_success "Directory structure created"
}

# Copy source code
copy_source() {
    log_info "Copying source code..."
    
    # Check if source exists in common locations
    local source_dir=""
    if [[ -d "/root/vm_ai_agent" ]]; then
        source_dir="/root/vm_ai_agent"
    elif [[ -d "$(pwd)/vm_agent" ]]; then
        source_dir="$(pwd)"
    elif [[ -d "/tmp/vm-agent" ]]; then
        source_dir="/tmp/vm-agent"
    else
        log_error "Source code not found. Please ensure vm_agent code is available."
        exit 1
    fi
    
    # Copy source
    cp -r "$source_dir"/* "$INSTALL_DIR/src/" 2>/dev/null || cp -r "$source_dir/vm_agent" "$INSTALL_DIR/src/"
    
    # Ensure ownership
    chown -R "$USER:$GROUP" "$INSTALL_DIR/src"
    
    log_success "Source code copied from $source_dir"
}

# Install Python dependencies
install_dependencies() {
    log_info "Installing Python dependencies..."
    
    # Create virtual environment
    sudo -u "$USER" python3 -m venv "$INSTALL_DIR/venv"
    
    # Upgrade pip
    sudo -u "$USER" "$INSTALL_DIR/venv/bin/pip" install --upgrade pip
    
    # Install required packages
    sudo -u "$USER" "$INSTALL_DIR/venv/bin/pip" install \
        aiofiles>=24.1.0 \
        aiohttp>=3.8.0 \
        aiohttp-cors>=0.7.0 \
        PyYAML>=6.0 \
        cryptography>=41.0.0 \
        psutil>=5.9.0 \
        websockets>=11.0 \
        asyncio-mqtt \
        pyjwt \
        paramiko \
        mcp \
        click
    
    # Install the vm_agent package
    cd "$INSTALL_DIR/src"
    sudo -u "$USER" "$INSTALL_DIR/venv/bin/pip" install -e .
    
    # Test installation
    if sudo -u "$USER" "$INSTALL_DIR/venv/bin/python" -c "import vm_agent; print('vm_agent imported successfully')" 2>/dev/null; then
        log_success "Dependencies installed and vm_agent package ready"
    else
        log_error "Failed to install vm_agent package"
        exit 1
    fi
}

# Generate VM ID and API key
generate_credentials() {
    log_info "Generating VM credentials..."
    
    # Generate VM ID
    local vm_id="vm-$(hostname)-$(date +%s | tail -c 6)"
    echo "$vm_id" > "$INSTALL_DIR/security/vm_id"
    
    # Generate API key
    local api_key=$(openssl rand -hex 32)
    echo "$api_key" > "$INSTALL_DIR/security/api_key"
    
    # Generate CSR for certificate
    local csr_config="$INSTALL_DIR/security/csr.conf"
    cat > "$csr_config" << EOF
[req]
distinguished_name = req_distinguished_name
req_extensions = v3_req
prompt = no

[req_distinguished_name]
C = US
ST = State
L = City
O = Organization
OU = VM Agent
CN = $vm_id

[v3_req]
keyUsage = keyEncipherment, dataEncipherment, digitalSignature
extendedKeyUsage = serverAuth, clientAuth
subjectAltName = @alt_names

[alt_names]
DNS.1 = $vm_id
DNS.2 = $(hostname)
IP.1 = $(hostname -I | awk '{print $1}')
EOF

    # Generate private key and CSR
    openssl genrsa -out "$INSTALL_DIR/security/vm_agent.key" 2048
    openssl req -new -key "$INSTALL_DIR/security/vm_agent.key" \
        -out "$INSTALL_DIR/security/vm_agent.csr" \
        -config "$csr_config"
    
    # Set permissions
    chmod 600 "$INSTALL_DIR/security/vm_agent.key"
    chmod 644 "$INSTALL_DIR/security/vm_agent.csr"
    chown "$USER:$GROUP" "$INSTALL_DIR/security"/*
    
    log_success "VM credentials generated (ID: $vm_id)"
    echo "$vm_id"  # Return the VM ID for use in registration
}

# Register with orchestrator
register_agent() {
    local vm_id="$1"
    log_info "Registering agent with orchestrator..."
    
    # Read generated credentials
    local api_key=$(cat "$INSTALL_DIR/security/api_key")
    local csr=$(cat "$INSTALL_DIR/security/vm_agent.csr")
    local hostname=$(hostname)
    
    # Base64 encode the CSR to avoid newline escaping issues
    local csr_base64=$(echo "$csr" | base64 -w 0)
    
    # Prepare registration payload using jq for better JSON handling
    local registration_payload=$(jq -n \
        --arg vm_id "$vm_id" \
        --arg api_key "$api_key" \
        --arg csr_base64 "$csr_base64" \
        --arg hostname "$hostname" \
        --arg agent_version "1.0.0" \
        --arg provisioning_token "$PROVISIONING_TOKEN" \
        '{
            vm_id: $vm_id,
            api_key: $api_key,
            csr_base64: $csr_base64,
            hostname: $hostname,
            agent_version: $agent_version,
            capabilities: {
                shell_executor: true,
                file_manager: true,
                system_monitor: true,
                log_analyzer: true
            }
        } + (if $provisioning_token != "" then {provisioning_token: $provisioning_token} else {} end)')
    
    # Call registration endpoint
    local response=$(curl -s -X POST "$ORCHESTRATOR_URL/api/v1/agents/register" \
        -H "Content-Type: application/json" \
        -d "$registration_payload" \
        --max-time 30)
    
    # Check if registration was successful
    if echo "$response" | jq -e '.agent_id' >/dev/null 2>&1; then
        # Parse response using jq for better handling
        local agent_id=$(echo "$response" | jq -r '.agent_id')
        local certificate=$(echo "$response" | jq -r '.certificate')
        local ca_certificate=$(echo "$response" | jq -r '.ca_certificate')
        local websocket_url=$(echo "$response" | jq -r '.websocket_url')
        
        # Save certificates
        echo "$certificate" > "$INSTALL_DIR/security/vm_agent.crt"
        echo "$ca_certificate" > "$INSTALL_DIR/security/ca.crt"
        echo "$agent_id" > "$INSTALL_DIR/security/agent_id"
        echo "$websocket_url" > "$INSTALL_DIR/security/websocket_url"
        
        # Set permissions
        chmod 644 "$INSTALL_DIR/security/vm_agent.crt"
        chmod 644 "$INSTALL_DIR/security/ca.crt"
        chown "$USER:$GROUP" "$INSTALL_DIR/security"/*
        
        log_success "Agent registered successfully (Agent ID: $agent_id)"
        return 0
    else
        log_error "Registration failed:"
        echo "$response" | head -5
        return 1
    fi
}

# Create configuration file
create_config() {
    local vm_id="$1"
    log_info "Creating configuration file..."
    
    # Read saved values
    local websocket_url=""
    if [[ -f "$INSTALL_DIR/security/websocket_url" ]]; then
        websocket_url=$(cat "$INSTALL_DIR/security/websocket_url")
    else
        websocket_url="$ORCHESTRATOR_URL/api/v1/agents/$vm_id/ws"
    fi
    
    cat > "$INSTALL_DIR/config/agent_config.yaml" << EOF
agent:
  id: $vm_id
  name: "VM Agent"
  version: "1.0.0"

server:
  host: "0.0.0.0"
  port: 8080
  ssl:
    enabled: true
    cert_file: "$INSTALL_DIR/security/vm_agent.crt"
    key_file: "$INSTALL_DIR/security/vm_agent.key"

orchestrator:
  url: "$ORCHESTRATOR_URL"
  websocket_url: "$websocket_url"
  heartbeat_interval: 30
  command_poll_interval: 5

security:
  enabled: true
  mtls: true
  api_key_required: true
  ca_cert_file: "$INSTALL_DIR/security/ca.crt"

tools:
  shell_executor:
    enabled: true
    timeout: 300
  file_manager:
    enabled: true
    max_file_size: "100MB"
  system_monitor:
    enabled: true
    interval: 60
  log_analyzer:
    enabled: true
    max_lines: 10000

logging:
  level: INFO
  file: "/var/log/vm-agent/agent.log"
  max_size: "100MB"
  backup_count: 5
EOF

    chown "$USER:$GROUP" "$INSTALL_DIR/config/agent_config.yaml"
    chmod 644 "$INSTALL_DIR/config/agent_config.yaml"
    
    log_success "Configuration file created"
}

# Create systemd service
create_service() {
    log_info "Creating systemd service..."
    
    cat > "/etc/systemd/system/$SERVICE_NAME.service" << EOF
[Unit]
Description=VM Agent for AI Infrastructure Management
After=network.target
Wants=network.target

[Service]
Type=simple
User=$USER
Group=$GROUP
WorkingDirectory=$INSTALL_DIR
Environment=PYTHONPATH=$INSTALL_DIR/src
Environment=ORCHESTRATOR_URL=$ORCHESTRATOR_URL
ExecStart=$INSTALL_DIR/venv/bin/python -m vm_agent.server --config $INSTALL_DIR/config/agent_config.yaml
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=vm-agent

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=$INSTALL_DIR /var/log/vm-agent /var/log/vm-agent.log

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    systemctl enable "$SERVICE_NAME"
    
    log_success "Systemd service created and enabled"
}

# Start and verify service
start_service() {
    log_info "Starting VM Agent service..."
    
    systemctl start "$SERVICE_NAME"
    sleep 5
    
    if systemctl is-active --quiet "$SERVICE_NAME"; then
        log_success "VM Agent service is running"
        
        # Show service status
        echo
        log_info "Service Status:"
        systemctl status "$SERVICE_NAME" --no-pager -l | head -15
        
        # Test health endpoint
        echo
        log_info "Testing health endpoint..."
        local health_response=$(curl -s "http://localhost:8080/health" 2>/dev/null || echo "unreachable")
        
        if echo "$health_response" | grep -q "healthy\|ok"; then
            log_success "Health endpoint is responding"
        else
            log_warning "Health endpoint not responding yet (service may still be starting)"
        fi
        
        return 0
    else
        log_error "Service failed to start"
        log_info "Checking logs..."
        journalctl -u "$SERVICE_NAME" -n 20 --no-pager
        return 1
    fi
}

# Show final status and usage info
show_final_status() {
    local vm_id="$1"
    
    echo
    echo "=================================="
    log_success "VM Agent Installation Complete!"
    echo "=================================="
    echo
    log_info "Agent Details:"
    echo "  VM ID: $vm_id"
    echo "  Install Directory: $INSTALL_DIR"
    echo "  Config File: $INSTALL_DIR/config/agent_config.yaml"
    echo "  Service Name: $SERVICE_NAME"
    echo
    log_info "Useful Commands:"
    echo "  sudo systemctl status $SERVICE_NAME"
    echo "  sudo systemctl restart $SERVICE_NAME"
    echo "  sudo journalctl -u $SERVICE_NAME -f"
    echo "  curl http://localhost:8080/health"
    echo "  curl http://localhost:8080/info"
    echo
    log_info "The agent should now be visible in your orchestrator dashboard."
}

# Cleanup function for failed installations
cleanup_on_failure() {
    log_error "Installation failed. Cleaning up..."
    systemctl stop "$SERVICE_NAME" 2>/dev/null || true
    systemctl disable "$SERVICE_NAME" 2>/dev/null || true
    rm -f "/etc/systemd/system/$SERVICE_NAME.service"
    systemctl daemon-reload
    # Note: We don't remove the install directory in case user wants to debug
}

# Main installation function
main() {
    echo "🚀 Enhanced VM Agent Installation"
    echo "================================="
    
    # Run all installation steps
    check_root
    validate_params
    check_requirements
    test_orchestrator
    stop_existing_service
    create_user
    create_directories
    copy_source
    install_dependencies
    
    # Generate credentials and register
    local vm_id=$(generate_credentials)
    
    if register_agent "$vm_id"; then
        create_config "$vm_id"
        create_service
        
        if start_service; then
            show_final_status "$vm_id"
            exit 0
        else
            cleanup_on_failure
            exit 1
        fi
    else
        log_error "Agent registration failed. Please check your provisioning token and try again."
        cleanup_on_failure
        exit 1
    fi
}

# Set trap for cleanup on error
trap 'cleanup_on_failure' ERR

# Run main installation
main "$@" 