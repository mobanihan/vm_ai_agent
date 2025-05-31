#!/bin/bash
# Fixed VM Agent Installation with Proper Permissions

set -e

echo "🔧 Fixing VM Agent installation..."

# Stop the service if running
echo "⏹️  Stopping service..."
sudo systemctl stop vm-agent 2>/dev/null || true

# Create proper directory structure
echo "📁 Creating directory structure..."
sudo mkdir -p /opt/vm-agent/{src,config,security,tenant,logs}
sudo mkdir -p /var/log/vm-agent

# Create log file with proper permissions
echo "📝 Creating log file..."
sudo touch /var/log/vm-agent.log /var/log/vm-agent/agent.log
sudo chown vm-agent:vm-agent /var/log/vm-agent.log /var/log/vm-agent/agent.log
sudo chmod 644 /var/log/vm-agent.log /var/log/vm-agent/agent.log

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

# Create virtual environment directory first as root, then change ownership
echo "🐍 Creating virtual environment directory..."
sudo mkdir -p /opt/vm-agent-venv
sudo chown vm-agent:vm-agent /opt/vm-agent-venv

# Now create virtual environment as vm-agent user
echo "🐍 Creating virtual environment..."
sudo -u vm-agent python3 -m venv /opt/vm-agent-venv

# Set permissions on source
echo "🔒 Setting permissions..."
sudo chown -R vm-agent:vm-agent /opt/vm-agent
sudo chmod -R 755 /opt/vm-agent/src
sudo chmod 700 /opt/vm-agent/security
sudo chmod 755 /opt/vm-agent

# Install dependencies as vm-agent user
echo "📦 Installing dependencies..."
sudo -u vm-agent /opt/vm-agent-venv/bin/pip install --upgrade pip
sudo -u vm-agent /opt/vm-agent-venv/bin/pip install aiofiles aiohttp aiohttp-cors PyYAML cryptography psutil websockets asyncio-mqtt pyjwt paramiko mcp click

# Install the vm_agent package
echo "📦 Installing vm_agent package..."
cd /opt/vm-agent/src
sudo -u vm-agent /opt/vm-agent-venv/bin/pip install .

# Test the installation
echo "🔍 Testing vm_agent import..."
if sudo -u vm-agent /opt/vm-agent-venv/bin/python -c "import vm_agent; print('✅ vm_agent imported successfully')" 2>/dev/null; then
    echo "✅ vm_agent package installed correctly"
else
    echo "❌ Failed to import vm_agent"
    exit 1
fi

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
  url: "${ORCHESTRATOR_URL:-https://your-orchestrator.com}"
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
Environment=ORCHESTRATOR_URL=${ORCHESTRATOR_URL:-https://your-orchestrator.com}
ExecStart=/opt/vm-agent-venv/bin/python -m vm_agent.server
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=vm-agent

# Security settings (relaxed for log file access)
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/vm-agent /var/log/vm-agent /var/log/vm-agent.log

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
sleep 5

# Check status
if sudo systemctl is-active --quiet vm-agent; then
    echo "✅ VM Agent is running successfully!"
    echo ""
    echo "📊 Service Status:"
    sudo systemctl status vm-agent --no-pager -l | head -10
    echo ""
    echo "🔍 Testing health endpoint..."
    if curl -s http://localhost:8080/health >/dev/null 2>&1; then
        echo "✅ Health endpoint is accessible"
    else
        echo "⚠️  Health endpoint not accessible yet (may still be starting)"
    fi
    echo ""
    echo "📋 Useful commands:"
    echo "  sudo systemctl status vm-agent"
    echo "  sudo journalctl -u vm-agent -f"
    echo "  curl http://localhost:8080/health"
else
    echo "❌ Service failed to start. Checking logs..."
    sudo journalctl -u vm-agent -n 20 --no-pager
fi 