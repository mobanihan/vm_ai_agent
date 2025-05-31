#!/usr/bin/env python3
"""
VM Agent Installer

Handles installation and setup of VM agent as a system service.
Supports systemd on Linux systems.
"""

import os
import sys
import subprocess
import shutil
import click
from pathlib import Path
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class VMAgentInstaller:
    """Installer for VM Agent system service"""
    
    def __init__(self):
        self.install_dir = Path("/opt/vm-agent")
        self.service_name = "vm-agent"
        self.service_file = f"/etc/systemd/system/{self.service_name}.service"
        self.user = "vm-agent"
        self.group = "vm-agent"
        
    def check_requirements(self) -> bool:
        """Check system requirements"""
        # Check if running as root
        if os.geteuid() != 0:
            click.echo("❌ Installation requires root privileges. Please run with sudo.")
            return False
        
        # Check if systemd is available
        if not shutil.which("systemctl"):
            click.echo("❌ systemd is required but not found.")
            return False
        
        # Check Python version
        if sys.version_info < (3, 8):
            click.echo("❌ Python 3.8 or higher is required.")
            return False
        
        return True
    
    def create_user(self) -> bool:
        """Create vm-agent user and group"""
        try:
            # Check if user already exists
            result = subprocess.run(["id", self.user], capture_output=True)
            if result.returncode == 0:
                click.echo(f"✓ User {self.user} already exists")
                return True
            
            # Create group
            subprocess.run(["groupadd", "--system", self.group], check=True)
            
            # Create user
            subprocess.run([
                "useradd", "--system", "--gid", self.group,
                "--home-dir", str(self.install_dir),
                "--no-create-home", "--shell", "/bin/false",
                self.user
            ], check=True)
            
            click.echo(f"✓ Created user {self.user}")
            return True
            
        except subprocess.CalledProcessError as e:
            click.echo(f"❌ Failed to create user: {e}")
            return False
    
    def create_directories(self) -> bool:
        """Create necessary directories"""
        try:
            directories = [
                self.install_dir,
                self.install_dir / "security",
                self.install_dir / "tenant",
                self.install_dir / "logs",
                Path("/var/log/vm-agent"),
            ]
            
            for directory in directories:
                directory.mkdir(parents=True, exist_ok=True)
                shutil.chown(directory, self.user, self.group)
                directory.chmod(0o755)
            
            # Secure directories
            (self.install_dir / "security").chmod(0o700)
            (self.install_dir / "tenant").chmod(0o700)
            
            click.echo("✓ Created directories")
            return True
            
        except Exception as e:
            click.echo(f"❌ Failed to create directories: {e}")
            return False
    
    def create_wrapper_script(self) -> bool:
        """Create an intelligent wrapper script that handles environment detection"""
        try:
            # Auto-detect the correct Python interpreter
            python_executable = sys.executable
            
            wrapper_content = f"""#!/bin/bash
# VM Agent Wrapper Script - Auto-generated
# Handles virtual environment detection and proper Python path setup

# Set working directory
cd {self.install_dir}

# Auto-detect Python environment
DETECTED_PYTHON="{python_executable}"

# If the detected Python doesn't exist (e.g., venv was moved), try fallbacks
if [ ! -f "$DETECTED_PYTHON" ]; then
    echo "⚠️  Original Python not found: $DETECTED_PYTHON"
    
    # Try common virtual environment locations
    for venv_path in "/root/vm_ai_agent/venv/bin/python3" "/opt/vm-agent/venv/bin/python3" "/usr/local/bin/python3" "/usr/bin/python3"; do
        if [ -f "$venv_path" ]; then
            echo "✓ Using fallback Python: $venv_path"
            DETECTED_PYTHON="$venv_path"
            break
        fi
    done
fi

# Test if Python can import required modules
if ! "$DETECTED_PYTHON" -c "import aiofiles, aiohttp, vm_agent" 2>/dev/null; then
    echo "❌ Python at $DETECTED_PYTHON cannot import required modules"
    echo "📋 Available Python installations:"
    find /usr/bin /usr/local/bin /root -name "python3*" 2>/dev/null | head -10
    exit 1
fi

# Set up environment
export PYTHONPATH="{self.install_dir}:$PYTHONPATH"

# Execute the vm-agent server
exec "$DETECTED_PYTHON" -m vm_agent.server "$@"
"""
            
            wrapper_path = self.install_dir / "vm-agent-wrapper.sh"
            with open(wrapper_path, 'w') as f:
                f.write(wrapper_content)
            
            # Make executable
            wrapper_path.chmod(0o755)
            shutil.chown(wrapper_path, self.user, self.group)
            
            click.echo(f"✓ Created wrapper script: {wrapper_path}")
            return True
            
        except Exception as e:
            click.echo(f"❌ Failed to create wrapper script: {e}")
            return False

    def create_config_file(self, orchestrator_url: str, **kwargs) -> bool:
        """Create configuration file"""
        try:
            config_content = f"""# VM Agent Configuration
agent:
  id: vm-agent-{os.uname().nodename}
  name: "VM Agent"
  version: "1.0.0"

server:
  host: "0.0.0.0"
  port: 8080
  ssl:
    enabled: true
    cert_file: "{self.install_dir}/security/server.crt"
    key_file: "{self.install_dir}/security/server.key"

orchestrator:
  url: "{orchestrator_url}"
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
"""
            
            config_file = self.install_dir / "config" / "agent_config.yaml"
            config_file.parent.mkdir(exist_ok=True)
            
            with open(config_file, 'w') as f:
                f.write(config_content)
            
            shutil.chown(config_file, self.user, self.group)
            config_file.chmod(0o644)
            
            click.echo("✓ Created configuration file")
            return True
            
        except Exception as e:
            click.echo(f"❌ Failed to create config: {e}")
            return False
    
    def install_service_file(self, use_wrapper: bool = False) -> bool:
        """Install systemd service file"""
        try:
            if use_wrapper:
                # Create wrapper script first
                if not self.create_wrapper_script():
                    return False
                
                exec_start = f"{self.install_dir}/vm-agent-wrapper.sh"
                click.echo("✓ Using wrapper script for service")
            else:
                # Auto-detect the correct Python interpreter
                python_executable = sys.executable
                
                # If we're in a virtual environment, use that Python
                if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
                    click.echo(f"✓ Detected virtual environment, using: {python_executable}")
                else:
                    click.echo(f"✓ Using system Python: {python_executable}")
                
                exec_start = f"{python_executable} -m vm_agent.server"
            
            service_content = f"""[Unit]
Description=VM Agent for AI Infrastructure Management
After=network.target
Wants=network.target

[Service]
Type=simple
User={self.user}
Group={self.group}
WorkingDirectory={self.install_dir}
Environment=PYTHONPATH={self.install_dir}
ExecStart={exec_start}
ExecReload=/bin/kill -HUP $MAINPID
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
ReadWritePaths={self.install_dir} /var/log/vm-agent

[Install]
WantedBy=multi-user.target
"""
            
            with open(self.service_file, 'w') as f:
                f.write(service_content)
            
            os.chmod(self.service_file, 0o644)
            
            # Reload systemd
            subprocess.run(["systemctl", "daemon-reload"], check=True)
            
            click.echo("✓ Installed systemd service")
            return True
            
        except Exception as e:
            click.echo(f"❌ Failed to install service: {e}")
            return False
    
    def enable_service(self) -> bool:
        """Enable and start the service"""
        try:
            # Enable service
            subprocess.run(["systemctl", "enable", self.service_name], check=True)
            click.echo("✓ Enabled vm-agent service")
            
            # Start service
            subprocess.run(["systemctl", "start", self.service_name], check=True)
            click.echo("✓ Started vm-agent service")
            
            return True
            
        except subprocess.CalledProcessError as e:
            click.echo(f"❌ Failed to enable/start service: {e}")
            return False
    
    def install(
        self, 
        orchestrator_url: str,
        provisioning_token: Optional[str] = None,
        tenant_id: Optional[str] = None,
        use_wrapper: bool = False,
        **kwargs
    ) -> bool:
        """Complete installation process"""
        
        click.echo("🚀 Installing VM Agent as system service...")
        
        # Check requirements
        if not self.check_requirements():
            return False
        
        # Create user
        if not self.create_user():
            return False
        
        # Create directories
        if not self.create_directories():
            return False
        
        # Create config
        if not self.create_config_file(orchestrator_url, **kwargs):
            return False
        
        # Install service
        if not self.install_service_file(use_wrapper=use_wrapper):
            return False
        
        # Enable and start service
        if not self.enable_service():
            return False
        
        click.echo("\n✅ VM Agent installed successfully!")
        click.echo(f"📁 Installation directory: {self.install_dir}")
        click.echo(f"🔧 Service name: {self.service_name}")
        if use_wrapper:
            click.echo(f"📜 Wrapper script: {self.install_dir}/vm-agent-wrapper.sh")
        click.echo("\n📋 Useful commands:")
        click.echo(f"  sudo systemctl status {self.service_name}")
        click.echo(f"  sudo systemctl restart {self.service_name}")
        click.echo(f"  sudo journalctl -u {self.service_name} -f")
        
        return True
    
    def uninstall(self) -> bool:
        """Uninstall the VM agent service"""
        
        if not self.check_requirements():
            return False
        
        click.echo("🗑️ Uninstalling VM Agent...")
        
        try:
            # Stop and disable service
            subprocess.run(["systemctl", "stop", self.service_name], check=False)
            subprocess.run(["systemctl", "disable", self.service_name], check=False)
            
            # Remove service file
            if os.path.exists(self.service_file):
                os.remove(self.service_file)
                subprocess.run(["systemctl", "daemon-reload"], check=True)
            
            # Remove installation directory
            if self.install_dir.exists():
                shutil.rmtree(self.install_dir)
            
            # Remove user (optional)
            subprocess.run(["userdel", self.user], check=False)
            subprocess.run(["groupdel", self.group], check=False)
            
            click.echo("✅ VM Agent uninstalled successfully!")
            return True
            
        except Exception as e:
            click.echo(f"❌ Uninstall failed: {e}")
            return False


@click.command()
@click.option('--orchestrator-url', required=True, help='Orchestrator URL')
@click.option('--provisioning-token', help='Provisioning token for auto-setup')
@click.option('--tenant-id', help='Manual tenant ID')
@click.option('--use-wrapper', is_flag=True, help='Use wrapper script for complex environments')
@click.option('--uninstall', is_flag=True, help='Uninstall the service')
def main(orchestrator_url: str, provisioning_token: str, tenant_id: str, use_wrapper: bool, uninstall: bool):
    """VM Agent Installer - Install or uninstall the VM agent service"""
    
    # Configure logging
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    
    installer = VMAgentInstaller()
    
    if uninstall:
        success = installer.uninstall()
    else:
        success = installer.install(
            orchestrator_url=orchestrator_url,
            provisioning_token=provisioning_token,
            tenant_id=tenant_id,
            use_wrapper=use_wrapper
        )
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main() 