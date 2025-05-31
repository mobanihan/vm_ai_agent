#!/bin/bash
# VM Agent Complete Setup Script
# One-script solution: Environment setup + Orchestrator registration
# Usage: curl -fsSL https://your-server.com/setup.sh | sudo bash -s -- --provisioning-token "token" --server-url "https://orchestrator.com"

set -e

# Script version
VERSION="1.0.0"

# Default configuration
INSTALL_DIR="/opt/vm-agent"
SERVICE_NAME="vm-agent"
USER="vm-agent"
GROUP="vm-agent"
PYTHON_CMD="python3"

# Command line arguments
PROVISIONING_TOKEN=""
SERVER_URL=""
SKIP_DEPENDENCIES=false
FORCE_REINSTALL=false
DEBUG=false

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
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

log_debug() {
    if [[ "$DEBUG" == "true" ]]; then
        echo -e "${BOLD}🔍 DEBUG: $1${NC}"
    fi
}

# Show usage information
show_usage() {
    cat << EOF
${BOLD}VM Agent Complete Setup Script v${VERSION}${NC}

${BOLD}DESCRIPTION:${NC}
    Complete one-script solution for VM agent installation and orchestrator registration.
    Handles environment setup, dependencies, and full orchestrator integration.

${BOLD}USAGE:${NC}
    # Direct execution:
    sudo $0 --provisioning-token "token" --server-url "https://orchestrator.com"
    
    # One-liner with curl:
    curl -fsSL https://your-server.com/setup.sh | sudo bash -s -- \\
      --provisioning-token "eyJhbGciOiJIUzI1NiIs..." \\
      --server-url "https://your-orchestrator.com"

${BOLD}REQUIRED ARGUMENTS:${NC}
    --provisioning-token TOKEN    Provisioning token from orchestrator
    --server-url URL             Orchestrator server URL

${BOLD}OPTIONAL ARGUMENTS:${NC}
    --skip-dependencies          Skip system dependency installation
    --force-reinstall           Force reinstall even if already installed
    --debug                     Enable debug logging
    --help                      Show this help message

${BOLD}EXAMPLES:${NC}
    # Basic installation:
    curl -fsSL https://install.example.com/setup.sh | sudo bash -s -- \\
      --provisioning-token "prov_abc123..." \\
      --server-url "https://orchestrator.example.com"
    
    # With force reinstall:
    sudo ./setup.sh \\
      --provisioning-token "prov_abc123..." \\
      --server-url "https://orchestrator.example.com" \\
      --force-reinstall

${BOLD}WHAT THIS SCRIPT DOES:${NC}
    1. 📦 Installs system dependencies (curl, openssl, jq, python3)
    2. 🐍 Sets up Python environment and installs packages
    3. 🔐 Downloads CA certificate from orchestrator
    4. 🔑 Generates VM credentials and CSR
    5. 📝 Registers agent with orchestrator using provisioning token
    6. 📜 Installs signed certificates
    7. ⚙️  Creates complete agent configuration
    8. 👤 Sets up system user and permissions
    9. 🚀 Creates and starts systemd service
    10. ✅ Verifies everything is working

${BOLD}RESULT:${NC}
    Fully registered VM agent visible in orchestrator dashboard with:
    - ✅ Real-time WebSocket connection
    - ✅ Certificate-based authentication  
    - ✅ Automatic heartbeat monitoring
    - ✅ Ready to receive commands from orchestrator

EOF
}

# Parse command line arguments
parse_arguments() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --provisioning-token)
                PROVISIONING_TOKEN="$2"
                shift 2
                ;;
            --server-url)
                SERVER_URL="$2"
                shift 2
                ;;
            --skip-dependencies)
                SKIP_DEPENDENCIES=true
                shift
                ;;
            --force-reinstall)
                FORCE_REINSTALL=true
                shift
                ;;
            --debug)
                DEBUG=true
                shift
                ;;
            --help|-h)
                show_usage
                exit 0
                ;;
            *)
                log_error "Unknown argument: $1"
                show_usage
                exit 1
                ;;
        esac
    done
}

