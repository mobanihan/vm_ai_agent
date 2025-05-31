#!/bin/bash
# VM Agent Installation Script - PEP 668 Compatible

set -e

echo "🚀 VM Agent Installation (PEP 668 Compatible)"

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "❌ Please run as root (use sudo)"
    exit 1
fi

# Get orchestrator URL
ORCHESTRATOR_URL="${1:-https://your-orchestrator.com}"
echo "📡 Orchestrator URL: $ORCHESTRATOR_URL"

# Create dedicated virtual environment
echo "🔧 Creating dedicated virtual environment..."
python3 -m venv /opt/vm-agent-venv

# Install dependencies
echo "📦 Installing dependencies..."
/opt/vm-agent-venv/bin/pip install --upgrade pip
/opt/vm-agent-venv/bin/pip install aiofiles aiohttp aiohttp-cors PyYAML cryptography psutil websockets asyncio-mqtt pyjwt paramiko mcp click

# Install vm_agent from current directory
if [ -d "/root/vm_ai_agent" ]; then
    echo "📦 Installing vm_agent package..."
    /opt/vm-agent-venv/bin/pip install -e /root/vm_ai_agent
fi

# Create user
echo "👤 Creating vm-agent user..."
useradd --system --home-dir /opt/vm-agent --no-create-home --shell /bin/false vm-agent 2>/dev/null || true

# Create directories
echo "📁 Creating directories..."
mkdir -p /opt/vm-agent/{security,tenant,logs,config}
mkdir -p /var/log/vm-agent

# Create configuration
echo "⚙️ Creating configuration..."
cat > /opt/vm-agent/config/agent_config.yaml << EOF
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
EOF

# Create systemd service
echo "🔧 Creating systemd service..."
cat > /etc/systemd/system/vm-agent.service << 'EOF'
[Unit]
Description=VM Agent for AI Infrastructure Management
After=network.target
Wants=network.target

[Service]
Type=simple
User=vm-agent
Group=vm-agent
WorkingDirectory=/opt/vm-agent
Environment=PYTHONPATH=/opt/vm-agent
Environment=ORCHESTRATOR_URL=$ORCHESTRATOR_URL
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

# Set environment variable in service
sed -i "s|\$ORCHESTRATOR_URL|$ORCHESTRATOR_URL|g" /etc/systemd/system/vm-agent.service

# Set permissions
echo "🔒 Setting permissions..."
chown -R vm-agent:vm-agent /opt/vm-agent
chown -R vm-agent:vm-agent /opt/vm-agent-venv
chmod 700 /opt/vm-agent/security
chmod 600 /opt/vm-agent/config/agent_config.yaml

# Enable and start service
echo "🚀 Starting service..."
systemctl daemon-reload
systemctl enable vm-agent
systemctl start vm-agent

# Wait a moment for service to start
sleep 3

# Check status
if systemctl is-active --quiet vm-agent; then
    echo "✅ VM Agent installed and running successfully!"
    echo ""
    echo "📋 Useful commands:"
    echo "  sudo systemctl status vm-agent"
    echo "  sudo journalctl -u vm-agent -f"
    echo "  curl http://localhost:8080/health"
else
    echo "⚠️ Service may not have started properly. Check logs:"
    echo "  sudo journalctl -u vm-agent -n 50"
fi

echo ""
echo "🎉 Installation complete!"