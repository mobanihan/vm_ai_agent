#!/usr/bin/env python3
"""
VM Agent Installer

Handles installation and setup of VM agent as a system service.
Supports systemd on Linux systems with robust virtual environment handling.
"""

import os
import sys
import subprocess
import shutil
import click
from pathlib import Path
from typing import Dict, Any, Optional, List
import logging

logger = logging.getLogger(__name__)

# Required packages for VM Agent
REQUIRED_PACKAGES = [
    'aiofiles>=24.1.0',
    'aiohttp>=3.8.0',
    'aiohttp-cors>=0.7.0',
    'PyYAML>=6.0',
    'cryptography>=41.0.0',
    'psutil>=5.9.0',
    'websockets>=11.0',
]

class VMAgentInstaller:
    """Installer for VM Agent system service with robust environment handling"""
    
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
    
    def detect_python_environment(self) -> Dict[str, Any]:
        """Detect current Python environment and provide recommendations"""
        env_info = {
            'current_python': sys.executable,
            'is_venv': hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix),
            'venv_path': None,
            'system_python': '/usr/bin/python3',
            'recommendations': []
        }
        
        # Detect virtual environment path
        if env_info['is_venv']:
            env_info['venv_path'] = sys.executable
            env_info['recommendations'].append("Virtual environment detected - consider system-wide installation for stability")
        
        # Check if system Python has required packages
        system_has_packages = self.check_python_imports(env_info['system_python'])
        venv_has_packages = False
        
        if env_info['is_venv']:
            venv_has_packages = self.check_python_imports(env_info['current_python'])
        
        env_info['system_has_packages'] = system_has_packages
        env_info['venv_has_packages'] = venv_has_packages
        
        # Generate recommendations
        if not system_has_packages and not venv_has_packages:
            env_info['recommendations'].append("Install dependencies system-wide for reliability")
        elif env_info['is_venv'] and not system_has_packages:
            env_info['recommendations'].append("Virtual environment has packages but system doesn't - consider --install-system-wide")
        
        return env_info
    
    def check_python_imports(self, python_path: str) -> bool:
        """Check if Python can import required modules"""
        test_cmd = f"{python_path} -c 'import aiofiles, aiohttp, vm_agent' 2>/dev/null"
        try:
            result = subprocess.run(test_cmd, shell=True, capture_output=True)
            return result.returncode == 0
        except:
            return False
    
    def install_dependencies_system_wide(self) -> bool:
        """Install required dependencies system-wide"""
        click.echo("🔧 Installing dependencies system-wide...")
        
        try:
            packages = ' '.join(REQUIRED_PACKAGES)
            cmd = f"pip3 install {packages}"
            
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            if result.returncode == 0:
                click.echo("✅ Dependencies installed system-wide successfully")
                return True
            else:
                click.echo(f"❌ Failed to install dependencies: {result.stderr}")
                return False
        except Exception as e:
            click.echo(f"❌ Failed to install dependencies: {e}")
            return False
    
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
    
    def create_robust_wrapper_script(self, env_info: Dict[str, Any]) -> bool:
        """Create an intelligent wrapper script that handles environment detection and fixes"""
        try:
            wrapper_content = f"""#!/bin/bash
# VM Agent Robust Wrapper Script - Auto-generated
# Handles virtual environment detection, dependency validation, and automatic fixes

# Set working directory
cd {self.install_dir}

# Auto-detect Python environment with fallbacks
DETECTED_PYTHON="{env_info['current_python']}"
SYSTEM_PYTHON="/usr/bin/python3"

echo "🔍 VM Agent Environment Detection"

# Function to test Python imports
test_python_imports() {{
    local python_path="$1"
    if [ ! -f "$python_path" ]; then
        return 1
    fi
    
    if "$python_path" -c "import aiofiles, aiohttp, vm_agent" 2>/dev/null; then
        return 0
    else
        return 1
    fi
}}

# Test the detected Python first
if test_python_imports "$DETECTED_PYTHON"; then
    echo "✅ Using detected Python: $DETECTED_PYTHON"
    PYTHON_TO_USE="$DETECTED_PYTHON"
elif test_python_imports "$SYSTEM_PYTHON"; then
    echo "✅ Using system Python: $SYSTEM_PYTHON"
    PYTHON_TO_USE="$SYSTEM_PYTHON"
else
    echo "❌ Neither detected nor system Python can import required modules"
    echo "🔧 Attempting automatic fix..."
    
    # Try to install dependencies system-wide
    if pip3 install {' '.join(REQUIRED_PACKAGES)} 2>/dev/null; then
        echo "✅ Dependencies installed, retrying..."
        if test_python_imports "$SYSTEM_PYTHON"; then
            echo "✅ System Python now works after dependency installation"
            PYTHON_TO_USE="$SYSTEM_PYTHON"
        else
            echo "❌ System Python still doesn't work"
            exit 1
        fi
    else
        echo "❌ Failed to install dependencies automatically"
        echo "📋 Manual fix required:"
        echo "  sudo pip3 install {' '.join(REQUIRED_PACKAGES)}"
        echo "  sudo systemctl restart vm-agent"
        exit 1
    fi
fi

# Set up environment
export PYTHONPATH="{self.install_dir}:$PYTHONPATH"

# Execute the vm-agent server
echo "🚀 Starting VM Agent with Python: $PYTHON_TO_USE"
exec "$PYTHON_TO_USE" -m vm_agent.server "$@"
"""
            
            wrapper_path = self.install_dir / "vm-agent-wrapper.sh"
            with open(wrapper_path, 'w') as f:
                f.write(wrapper_content)
            
            # Make executable
            wrapper_path.chmod(0o755)
            shutil.chown(wrapper_path, self.user, self.group)
            
            click.echo(f"✓ Created robust wrapper script: {wrapper_path}")
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
    
    def install_service_file(self, env_info: Dict[str, Any], use_wrapper: bool = False, install_system_wide: bool = False) -> bool:
        """Install systemd service file with smart environment handling"""
        try:
            if use_wrapper:
                # Create robust wrapper script
                if not self.create_robust_wrapper_script(env_info):
                    return False
                
                exec_start = f"{self.install_dir}/vm-agent-wrapper.sh"
                click.echo("✓ Using robust wrapper script for service")
                
            elif install_system_wide or not env_info['is_venv']:
                # Use system Python for reliability
                exec_start = f"/usr/bin/python3 -m vm_agent.server"
                click.echo("✓ Using system Python for service")
                
            else:
                # Use current Python (virtual environment)
                exec_start = f"{env_info['current_python']} -m vm_agent.server"
                click.echo(f"⚠️  Using virtual environment Python: {env_info['current_python']}")
                click.echo("   Consider using --install-system-wide for production stability")
            
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
    
    def verify_installation(self) -> bool:
        """Verify the installation is working"""
        import time
        
        click.echo("🔍 Verifying installation...")
        
        # Give service time to start
        time.sleep(3)
        
        try:
            # Check service status
            result = subprocess.run(["systemctl", "is-active", self.service_name], 
                                  capture_output=True, text=True)
            
            if result.stdout.strip() == "active":
                click.echo("✅ Service is running")
            else:
                click.echo("⚠️  Service may not be running properly")
                return False
            
            # Test health endpoint
            try:
                import urllib.request
                response = urllib.request.urlopen("http://localhost:8080/health", timeout=5)
                if response.status == 200:
                    click.echo("✅ Health endpoint is accessible")
                    return True
                else:
                    click.echo("⚠️  Health endpoint returned non-200 status")
                    return False
            except:
                click.echo("⚠️  Health endpoint not accessible (may still be starting)")
                return False
                
        except Exception as e:
            click.echo(f"⚠️  Verification failed: {e}")
            return False
    
    def install(
        self, 
        orchestrator_url: str,
        provisioning_token: Optional[str] = None,
        tenant_id: Optional[str] = None,
        use_wrapper: bool = False,
        install_system_wide: bool = False,
        **kwargs
    ) -> bool:
        """Complete installation process with robust environment handling"""
        
        click.echo("🚀 Installing VM Agent as system service...")
        
        # Check requirements
        if not self.check_requirements():
            return False
        
        # Detect Python environment
        env_info = self.detect_python_environment()
        
        click.echo("\n🔍 Environment Analysis:")
        click.echo(f"  Current Python: {env_info['current_python']}")
        click.echo(f"  Virtual Environment: {'Yes' if env_info['is_venv'] else 'No'}")
        if env_info['is_venv']:
            click.echo(f"  Virtual Environment Path: {env_info['venv_path']}")
        click.echo(f"  System Python has packages: {'Yes' if env_info['system_has_packages'] else 'No'}")
        if env_info['is_venv']:
            click.echo(f"  Virtual Environment has packages: {'Yes' if env_info['venv_has_packages'] else 'No'}")
        
        # Show recommendations
        if env_info['recommendations']:
            click.echo("\n💡 Recommendations:")
            for rec in env_info['recommendations']:
                click.echo(f"  • {rec}")
        
        # Handle dependencies
        if install_system_wide or (env_info['is_venv'] and not env_info['system_has_packages']):
            click.echo("\n🔧 Installing dependencies system-wide for stability...")
            if not self.install_dependencies_system_wide():
                if not use_wrapper:
                    click.echo("❌ Failed to install dependencies. Consider using --use-wrapper flag.")
                    return False
            env_info['system_has_packages'] = True
        
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
        if not self.install_service_file(env_info, use_wrapper=use_wrapper, install_system_wide=install_system_wide):
            return False
        
        # Enable and start service
        if not self.enable_service():
            return False
        
        # Verify installation
        verification_success = self.verify_installation()
        
        click.echo("\n✅ VM Agent installed successfully!")
        click.echo(f"📁 Installation directory: {self.install_dir}")
        click.echo(f"🔧 Service name: {self.service_name}")
        
        if use_wrapper:
            click.echo(f"📜 Wrapper script: {self.install_dir}/vm-agent-wrapper.sh")
        elif install_system_wide or not env_info['is_venv']:
            click.echo("🐍 Using system Python for stability")
        else:
            click.echo("⚠️  Using virtual environment Python - consider --install-system-wide for production")
        
        click.echo("\n📋 Useful commands:")
        click.echo(f"  sudo systemctl status {self.service_name}")
        click.echo(f"  sudo systemctl restart {self.service_name}")
        click.echo(f"  sudo journalctl -u {self.service_name} -f")
        click.echo(f"  curl http://localhost:8080/health")
        
        if not verification_success:
            click.echo("\n⚠️  Installation completed but verification failed.")
            click.echo("Check service status and logs for any issues.")
        
        return True
    
    def fix_existing_installation(self) -> bool:
        """Fix an existing installation with virtual environment issues"""
        click.echo("🔧 Fixing existing VM Agent installation...")
        
        if not self.check_requirements():
            return False
        
        try:
            # Stop service
            subprocess.run(["systemctl", "stop", self.service_name], check=False)
            
            # Install dependencies system-wide
            if not self.install_dependencies_system_wide():
                return False
            
            # Update service to use system Python
            if os.path.exists(self.service_file):
                with open(self.service_file, 'r') as f:
                    content = f.read()
                
                # Update ExecStart line
                lines = content.split('\n')
                for i, line in enumerate(lines):
                    if line.strip().startswith('ExecStart='):
                        lines[i] = "ExecStart=/usr/bin/python3 -m vm_agent.server"
                        break
                
                with open(self.service_file, 'w') as f:
                    f.write('\n'.join(lines))
                
                # Reload systemd
                subprocess.run(["systemctl", "daemon-reload"], check=True)
                click.echo("✓ Updated service to use system Python")
            
            # Restart service
            subprocess.run(["systemctl", "start", self.service_name], check=True)
            
            # Verify fix
            if self.verify_installation():
                click.echo("✅ Fix completed successfully!")
                return True
            else:
                click.echo("⚠️  Fix completed but verification failed. Check logs.")
                return False
                
        except Exception as e:
            click.echo(f"❌ Fix failed: {e}")
            return False
    
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
@click.option('--orchestrator-url', required=False, help='Orchestrator URL')
@click.option('--provisioning-token', help='Provisioning token for auto-setup')
@click.option('--tenant-id', help='Manual tenant ID')
@click.option('--use-wrapper', is_flag=True, help='Use wrapper script for complex environments')
@click.option('--install-system-wide', is_flag=True, help='Install dependencies system-wide (recommended for production)')
@click.option('--fix-existing', is_flag=True, help='Fix existing installation with virtual environment issues')
@click.option('--uninstall', is_flag=True, help='Uninstall the service')
def main(orchestrator_url: str, provisioning_token: str, tenant_id: str, use_wrapper: bool, install_system_wide: bool, fix_existing: bool, uninstall: bool):
    """VM Agent Installer - Install, fix, or uninstall the VM agent service"""
    
    # Configure logging
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    
    installer = VMAgentInstaller()
    
    if uninstall:
        success = installer.uninstall()
    elif fix_existing:
        success = installer.fix_existing_installation()
    elif orchestrator_url:
        success = installer.install(
            orchestrator_url=orchestrator_url,
            provisioning_token=provisioning_token,
            tenant_id=tenant_id,
            use_wrapper=use_wrapper,
            install_system_wide=install_system_wide
        )
    else:
        click.echo("❌ --orchestrator-url is required for installation")
        click.echo("   Use --fix-existing to fix an existing installation")
        click.echo("   Use --uninstall to remove the service")
        success = False
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main() 