# Validate arguments
validate_arguments() {
    log_info "Validating arguments..."
    
    if [[ -z "$PROVISIONING_TOKEN" ]]; then
        log_error "Provisioning token is required"
        echo "Use: --provisioning-token \"your-token\""
        exit 1
    fi

    if [[ -z "$SERVER_URL" ]]; then
        log_error "Server URL is required"
        echo "Use: --server-url \"https://your-orchestrator.com\""
        exit 1
    fi

    # Clean up server URL (remove trailing slash)
    SERVER_URL="${SERVER_URL%/}"
    
    log_success "Arguments validated"
    log_info "Server URL: $SERVER_URL"
    log_info "Provisioning Token: ${PROVISIONING_TOKEN:0:8}..."
}

# Check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root (use sudo)"
        echo ""
        echo "Try: sudo $0 --provisioning-token \"token\" --server-url \"https://orchestrator.com\""
        echo "Or:  curl -fsSL https://install.example.com/setup.sh | sudo bash -s -- --provisioning-token \"token\" --server-url \"https://orchestrator.com\""
        exit 1
    fi
}

# Detect operating system
detect_os() {
    log_info "Detecting operating system..."
    
    if [[ -f /etc/os-release ]]; then
        . /etc/os-release
        OS=$ID
        OS_VERSION=$VERSION_ID
        OS_NAME=$PRETTY_NAME
    else
        log_error "Cannot detect operating system"
        exit 1
    fi
    
    log_success "Detected: $OS_NAME"
    log_debug "OS: $OS, Version: $OS_VERSION"
}

# Install system dependencies
install_dependencies() {
    if [[ "$SKIP_DEPENDENCIES" == "true" ]]; then
        log_info "Skipping dependency installation..."
        return 0
    fi
    
    log_info "Installing system dependencies..."
    
    case $OS in
        ubuntu|debian)
            apt-get update -qq
            apt-get install -y curl openssl jq python3 python3-pip python3-venv python3-dev build-essential
            ;;
        centos|rhel|fedora)
            if command -v dnf &> /dev/null; then
                dnf install -y curl openssl jq python3 python3-pip python3-devel gcc
            else
                yum install -y curl openssl jq python3 python3-pip python3-devel gcc
            fi
            ;;
        *)
            log_warning "Unsupported OS: $OS. Trying to install dependencies anyway..."
            # Try common package managers
            if command -v apt-get &> /dev/null; then
                apt-get update && apt-get install -y curl openssl jq python3 python3-pip python3-venv
            elif command -v yum &> /dev/null; then
                yum install -y curl openssl jq python3 python3-pip
            elif command -v dnf &> /dev/null; then
                dnf install -y curl openssl jq python3 python3-pip
            else
                log_error "No supported package manager found"
                exit 1
            fi
            ;;
    esac
    
    log_success "System dependencies installed"
}

# Check if agent is already installed
check_existing_installation() {
    if [[ "$FORCE_REINSTALL" == "true" ]]; then
        log_info "Force reinstall requested, removing existing installation..."
        systemctl stop $SERVICE_NAME 2>/dev/null || true
        systemctl disable $SERVICE_NAME 2>/dev/null || true
        rm -rf "$INSTALL_DIR"
        rm -f "/etc/systemd/system/$SERVICE_NAME.service"
        systemctl daemon-reload
        return 0
    fi
    
    if systemctl is-active --quiet $SERVICE_NAME 2>/dev/null; then
        log_warning "VM Agent is already running"
        log_info "Use --force-reinstall to reinstall"
        log_info "Current status:"
        systemctl status $SERVICE_NAME --no-pager -l | head -10
        exit 0
    fi
    
    if [[ -d "$INSTALL_DIR" ]]; then
        log_warning "Installation directory exists: $INSTALL_DIR"
        log_info "Use --force-reinstall to clean and reinstall"
        exit 0
    fi
}

# Test orchestrator connectivity
test_orchestrator_connectivity() {
    log_info "Testing orchestrator connectivity..."
    
    local status_code=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 10 "$SERVER_URL/api/v1/docs" || echo "000")
    
    if [[ "$status_code" == "200" ]]; then
        log_success "Orchestrator is reachable"
    else
        log_error "Cannot reach orchestrator at $SERVER_URL (HTTP $status_code)"
        log_error "Please check the URL and network connectivity"
        exit 1
    fi
}

