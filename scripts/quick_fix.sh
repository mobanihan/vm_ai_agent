#!/bin/bash
# Quick Fix for VM Agent Virtual Environment Issues
# This script provides two solutions for the common virtual environment problem

echo "🔍 VM Agent Virtual Environment Quick Fix"
echo "=========================================="

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "❌ Please run as root: sudo bash scripts/quick_fix.sh"
    exit 1
fi

echo ""
echo "The issue: Virtual environment /root/vm_ai_agent/venv is missing/broken"
echo "System Python cannot import required modules (aiofiles, aiohttp, etc.)"
echo ""
echo "Choose a solution:"
echo "1) Install dependencies system-wide (RECOMMENDED - fast and reliable)"
echo "2) Recreate virtual environment (keeps dependencies isolated)"
echo "3) Exit"
echo ""

read -p "Enter choice [1-3]: " choice

case $choice in
    1)
        echo "🔧 Installing dependencies system-wide..."
        pip3 install aiofiles>=24.1.0 aiohttp>=3.8.0 aiohttp-cors>=0.7.0 PyYAML>=6.0 cryptography>=41.0.0 psutil>=5.9.0 websockets>=11.0
        
        if [ $? -eq 0 ]; then
            echo "✅ Dependencies installed successfully"
            
            # Update systemd service to use system Python
            echo "🔧 Updating systemd service..."
            sed -i 's|ExecStart=.*|ExecStart=/usr/bin/python3 -m vm_agent.server|' /etc/systemd/system/vm-agent.service
            systemctl daemon-reload
            
            echo "🔄 Restarting vm-agent service..."
            systemctl restart vm-agent
            
            sleep 3
            if systemctl is-active --quiet vm-agent; then
                echo "✅ VM Agent is now running successfully!"
                systemctl status vm-agent --no-pager -l
            else
                echo "⚠️  Service may still have issues. Check logs:"
                echo "sudo journalctl -u vm-agent -f"
            fi
        else
            echo "❌ Failed to install dependencies"
            exit 1
        fi
        ;;
        
    2)
        echo "🔧 Recreating virtual environment..."
        
        # Remove old venv if exists
        if [ -d "/root/vm_ai_agent/venv" ]; then
            echo "Removing old virtual environment..."
            rm -rf /root/vm_ai_agent/venv
        fi
        
        # Create new venv
        mkdir -p /root/vm_ai_agent
        python3 -m venv /root/vm_ai_agent/venv
        
        if [ $? -eq 0 ]; then
            echo "✅ Virtual environment created"
            
            # Install dependencies
            echo "Installing dependencies in virtual environment..."
            /root/vm_ai_agent/venv/bin/pip install aiofiles>=24.1.0 aiohttp>=3.8.0 aiohttp-cors>=0.7.0 PyYAML>=6.0 cryptography>=41.0.0 psutil>=5.9.0 websockets>=11.0
            
            if [ $? -eq 0 ]; then
                echo "✅ Dependencies installed in virtual environment"
                
                # Update systemd service to use venv Python
                echo "🔧 Updating systemd service..."
                sed -i 's|ExecStart=.*|ExecStart=/root/vm_ai_agent/venv/bin/python3 -m vm_agent.server|' /etc/systemd/system/vm-agent.service
                systemctl daemon-reload
                
                echo "🔄 Restarting vm-agent service..."
                systemctl restart vm-agent
                
                sleep 3
                if systemctl is-active --quiet vm-agent; then
                    echo "✅ VM Agent is now running successfully!"
                    systemctl status vm-agent --no-pager -l
                else
                    echo "⚠️  Service may still have issues. Check logs:"
                    echo "sudo journalctl -u vm-agent -f"
                fi
            else
                echo "❌ Failed to install dependencies in virtual environment"
                exit 1
            fi
        else
            echo "❌ Failed to create virtual environment"
            exit 1
        fi
        ;;
        
    3)
        echo "Exiting..."
        exit 0
        ;;
        
    *)
        echo "❌ Invalid choice"
        exit 1
        ;;
esac

echo ""
echo "🎯 Quick Status Check:"
echo "Service status: $(systemctl is-active vm-agent)"
echo "Health check: $(curl -s http://localhost:8080/health 2>/dev/null | head -c 50 || echo 'Not accessible')"
echo ""
echo "If still having issues, check logs with:"
echo "sudo journalctl -u vm-agent -f" 