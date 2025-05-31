#!/bin/bash
# Fix VM Agent Installation with Proper Permissions

set -e

echo "🔧 Fixing VM Agent installation..."

# Stop the service if running
echo "⏹️  Stopping service..."
sudo systemctl stop vm-agent 2>/dev/null || true

# Create proper directory structure
echo "📁 Creating directory structure..."
sudo mkdir -p /opt/vm-agent/{src,config,security,tenant,logs}
sudo mkdir -p /var/log/vm-agent

# Copy source code to proper location
echo "📋 Copying source code..."
if [ -d "/root/vm_ai_agent" ]; then
    sudo cp -r /root/vm_ai_agent/* /opt/vm-agent/src/
else
    echo "❌ Source directory /root/vm_ai_agent not found!"
    exit 1
fi

# Create user if doesn't exist
echo "👤 Ensuring vm-agent user exists..."
sudo useradd --system --home-dir /opt/vm-agent --no-create-home --shell /bin/false vm-agent 2>/dev/null || true

# Set permissions on source
echo "🔒 Setting permissions..."
sudo chown -R vm-agent:vm-agent /opt/vm-agent
sudo chmod -R 755 /opt/vm-agent/src
sudo chmod 700 /opt/vm-agent/security
sudo chmod 755 /opt/vm-agent

# Recreate virtual environment with correct ownership
echo "🐍 Recreating virtual environment..."
sudo rm -rf /opt/vm-agent-venv
sudo -u vm-agent python3 -m venv /opt/vm-agent-venv

# Install dependencies as vm-agent user
echo "📦 Installing dependencies..."
sudo -u vm-agent /opt/vm-agent-venv/bin/pip install --upgrade pip
sudo -u vm-agent /opt/vm-agent-venv/bin/pip install aiofiles aiohttp aiohttp-cors PyYAML cryptography psutil websockets asyncio-mqtt pyjwt paramiko mcp click

# Install the vm_agent package
echo "📦 Installing vm_agent package..."
cd /opt/vm-agent/src
sudo -u vm-agent /opt/vm-agent-venv/bin/pip install .

# Create configuration if doesn't exist
if [ ! -f "/opt/vm-agent/config/agent_config.yaml" ]; then
    echo "⚙️  Creating configuration..."
    sudo -u vm-agent tee /opt/vm-agent/config/agent_config.yaml > /dev/null << 'EOF'
agent:
  id: vm-agent-$(hostname)
  name: "VM Agent"
  version: "1.0.0"

server:
  host: "0.0.0.0"
  port: 8080
  ssl:
    enabled: true
    cert_file: "/opt/vm-agent/security/server.crt"
    key_file: "/opt/vm-agent/security/server.key"

orchestrator:
  url: "${ORCHESTRATOR_URL}"
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
EOF
fi

# Update systemd service
echo "🔧 Updating systemd service..."
sudo tee /etc/systemd/system/vm-agent.service > /dev/null << 'EOF'
[Unit]
Description=VM Agent for AI Infrastructure Management
After=network.target
Wants=network.target

[Service]
Type=simple
User=vm-agent
Group=vm-agent
WorkingDirectory=/opt/vm-agent
Environment=PYTHONPATH=/opt/vm-agent/src
Environment=ORCHESTRATOR_URL=${ORCHESTRATOR_URL:-https://80a6-188-123-163-160.ngrok-free.app}
ExecStart=/opt/vm-agent-venv/bin/python -m vm_agent.server
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
ReadWritePaths=/opt/vm-agent /var/log/vm-agent

[Install]
WantedBy=multi-user.target
EOF

# Final permission check
echo "🔍 Final permission check..."
sudo chown -R vm-agent:vm-agent /opt/vm-agent
sudo chown -R vm-agent:vm-agent /opt/vm-agent-venv
sudo chown -R vm-agent:vm-agent /var/log/vm-agent

# Reload and start service
echo "🚀 Starting service..."
sudo systemctl daemon-reload
sudo systemctl enable vm-agent
sudo systemctl start vm-agent

# Wait for service to start
sleep 3

# Check status
if sudo systemctl is-active --quiet vm-agent; then
    echo "✅ VM Agent is running successfully!"
    echo ""
    echo "📋 Check status with:"
    echo "  sudo systemctl status vm-agent"
    echo "  sudo journalctl -u vm-agent -f"
    echo "  curl http://localhost:8080/health"
else
    echo "⚠️  Service failed to start. Checking logs..."
    sudo journalctl -u vm-agent -n 20 --no-pager
fi