# Step 1: Get CA Certificate from orchestrator
get_ca_certificate() {
    log_info "Step 1: Getting CA certificate from orchestrator..."
    
    local ca_cert_response=$(curl -s -X GET "$SERVER_URL/api/v1/agents/ca-certificate" 2>/dev/null)
    
    if [[ $? -ne 0 ]] || [[ -z "$ca_cert_response" ]]; then
        log_error "Failed to get CA certificate from orchestrator"
        exit 1
    fi
    
    # Create security directory
    mkdir -p "$INSTALL_DIR/security"
    
    # Save CA certificate (handle both JSON and raw certificate responses)
    if echo "$ca_cert_response" | jq -e . >/dev/null 2>&1; then
        # JSON response
        echo "$ca_cert_response" | jq -r '.' > "$INSTALL_DIR/security/ca.crt"
    else
        # Raw certificate
        echo "$ca_cert_response" > "$INSTALL_DIR/security/ca.crt"
    fi
    
    if [[ ! -s "$INSTALL_DIR/security/ca.crt" ]]; then
        log_error "Failed to save CA certificate"
        exit 1
    fi
    
    log_success "CA certificate downloaded and saved"
}

# Step 2: Generate VM credentials and CSR
generate_vm_credentials() {
    log_info "Step 2: Generating VM credentials and CSR..."
    
    # Generate unique VM ID
    local vm_id="vm-$(hostname)-$(date +%s | tail -c 6)"
    echo "$vm_id" > "$INSTALL_DIR/security/vm_id"
    
    # Generate API key
    local api_key=$(openssl rand -hex 32)
    echo "$api_key" > "$INSTALL_DIR/security/api_key"
    
    # Generate private key
    log_debug "Generating RSA private key..."
    openssl genrsa -out "$INSTALL_DIR/security/vm_agent.key" 2048 2>/dev/null
    
    # Get local IP address
    local local_ip=$(hostname -I | awk '{print $1}' 2>/dev/null || ip route get 1 | grep -oP 'src \K\S+' 2>/dev/null || echo '127.0.0.1')
    local hostname_fqdn=$(hostname -f 2>/dev/null || hostname)
    
    log_debug "VM ID: $vm_id"
    log_debug "Hostname: $(hostname)"
    log_debug "FQDN: $hostname_fqdn"
    log_debug "Local IP: $local_ip"
    
    # Create CSR configuration
    cat > "$INSTALL_DIR/security/csr.conf" << EOF
[req]
distinguished_name = req_distinguished_name
req_extensions = v3_req
prompt = no

[req_distinguished_name]
C = US
ST = State
L = City
O = VM Agent Organization
OU = VM Agent Unit
CN = $vm_id

[v3_req]
basicConstraints = CA:FALSE
keyUsage = nonRepudiation, digitalSignature, keyEncipherment
subjectAltName = @alt_names

[alt_names]
DNS.1 = $vm_id
DNS.2 = $(hostname)
DNS.3 = $hostname_fqdn
IP.1 = $local_ip
IP.2 = 127.0.0.1
EOF

    # Generate CSR
    log_debug "Generating Certificate Signing Request..."
    openssl req -new -key "$INSTALL_DIR/security/vm_agent.key" \
        -out "$INSTALL_DIR/security/vm_agent.csr" \
        -config "$INSTALL_DIR/security/csr.conf" 2>/dev/null
    
    if [[ $? -ne 0 ]]; then
        log_error "Failed to generate CSR"
        exit 1
    fi
    
    # Validate CSR
    log_debug "Validating generated CSR..."
    if openssl req -in "$INSTALL_DIR/security/vm_agent.csr" -text -noout >/dev/null 2>&1; then
        log_debug "CSR validation successful"
        
        # Show CSR details in debug mode
        if [[ "$DEBUG" == "true" ]]; then
            log_debug "CSR Subject:"
            openssl req -in "$INSTALL_DIR/security/vm_agent.csr" -subject -noout 2>/dev/null | sed 's/^subject=/  /'
            log_debug "CSR Alternative Names:"
            openssl req -in "$INSTALL_DIR/security/vm_agent.csr" -text -noout 2>/dev/null | grep -A 5 "Subject Alternative Name" | sed 's/^/  /'
        fi
    else
        log_error "Generated CSR is invalid"
        exit 1
    fi
    
    # Set proper permissions
    chmod 600 "$INSTALL_DIR/security/vm_agent.key"
    chmod 644 "$INSTALL_DIR/security/vm_agent.csr"
    chmod 644 "$INSTALL_DIR/security/ca.crt"
    chmod 644 "$INSTALL_DIR/security/csr.conf"
    
    log_success "VM credentials generated (ID: $vm_id)"
    echo "$vm_id"  # Return the VM ID
}

