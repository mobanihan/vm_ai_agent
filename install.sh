#!/bin/bash

# netifaces is required for network interface handling
sudo apt install -y build-essential python3-dev

sudo apt install python3.12-venv

# VM Agent Installation Script
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="/opt/vm-agent"
SERVICE_NAME="vm-agent"
LOG_DIR="/var/log"

echo "Installing VM Agent..."

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as root (use sudo)" 
   exit 1
fi

# Create installation directory
echo "Creating installation directory..."
mkdir -p $INSTALL_DIR
cp -r $SCRIPT_DIR/* $INSTALL_DIR/
chown -R root:root $INSTALL_DIR

# Create virtual environment
echo "Setting up Python virtual environment..."
cd $INSTALL_DIR
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Create log directory
mkdir -p $LOG_DIR
touch $LOG_DIR/vm-agent.log
chmod 644 $LOG_DIR/vm-agent.log

# Create systemd service
echo "Creating systemd service..."
cat > /etc/systemd/system/${SERVICE_NAME}.service << EOF
[Unit]
Description=VM Agent MCP Server
After=network.target
Wants=network.target

[Service]
Type=simple
User=root
Group=root
WorkingDirectory=$INSTALL_DIR
Environment=PATH=$INSTALL_DIR/venv/bin
Environment=VM_ID=\${VM_ID}
Environment=API_KEY=\${API_KEY}
Environment=AGENT_CONFIG=$INSTALL_DIR/config/agent_config.yaml
ExecStart=$INSTALL_DIR/venv/bin/python server.py
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
SyslogIdentifier=vm-agent

[Install]
WantedBy=multi-user.target
EOF

# Set VM_ID if not provided
if [ -z "$VM_ID" ]; then
    VM_ID=$(hostname)
    echo "VM_ID not set, using hostname: $VM_ID"
fi

# Create environment file
cat > /etc/default/vm-agent << EOF
VM_ID=$VM_ID
API_KEY=${API_KEY:-"default-key-change-me"}
EOF

# Update systemd service to use environment file
sed -i '/\[Service\]/a EnvironmentFile=/etc/default/vm-agent' /etc/systemd/system/${SERVICE_NAME}.service

# Reload systemd and enable service
systemctl daemon-reload
systemctl enable $SERVICE_NAME

echo "Installation completed!"
echo ""
echo "To start the service:"
echo "  sudo systemctl start $SERVICE_NAME"
echo ""
echo "To check status:"
echo "  sudo systemctl status $SERVICE_NAME"
echo ""
echo "To view logs:"
echo "  sudo journalctl -u $SERVICE_NAME -f"
echo ""
echo "Configuration file: $INSTALL_DIR/config/agent_config.yaml"
echo "Environment file: /etc/default/vm-agent"
echo ""
echo "Make sure to:"
echo "1. Set unique VM_ID in /etc/default/vm-agent"
echo "2. Configure API_KEY for security"
echo "3. Review and adjust agent_config.yaml as needed"