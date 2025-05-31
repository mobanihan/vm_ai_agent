#!/usr/bin/env python3
"""
VM Agent Environment Diagnostic Tool

This script helps diagnose Python environment issues that might prevent
the VM agent from running correctly.
"""

import os
import sys
import subprocess
from pathlib import Path
import importlib.util

def print_header(title):
    """Print a formatted header"""
    print(f"\n{'='*60}")
    print(f"🔍 {title}")
    print('='*60)

def check_python_installation():
    """Check Python installation details"""
    print_header("Python Installation")
    
    print(f"Python executable: {sys.executable}")
    print(f"Python version: {sys.version}")
    print(f"Python path: {sys.path}")
    
    # Check if in virtual environment
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print(f"✅ Virtual environment detected")
        print(f"  - Base prefix: {sys.base_prefix}")
        print(f"  - Current prefix: {sys.prefix}")
        if hasattr(sys, 'real_prefix'):
            print(f"  - Real prefix: {sys.real_prefix}")
    else:
        print("ℹ️  Using system Python (no virtual environment)")

def check_required_modules():
    """Check if required modules can be imported"""
    print_header("Required Modules")
    
    required_modules = [
        'aiofiles', 'aiohttp', 'aiohttp_cors', 'yaml', 'cryptography',
        'psutil', 'websockets', 'pyjwt', 'paramiko', 'click'
    ]
    
    for module in required_modules:
        try:
            spec = importlib.util.find_spec(module)
            if spec is None:
                print(f"❌ {module} - Not found")
            else:
                # Try to actually import it
                imported = importlib.import_module(module)
                version = getattr(imported, '__version__', 'unknown')
                location = getattr(spec, 'origin', 'unknown')
                print(f"✅ {module} ({version}) - {location}")
        except Exception as e:
            print(f"❌ {module} - Import error: {e}")

def check_vm_agent():
    """Check if vm_agent can be imported"""
    print_header("VM Agent Module")
    
    try:
        # Check if vm_agent can be found
        spec = importlib.util.find_spec('vm_agent')
        if spec is None:
            print("❌ vm_agent module not found")
            return False
        
        print(f"✅ vm_agent module found at: {spec.origin}")
        
        # Try to import it
        import vm_agent
        print(f"✅ vm_agent imported successfully")
        
        # Try to import submodules
        submodules = ['server', 'tools.security_manager', 'tools.file_manager']
        for submodule in submodules:
            try:
                importlib.import_module(f'vm_agent.{submodule}')
                print(f"✅ vm_agent.{submodule} imported successfully")
            except Exception as e:
                print(f"❌ vm_agent.{submodule} import error: {e}")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ vm_agent import error: {e}")
        return False

def check_installation_paths():
    """Check common installation paths"""
    print_header("Installation Paths")
    
    paths_to_check = [
        "/opt/vm-agent",
        "/opt/vm-agent/vm-agent-wrapper.sh",
        "/etc/systemd/system/vm-agent.service",
        "/var/log/vm-agent",
        "/root/vm_ai_agent/venv/bin/python3"
    ]
    
    for path in paths_to_check:
        path_obj = Path(path)
        if path_obj.exists():
            if path_obj.is_file():
                print(f"✅ {path} (file)")
                if path.endswith('.sh'):
                    try:
                        with open(path, 'r') as f:
                            first_lines = f.read(500)
                            print(f"   Preview: {first_lines[:100]}...")
                    except:
                        pass
            else:
                print(f"✅ {path} (directory)")
        else:
            print(f"❌ {path} (not found)")

def check_systemd_service():
    """Check systemd service status"""
    print_header("Systemd Service")
    
    try:
        # Check service status
        result = subprocess.run(
            ["systemctl", "status", "vm-agent", "--no-pager"],
            capture_output=True, text=True
        )
        
        print("Service status:")
        print(result.stdout)
        
        if result.stderr:
            print("Service errors:")
            print(result.stderr)
            
    except Exception as e:
        print(f"❌ Failed to check systemd service: {e}")

def suggest_fixes(vm_agent_works):
    """Suggest potential fixes"""
    print_header("Suggested Fixes")
    
    if not vm_agent_works:
        print("🔧 VM Agent import issues detected:")
        print("   1. Reinstall vm-agent: pip install -e .")
        print("   2. Check PYTHONPATH includes installation directory")
        print("   3. Ensure all dependencies are installed")
        print()
    
    print("🔧 For systemd service issues:")
    print("   1. Update Python path in service file:")
    print(f"      ExecStart={sys.executable} -m vm_agent.server")
    print()
    print("   2. Or reinstall with wrapper script:")
    print("      sudo python3 -m vm_agent.installer --orchestrator-url <URL> --use-wrapper")
    print()
    print("   3. Install dependencies system-wide:")
    print("      sudo pip3 install aiofiles aiohttp aiohttp-cors pyyaml cryptography")
    print()
    print("   4. Check service logs:")
    print("      sudo journalctl -u vm-agent -f")

def main():
    """Main diagnostic function"""
    print("🧪 VM Agent Environment Diagnostic Tool")
    print("This tool will check your Python environment and VM agent installation")
    
    check_python_installation()
    check_required_modules()
    vm_agent_works = check_vm_agent()
    check_installation_paths()
    check_systemd_service()
    suggest_fixes(vm_agent_works)
    
    print(f"\n{'='*60}")
    print("🏁 Diagnostic complete!")
    print("If you're still having issues, share this output for further assistance.")
    print('='*60)

if __name__ == "__main__":
    main() 