# Step 3: Register agent with orchestrator
register_agent() {
    local vm_id="$1"
    log_info "Step 3: Registering agent with orchestrator..."
    
    # Read generated credentials
    local api_key=$(cat "$INSTALL_DIR/security/api_key")
    local csr=$(cat "$INSTALL_DIR/security/vm_agent.csr")
    local hostname=$(hostname)
    
    # Properly escape CSR for JSON (replace newlines with \n)
    local csr_escaped=$(echo "$csr" | sed ':a;N;$!ba;s/\n/\\n/g' | sed 's/\r//g')
    
    # Escape other fields for JSON safety
    local hostname_escaped=$(echo "$hostname" | sed 's/"/\\"/g')
    local vm_id_escaped=$(echo "$vm_id" | sed 's/"/\\"/g')
    local api_key_escaped=$(echo "$api_key" | sed 's/"/\\"/g')
    local token_escaped=$(echo "$PROVISIONING_TOKEN" | sed 's/"/\\"/g')
    
    # Prepare registration payload using jq to ensure valid JSON
    local registration_payload=$(jq -n \
        --arg vm_id "$vm_id_escaped" \
        --arg api_key "$api_key_escaped" \
        --arg csr "$csr_escaped" \
        --arg hostname "$hostname_escaped" \
        --arg agent_version "$VERSION" \
        --arg provisioning_token "$token_escaped" \
        '{
            vm_id: $vm_id,
            api_key: $api_key,
            csr: $csr,
            hostname: $hostname,
            agent_version: $agent_version,
            capabilities: {
                shell_executor: true,
                file_manager: true,
                system_monitor: true,
                log_analyzer: true
            },
            provisioning_token: $provisioning_token
        }')
    
    log_debug "Calling registration endpoint: $SERVER_URL/api/v1/agents/register"
    log_debug "Payload size: $(echo "$registration_payload" | wc -c) bytes"
    
    # Call agent registration endpoint
    local response=$(curl -s -X POST "$SERVER_URL/api/v1/agents/register" \
        -H "Content-Type: application/json" \
        -d "$registration_payload" \
        --max-time 30)
    
    if [[ $? -ne 0 ]]; then
        log_error "Failed to connect to registration endpoint"
        exit 1
    fi
    
    log_debug "Registration response: ${response:0:200}..."
    
    # Check if registration was successful
    local agent_id=$(echo "$response" | jq -r '.agent_id // empty' 2>/dev/null)
    
    if [[ -z "$agent_id" ]] || [[ "$agent_id" == "null" ]]; then
        log_error "Registration failed. Response:"
        echo "$response" | head -5
        
        # Additional debugging for different error types
        if echo "$response" | grep -q "JSON decode error"; then
            log_error "JSON payload validation failed. Checking payload..."
            if echo "$registration_payload" | jq . >/dev/null 2>&1; then
                log_info "Payload JSON is valid"
            else
                log_error "Payload JSON is invalid!"
                echo "$registration_payload" | head -5
            fi
        elif echo "$response" | grep -q "Failed to sign certificate"; then
            log_error "Certificate signing failed. Debugging..."
            
            # Check if CSR is valid
            if openssl req -in "$INSTALL_DIR/security/vm_agent.csr" -text -noout >/dev/null 2>&1; then
                log_info "CSR is structurally valid"
                
                # Show CSR details for debugging
                log_info "CSR Details:"
                echo "  Subject: $(openssl req -in "$INSTALL_DIR/security/vm_agent.csr" -subject -noout 2>/dev/null | sed 's/^subject=//')"
                echo "  Key size: $(openssl req -in "$INSTALL_DIR/security/vm_agent.csr" -noout -text 2>/dev/null | grep -o 'Public-Key: ([0-9]* bit)' || echo 'Unknown')"
                
                # Check if provisioning token looks valid
                if [[ ${#PROVISIONING_TOKEN} -lt 10 ]]; then
                    log_warning "Provisioning token seems too short (${#PROVISIONING_TOKEN} chars)"
                elif [[ ${#PROVISIONING_TOKEN} -gt 1000 ]]; then
                    log_warning "Provisioning token seems too long (${#PROVISIONING_TOKEN} chars)"
                else
                    log_info "Provisioning token length seems reasonable (${#PROVISIONING_TOKEN} chars)"
                fi
                
                # Check token format (basic validation)
                if [[ "$PROVISIONING_TOKEN" =~ ^[A-Za-z0-9+/=._-]+$ ]]; then
                    log_info "Provisioning token format looks valid"
                else
                    log_warning "Provisioning token contains unexpected characters"
                fi
                
            else
                log_error "CSR is structurally invalid!"
                log_info "CSR file size: $(wc -c < "$INSTALL_DIR/security/vm_agent.csr") bytes"
            fi
            
            # Check if the orchestrator is rejecting the request for other reasons
            log_info "Possible causes:"
            echo "  1. Provisioning token expired or invalid"
            echo "  2. Provisioning token already used"
            echo "  3. Organization quota exceeded"
            echo "  4. CSR format not accepted by orchestrator"
            echo "  5. Network/connectivity issues"
            
        elif echo "$response" | grep -q "token"; then
            log_error "Token-related error detected"
            log_info "Please check:"
            echo "  1. Token is not expired (tokens typically expire in 24 hours)"
            echo "  2. Token hasn't been used already"
            echo "  3. Token is for the correct organization"
            
        else
            log_error "Unknown registration error"
            log_info "Full response:"
            echo "$response"
        fi
        
        exit 1
    fi
    
    # Parse and save response data
    local certificate=$(echo "$response" | jq -r '.certificate // empty')
    local ca_certificate=$(echo "$response" | jq -r '.ca_certificate // empty')
    local websocket_url=$(echo "$response" | jq -r '.websocket_url // empty')
    local certificate_serial=$(echo "$response" | jq -r '.certificate_serial // empty')
    
    if [[ -z "$certificate" ]] || [[ "$certificate" == "null" ]]; then
        log_error "Invalid response: missing certificate"
        exit 1
    fi
    
    # Save certificates and registration data
    echo "$certificate" > "$INSTALL_DIR/security/vm_agent.crt"
    echo "$ca_certificate" > "$INSTALL_DIR/security/ca.crt"
    echo "$agent_id" > "$INSTALL_DIR/security/agent_id"
    echo "$websocket_url" > "$INSTALL_DIR/security/websocket_url"
    echo "$certificate_serial" > "$INSTALL_DIR/security/certificate_serial"
    
    # Set permissions
    chmod 644 "$INSTALL_DIR/security/vm_agent.crt"
    chmod 644 "$INSTALL_DIR/security/ca.crt"
    chmod 644 "$INSTALL_DIR/security/agent_id"
    chmod 644 "$INSTALL_DIR/security/websocket_url"
    chmod 644 "$INSTALL_DIR/security/certificate_serial"
    
    log_success "Agent registered successfully"
    log_info "Agent ID: $agent_id"
    log_info "WebSocket URL: $websocket_url"
    
    return 0
}

# Step 4: Set up system user and directories
setup_system() {
    log_info "Step 4: Setting up system user and directories..."
    
    # Create group and user
    if ! getent group "$GROUP" >/dev/null 2>&1; then
        groupadd --system "$GROUP"
        log_debug "Created group: $GROUP"
    fi
    
    if ! id "$USER" &>/dev/null; then
        useradd --system --gid "$GROUP" \
            --home-dir "$INSTALL_DIR" \
            --no-create-home \
            --shell /bin/false \
            "$USER"
        log_debug "Created user: $USER"
    fi
    
    # Create directory structure
    mkdir -p "$INSTALL_DIR"/{src,config,security,logs}
    mkdir -p /var/log/vm-agent
    
    # Create log files
    touch /var/log/vm-agent.log
    touch /var/log/vm-agent/agent.log
    
    # Set ownership and permissions
    chown -R "$USER:$GROUP" "$INSTALL_DIR"
    chown -R "$USER:$GROUP" /var/log/vm-agent
    chown "$USER:$GROUP" /var/log/vm-agent.log
    
    chmod 755 "$INSTALL_DIR"
    chmod 700 "$INSTALL_DIR/security"
    chmod 755 "$INSTALL_DIR/config"
    chmod 644 /var/log/vm-agent.log
    chmod 644 /var/log/vm-agent/agent.log
    
    log_success "System setup completed"
}

# Step 5: Set up Python environment and install VM agent
setup_python_environment() {
    log_info "Step 5: Setting up Python environment..."
    
    # Create virtual environment
    log_debug "Creating virtual environment at $INSTALL_DIR/venv"
    $PYTHON_CMD -m venv "$INSTALL_DIR/venv"
    
    # Activate virtual environment and install dependencies
    source "$INSTALL_DIR/venv/bin/activate"
    
    # Upgrade pip
    pip install --upgrade pip
    
    # Install required packages
    log_info "Installing Python packages..."
    pip install aiofiles aiohttp aiohttp-cors PyYAML cryptography psutil websockets asyncio-mqtt pyjwt paramiko mcp click
    
    # Install vm_agent if source is available
    if [[ -d "$(dirname "$0")/vm_agent" ]]; then
        log_info "Installing vm_agent from source..."
        cp -r "$(dirname "$0")/vm_agent" "$INSTALL_DIR/src/"
        cp "$(dirname "$0")"/*.py "$INSTALL_DIR/src/" 2>/dev/null || true
        
        # Install the package
        cd "$INSTALL_DIR/src"
        pip install .
    else
        log_warning "VM agent source not found. Service may fail to start."
        log_info "Please ensure vm_agent source is available."
    fi
    
    deactivate
    
    # Set ownership
    chown -R "$USER:$GROUP" "$INSTALL_DIR/venv"
    chown -R "$USER:$GROUP" "$INSTALL_DIR/src"
    
    log_success "Python environment setup completed"
}

# Step 6: Create agent configuration
create_agent_config() {
    local vm_id="$1"
    log_info "Step 6: Creating agent configuration..."
    
    # Read saved values
    local agent_id=$(cat "$INSTALL_DIR/security/agent_id")
    local websocket_url=$(cat "$INSTALL_DIR/security/websocket_url")
    
    cat > "$INSTALL_DIR/config/agent_config.yaml" << EOF
agent:
  id: $vm_id
  name: "VM Agent"
  version: "$VERSION"

server:
  host: "0.0.0.0"
  port: 8080
  ssl:
    enabled: true
    cert_file: "$INSTALL_DIR/security/vm_agent.crt"
    key_file: "$INSTALL_DIR/security/vm_agent.key"

orchestrator:
  url: "$SERVER_URL"
  websocket_url: "$websocket_url"
  agent_id: "$agent_id"
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
    
    log_success "Agent configuration created"
}

# Step 7: Create systemd service
create_systemd_service() {
    log_info "Step 7: Creating systemd service..."
    
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
Environment=PATH=$INSTALL_DIR/venv/bin:/usr/bin:/bin
Environment=PYTHONPATH=$INSTALL_DIR/src
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

# Step 8: Start and verify service
start_and_verify_service() {
    log_info "Step 8: Starting VM agent service..."
    
    systemctl start "$SERVICE_NAME"
    sleep 5
    
    if systemctl is-active --quiet "$SERVICE_NAME"; then
        log_success "VM Agent service is running"
        
        # Wait a bit more for full startup
        sleep 5
        
        # Test health endpoint
        log_info "Testing health endpoint..."
        local health_response=$(curl -s "http://localhost:8080/health" 2>/dev/null || echo "unreachable")
        
        if echo "$health_response" | grep -q '"status"'; then
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

# Step 9: Test heartbeat connectivity
test_heartbeat() {
    log_info "Step 9: Testing orchestrator connectivity..."
    
    local agent_id=$(cat "$INSTALL_DIR/security/agent_id")
    local api_key=$(cat "$INSTALL_DIR/security/api_key")
    
    # Prepare heartbeat payload
    local heartbeat_payload=$(cat << EOF
{
    "status": "online",
    "metrics": {
        "uptime": 0,
        "cpu_usage": 0.0,
        "memory_usage": 0.0,
        "disk_usage": 0.0
    }
}
EOF
    )
    
    # Send test heartbeat
    local heartbeat_response=$(curl -s -X POST "$SERVER_URL/api/v1/agents/$agent_id/heartbeat" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $api_key" \
        -d "$heartbeat_payload" \
        --max-time 10 2>/dev/null || echo "failed")
    
    if [[ "$heartbeat_response" != "failed" ]] && echo "$heartbeat_response" | grep -q "acknowledged"; then
        log_success "Heartbeat test successful - Agent connected to orchestrator"
    else
        log_warning "Heartbeat test failed, but agent should connect automatically"
        log_info "The agent will establish connection when fully started"
    fi
}

# Show final status and information
show_final_status() {
    local vm_id="$1"
    local agent_id=$(cat "$INSTALL_DIR/security/agent_id" 2>/dev/null || echo "unknown")
    
    echo
    echo "==========================================="
    log_success "🎉 VM Agent Installation Complete!"
    echo "==========================================="
    echo
    log_info "${BOLD}Agent Details:${NC}"
    echo "  VM ID: $vm_id"
    echo "  Agent ID: $agent_id"
    echo "  Orchestrator: $SERVER_URL"
    echo "  Install Directory: $INSTALL_DIR"
    echo "  Config File: $INSTALL_DIR/config/agent_config.yaml"
    echo "  Service Name: $SERVICE_NAME"
    echo
    log_info "${BOLD}Service Status:${NC}"
    if systemctl is-active --quiet "$SERVICE_NAME"; then
        echo "  Status: ${GREEN}Running${NC}"
    else
        echo "  Status: ${RED}Not Running${NC}"
    fi
    echo
    log_info "${BOLD}Useful Commands:${NC}"
    echo "  sudo systemctl status $SERVICE_NAME"
    echo "  sudo systemctl restart $SERVICE_NAME"
    echo "  sudo journalctl -u $SERVICE_NAME -f"
    echo "  curl http://localhost:8080/health"
    echo "  curl http://localhost:8080/info"
    echo
    log_success "✅ The agent should now be visible in your orchestrator dashboard"
    log_success "✅ WebSocket connection will be established automatically"
    log_success "✅ Ready to receive commands from orchestrator"
    echo
}

# Cleanup function for failed installations
cleanup_on_failure() {
    log_error "Setup failed. Cleaning up..."
    systemctl stop "$SERVICE_NAME" 2>/dev/null || true
    systemctl disable "$SERVICE_NAME" 2>/dev/null || true
    rm -f "/etc/systemd/system/$SERVICE_NAME.service"
    systemctl daemon-reload
    log_info "Install directory preserved for debugging: $INSTALL_DIR"
}

# Main installation function
main() {
    echo
    echo "${BOLD}🚀 VM Agent Complete Setup Script v${VERSION}${NC}"
    echo "${BOLD}One-script solution: Environment + Registration${NC}"
    echo "=============================================="
    echo
    
    # Parse and validate arguments
    parse_arguments "$@"
    validate_arguments
    
    # System checks
    check_root
    detect_os
    check_existing_installation
    
    # Install dependencies and test connectivity
    install_dependencies
    test_orchestrator_connectivity
    
    echo
    log_info "${BOLD}Starting agent registration and setup...${NC}"
    echo
    
    # Main installation flow
    get_ca_certificate
    local vm_id=$(generate_vm_credentials)
    register_agent "$vm_id"
    setup_system
    setup_python_environment
    create_agent_config "$vm_id"
    create_systemd_service
    
    # Start and verify
    if start_and_verify_service; then
        test_heartbeat
        show_final_status "$vm_id"
        exit 0
    else
        cleanup_on_failure
        exit 1
    fi
}

# Set error trap
trap 'cleanup_on_failure' ERR

# Handle the case where this script is run via curl | bash
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi 