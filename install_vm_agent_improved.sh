#!/bin/bash
# Enhanced VM Agent Installation with Dedicated Virtual Environment
# This approach creates a stable virtual environment owned by the vm-agent user

set -e

# Configuration
ORCHESTRATOR_URL="${ORCHESTRATOR_URL:-https://your-orchestrator.com}"
VM_AGENT_DIR="/opt/vm-agent"
VM_AGENT_VENV="/opt/vm-agent-venv"
SOURCE_DIR="/root/vm_ai_agent"

echo "🚀 Enhanced VM Agent Installation"
echo "=================================="

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check if we're running as root
check_root() {
    if [ "$EUID" -ne 0 ]; then
        echo "❌ This script must be run as root (use sudo)"
        exit 1
    fi
}

# Function to detect Python version
detect_python() {
    if command_exists python3; then
        PYTHON_CMD="python3"
    elif command_exists python; then
        PYTHON_CMD="python"
    else
        echo "❌ Python 3 not found. Please install Python 3.8+"
        exit 1
    fi
    
    # Check Python version
    PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | grep -oE '[0-9]+\.[0-9]+')
    if [ "${PYTHON_VERSION%.*}" -lt 3 ] || [ "${PYTHON_VERSION#*.}" -lt 8 ]; then
        echo "❌ Python 3.8+ required. Found: $($PYTHON_CMD --version)"
        exit 1
    fi
    
    echo "✅ Using Python: $PYTHON_CMD ($($PYTHON_CMD --version))"
}

# Check prerequisites
check_root
detect_python

# Stop the service if running
echo "⏹️  Stopping existing service..."
systemctl stop vm-agent 2>/dev/null || true
systemctl disable vm-agent 2>/dev/null || true

# Clean up any existing installation
echo "🧹 Cleaning up existing installation..."
rm -rf "$VM_AGENT_DIR" "$VM_AGENT_VENV"
rm -f /etc/systemd/system/vm-agent.service

# Create proper directory structure
echo "📁 Creating directory structure..."
mkdir -p "$VM_AGENT_DIR"/{src,config,security,tenant,logs}
mkdir -p /var/log/vm-agent

