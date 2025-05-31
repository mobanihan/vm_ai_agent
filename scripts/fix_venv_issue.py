#!/usr/bin/env python3
"""
VM Agent Virtual Environment Issue Fixer

This script fixes the common issue where the systemd service fails because:
1. The original virtual environment is missing/moved
2. System Python lacks the required dependencies

Usage:
    python3 scripts/fix_venv_issue.py [--system-wide]
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path
import argparse
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

REQUIRED_PACKAGES = [
    'aiofiles>=24.1.0',
    'aiohttp>=3.8.0',
    'aiohttp-cors>=0.7.0',
    'PyYAML>=6.0',
    'cryptography>=41.0.0',
    'psutil>=5.9.0',
    'websockets>=11.0',
]

VENV_PATH = Path("/root/vm_ai_agent/venv")
SERVICE_FILE = Path("/etc/systemd/system/vm-agent.service")

def run_command(cmd, check=True):
    """Run a command and return the result"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=check)
        return result.stdout.strip(), result.stderr.strip(), result.returncode
    except subprocess.CalledProcessError as e:
        return e.stdout.strip(), e.stderr.strip(), e.returncode

def check_python_imports(python_path):
    """Check if Python can import required modules"""
    test_cmd = f"{python_path} -c 'import aiofiles, aiohttp, vm_agent; print(\"SUCCESS\")'"
    stdout, stderr, returncode = run_command(test_cmd, check=False)
    return returncode == 0

def install_system_wide():
    """Install dependencies system-wide"""
    logger.info("🔧 Installing dependencies system-wide...")
    
    packages = ' '.join(REQUIRED_PACKAGES)
    cmd = f"pip3 install {packages}"
    
    logger.info(f"Running: {cmd}")
    stdout, stderr, returncode = run_command(cmd)
    
    if returncode == 0:
        logger.info("✅ Successfully installed dependencies system-wide")
        return True
    else:
        logger.error(f"❌ Failed to install dependencies: {stderr}")
        return False

def recreate_virtual_environment():
    """Recreate the virtual environment"""
    logger.info("🔧 Recreating virtual environment...")
    
    # Remove existing venv if it exists but is broken
    if VENV_PATH.exists():
        logger.info(f"Removing existing broken venv at {VENV_PATH}")
        shutil.rmtree(VENV_PATH)
    
    # Create parent directory
    VENV_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    # Create new virtual environment
    cmd = f"python3 -m venv {VENV_PATH}"
    logger.info(f"Running: {cmd}")
    stdout, stderr, returncode = run_command(cmd)
    
    if returncode != 0:
        logger.error(f"❌ Failed to create virtual environment: {stderr}")
        return False
    
    # Install dependencies in venv
    pip_path = VENV_PATH / "bin" / "pip"
    packages = ' '.join(REQUIRED_PACKAGES)
    cmd = f"{pip_path} install {packages}"
    
    logger.info(f"Installing packages in venv: {cmd}")
    stdout, stderr, returncode = run_command(cmd)
    
    if returncode == 0:
        logger.info("✅ Successfully recreated virtual environment")
        return True
    else:
        logger.error(f"❌ Failed to install packages in venv: {stderr}")
        return False

def update_systemd_service(python_path):
    """Update systemd service to use the correct Python path"""
    if not SERVICE_FILE.exists():
        logger.error(f"❌ Service file not found: {SERVICE_FILE}")
        return False
    
    # Read current service file
    with open(SERVICE_FILE, 'r') as f:
        content = f.read()
    
    # Update ExecStart line
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if line.strip().startswith('ExecStart='):
            lines[i] = f"ExecStart={python_path} -m vm_agent.server"
            break
    
    # Write updated service file
    new_content = '\n'.join(lines)
    with open(SERVICE_FILE, 'w') as f:
        f.write(new_content)
    
    # Reload systemd
    run_command("systemctl daemon-reload")
    logger.info(f"✅ Updated systemd service to use: {python_path}")
    return True

def main():
    parser = argparse.ArgumentParser(description="Fix VM Agent virtual environment issues")
    parser.add_argument('--system-wide', action='store_true', 
                       help='Install dependencies system-wide instead of recreating venv')
    args = parser.parse_args()
    
    logger.info("🔍 VM Agent Virtual Environment Issue Fixer")
    logger.info("=" * 50)
    
    # Check current status
    logger.info("📋 Current Status:")
    logger.info(f"Virtual environment path: {VENV_PATH}")
    logger.info(f"Virtual environment exists: {VENV_PATH.exists()}")
    
    venv_python = VENV_PATH / "bin" / "python3"
    system_python = "/usr/bin/python3"
    
    logger.info(f"Virtual environment Python works: {check_python_imports(str(venv_python))}")
    logger.info(f"System Python works: {check_python_imports(system_python)}")
    
    # Determine fix strategy
    if args.system_wide:
        logger.info("\n🎯 Strategy: Install dependencies system-wide")
        success = install_system_wide()
        if success and check_python_imports(system_python):
            success = update_systemd_service(system_python)
    else:
        logger.info("\n🎯 Strategy: Recreate virtual environment")
        success = recreate_virtual_environment()
        if success and check_python_imports(str(venv_python)):
            success = update_systemd_service(str(venv_python))
    
    if success:
        logger.info("\n✅ Fix completed successfully!")
        logger.info("🔄 Restarting vm-agent service...")
        run_command("systemctl restart vm-agent")
        
        # Check final status
        logger.info("📊 Final Status Check:")
        stdout, stderr, returncode = run_command("systemctl is-active vm-agent", check=False)
        if returncode == 0 and stdout == "active":
            logger.info("✅ VM Agent service is now running!")
        else:
            logger.warning("⚠️  Service may still have issues. Check with: systemctl status vm-agent")
    else:
        logger.error("\n❌ Fix failed. Please check the errors above.")
        return 1
    
    return 0

if __name__ == "__main__":
    if os.geteuid() != 0:
        print("❌ This script must be run as root (use sudo)")
        sys.exit(1)
    
    sys.exit(main()) 