# Copy source code to proper location
echo "📋 Copying source code..."
if [ -d "$SOURCE_DIR" ]; then
    cp -r "$SOURCE_DIR"/* "$VM_AGENT_DIR/src/"
    echo "✅ Source code copied from $SOURCE_DIR"
else
    echo "❌ Source directory $SOURCE_DIR not found!"
    echo "Please ensure vm_agent source is available at $SOURCE_DIR"
    exit 1
fi

# Create vm-agent user and group
echo "👤 Creating vm-agent user..."
if ! id vm-agent >/dev/null 2>&1; then
    useradd --system --home-dir "$VM_AGENT_DIR" --no-create-home --shell /bin/false vm-agent
    echo "✅ Created vm-agent user"
else
    echo "✅ vm-agent user already exists"
fi

# Set initial permissions
echo "🔒 Setting initial permissions..."
chown -R vm-agent:vm-agent "$VM_AGENT_DIR"
chown -R vm-agent:vm-agent /var/log/vm-agent
chmod -R 755 "$VM_AGENT_DIR/src"
chmod 700 "$VM_AGENT_DIR/security"
chmod 755 "$VM_AGENT_DIR"

# Create dedicated virtual environment
echo "🐍 Creating dedicated virtual environment..."
sudo -u vm-agent $PYTHON_CMD -m venv "$VM_AGENT_VENV"

# Upgrade pip first
echo "📦 Upgrading pip..."
sudo -u vm-agent "$VM_AGENT_VENV/bin/pip" install --upgrade pip

# Install all required dependencies (enhanced list)
echo "📦 Installing dependencies..."
sudo -u vm-agent "$VM_AGENT_VENV/bin/pip" install \
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
echo "📦 Installing vm_agent package..."
cd "$VM_AGENT_DIR/src"
sudo -u vm-agent "$VM_AGENT_VENV/bin/pip" install .

# Verify installation
echo "🔍 Verifying vm_agent installation..."
if sudo -u vm-agent "$VM_AGENT_VENV/bin/python" -c "import vm_agent; print('✅ vm_agent module imported successfully')" 2>/dev/null; then
    echo "✅ vm_agent package installed correctly"
else
    echo "❌ Failed to import vm_agent module"
    exit 1
fi

# Create configuration
echo "⚙️  Creating configuration..."
sudo -u vm-agent tee "$VM_AGENT_DIR/config/agent_config.yaml" > /dev/null << EOF
agent:
  id: vm-agent-$(hostname)
  name: "VM Agent"
  version: "1.0.0"

server:
  host: "0.0.0.0"
  port: 8080
  ssl:
    enabled: true
    cert_file: "$VM_AGENT_DIR/security/server.crt"
    key_file: "$VM_AGENT_DIR/security/server.key"

orchestrator:
  url: "$ORCHESTRATOR_URL"
  heartbeat_interval: 30
  command_poll_interval: 5

security:
  enabled: true
  mtls: true
  api_key_required: true

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

# Create systemd service with the dedicated virtual environment
echo "🔧 Creating systemd service..."
tee /etc/systemd/system/vm-agent.service > /dev/null << EOF
[Unit]
Description=VM Agent for AI Infrastructure Management
After=network.target
Wants=network.target

[Service]
Type=simple
User=vm-agent
Group=vm-agent
WorkingDirectory=$VM_AGENT_DIR
Environment=PYTHONPATH=$VM_AGENT_DIR/src
Environment=ORCHESTRATOR_URL=$ORCHESTRATOR_URL
ExecStart=$VM_AGENT_VENV/bin/python -m vm_agent.server
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
ReadWritePaths=$VM_AGENT_DIR /var/log/vm-agent

[Install]
WantedBy=multi-user.target
EOF

# Final permission setup
echo "🔍 Final permission setup..."
chown -R vm-agent:vm-agent "$VM_AGENT_DIR"
chown -R vm-agent:vm-agent "$VM_AGENT_VENV"
chown -R vm-agent:vm-agent /var/log/vm-agent

# Enable and start service
echo "🚀 Starting service..."
systemctl daemon-reload
systemctl enable vm-agent
systemctl start vm-agent

# Wait for service to start
echo "⏳ Waiting for service to start..."
sleep 5

# Comprehensive verification
echo "🔍 Verifying installation..."
SERVICE_STATUS=$(systemctl is-active vm-agent)

if [ "$SERVICE_STATUS" = "active" ]; then
    echo "✅ VM Agent service is running!"
    
    # Test health endpoint
    if curl -s http://localhost:8080/health >/dev/null 2>&1; then
        echo "✅ Health endpoint is accessible"
        echo ""
        echo "🎉 Installation completed successfully!"
    else
        echo "⚠️  Service is running but health endpoint not accessible yet"
        echo "   (This is normal, it may take a moment to fully initialize)"
    fi
else
    echo "❌ Service failed to start. Status: $SERVICE_STATUS"
    echo ""
    echo "📋 Checking logs..."
    journalctl -u vm-agent -n 20 --no-pager
    exit 1
fi

echo ""
echo "📋 Useful commands:"
echo "  sudo systemctl status vm-agent"
echo "  sudo systemctl restart vm-agent"
echo "  sudo journalctl -u vm-agent -f"
echo "  curl http://localhost:8080/health"
echo ""
echo "📁 Installation details:"
echo "  Source code: $VM_AGENT_DIR/src"
echo "  Virtual environment: $VM_AGENT_VENV"
echo "  Configuration: $VM_AGENT_DIR/config/agent_config.yaml"
echo "  Service file: /etc/systemd/system/vm-agent.service" 