# AI Infra VM Agent

[![PyPI version](https://badge.fury.io/py/ai-infra-vm-agent.svg)](https://badge.fury.io/py/ai-infra-vm-agent)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A production-ready VM agent for AI infrastructure management with MCP (Model Context Protocol) support, providing secure, multi-tenant VM management capabilities.

## Features

### 🔧 **Core Capabilities**
- **Shell Command Execution**: Secure command execution with timeout and logging
- **File System Operations**: Read, write, and manage files with proper permissions
- **System Monitoring**: Real-time metrics collection (CPU, memory, disk, network)
- **Log Analysis**: Intelligent log parsing and pattern recognition
- **WebSocket Communication**: Real-time bidirectional communication
- **MCP Protocol Support**: Standard protocol for AI tool integration

### 🔒 **Security & Multi-tenancy**
- **Certificate-based Authentication**: mTLS support for secure connections
- **API Key Management**: Secure API key generation and validation
- **Multi-tenant Isolation**: Organization-based resource isolation
- **Encrypted Communication**: End-to-end encryption for all communications
- **Audit Logging**: Comprehensive logging for compliance and debugging

### 🚀 **Production Ready**
- **High Performance**: Async/await architecture for optimal performance
- **Scalable**: Designed for multi-VM, multi-tenant environments
- **Reliable**: Comprehensive error handling and recovery mechanisms
- **Configurable**: Flexible configuration system with environment variable support
- **Monitorable**: Built-in health checks and metrics endpoints

### 🆕 **New Features**
- **🔍 Smart Environment Detection**: Automatically detects Python environments and virtual environments
- **🛡️ Intelligent Wrapper Scripts**: Handles environment changes and provides fallback mechanisms
- **🧪 Diagnostic Tools**: Comprehensive environment troubleshooting and validation
- **🔧 Flexible Installation**: Multiple installation modes for different deployment scenarios
- **⚡ Improved Error Handling**: Better error messages and recovery mechanisms

## Quick Start

### Prerequisites

- **Python 3.8+** (Python 3.11+ recommended)
- **Linux system** with systemd support
- **Root/sudo access** for system service installation

### Installation Options

#### Option 1: Simple Installation (Recommended)

```bash
# Install the package
pip install ai-infra-vm-agent

# Install as system service (auto-detects your Python environment)
sudo python3 -m vm_agent.installer --orchestrator-url https://your-orchestrator.com
```

#### Option 2: Development Installation

```bash
# Clone the repository
git clone https://github.com/ai-infra/vm-agent.git
cd vm-agent

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install in development mode
pip install -e .

# Install as system service (will use your virtual environment)
sudo python3 -m vm_agent.installer --orchestrator-url https://your-orchestrator.com
```

#### Option 3: Complex Environments (with Wrapper Script)

For environments with complex Python setups or where the Python environment might change:

```bash
# Install with intelligent wrapper script
sudo python3 -m vm_agent.installer \
    --orchestrator-url https://your-orchestrator.com \
    --use-wrapper
```

#### Option 4: With Provisioning Token

```bash
# Automated setup with provisioning token
sudo python3 -m vm_agent.installer \
    --orchestrator-url https://your-orchestrator.com \
    --provisioning-token "your-token-here"
```

### Verification

After installation, verify everything is working:

```bash
# Check service status
sudo systemctl status vm-agent

# Check health endpoint
curl http://localhost:8080/health

# Run diagnostic tool
python3 scripts/diagnose_environment.py
```

## Installation Troubleshooting

### 🧪 Diagnostic Tool

If you encounter any issues, run our comprehensive diagnostic tool:

```bash
python3 scripts/diagnose_environment.py
```

This will check:
- ✅ Python installation and virtual environment detection
- ✅ All required dependencies
- ✅ VM agent module imports
- ✅ Installation paths and systemd service
- ✅ Provides specific fix suggestions

### Common Installation Issues

#### Issue: "ModuleNotFoundError: No module named 'aiofiles'"

**Cause**: Python environment mismatch between installation and runtime.

**Solutions**:
```bash
# Option 1: Reinstall with auto-detection
sudo python3 -m vm_agent.installer --uninstall
sudo python3 -m vm_agent.installer --orchestrator-url YOUR_URL

# Option 2: Use wrapper script
sudo python3 -m vm_agent.installer --orchestrator-url YOUR_URL --use-wrapper

# Option 3: Install dependencies system-wide
sudo pip3 install aiofiles aiohttp aiohttp-cors pyyaml cryptography psutil
```

#### Issue: Service fails to start

**Diagnosis**:
```bash
# Check service logs
sudo journalctl -u vm-agent -f

# Run diagnostic
python3 scripts/diagnose_environment.py

# Test Python environment
python3 -c "import vm_agent; print('✅ VM Agent works')"
```

#### Issue: SSL/Certificate errors

**Solutions**:
```bash
# Reinstall with fresh certificates
sudo python3 -m vm_agent.installer --orchestrator-url YOUR_URL --uninstall
sudo python3 -m vm_agent.installer --orchestrator-url YOUR_URL

# Check certificate permissions
sudo ls -la /opt/vm-agent/security/
```

### Installation Command Reference

```bash
# Basic installation
sudo python3 -m vm_agent.installer --orchestrator-url URL

# With provisioning token
sudo python3 -m vm_agent.installer --orchestrator-url URL --provisioning-token TOKEN

# With wrapper script (for complex environments)
sudo python3 -m vm_agent.installer --orchestrator-url URL --use-wrapper

# With tenant ID
sudo python3 -m vm_agent.installer --orchestrator-url URL --tenant-id TENANT

# Uninstall
sudo python3 -m vm_agent.installer --uninstall

# Get help
python3 -m vm_agent.installer --help
```

## Basic Usage

#### Starting the Agent Server

```bash
# Start with default configuration
vm-agent server

# Start with custom configuration
vm-agent server --host 0.0.0.0 --port 8080 --ssl

# Start with custom config file
vm-agent --config /path/to/config.yaml server
```

#### Using the Client

```python
import asyncio
from vm_agent import connect_to_agent

async def main():
    # Connect to agent
    async with connect_to_agent(
        "https://vm-agent:8080",
        api_key="your-api-key"
    ) as client:
        # Execute command
        result = await client.execute_command("ls -la")
        print(result)
        
        # Read file
        content = await client.read_file("/etc/hostname")
        print(content)
        
        # Get system metrics
        metrics = await client.get_system_metrics()
        print(metrics)

asyncio.run(main())
```

## Architecture

### Components

```
vm_agent/
├── server.py          # Main agent server with MCP protocol support
├── client.py          # Client library for connecting to agents
├── cli.py             # Command-line interface
├── installer.py       # 🆕 Smart installer with environment detection
├── tools/             # Tool implementations
│   ├── shell_executor.py      # Shell command execution
│   ├── file_manager.py        # File system operations
│   ├── system_monitor.py      # System metrics collection
│   ├── log_analyzer.py        # Log analysis and parsing
│   ├── security_manager.py    # 🔧 Enhanced security and authentication
│   ├── websocket_handler.py   # 🔧 Improved WebSocket communication
│   └── tenant_manager.py      # Multi-tenant management
├── config/            # Configuration files
├── systemd/           # System service files
└── scripts/           # 🆕 Diagnostic and utility scripts
    ├── diagnose_environment.py    # Environment diagnostic tool
    └── test_server.py             # Server functionality tests
```

### 🆕 Smart Installation Features

#### Python Environment Auto-Detection

The installer automatically detects and configures the correct Python environment:

```bash
# When you run the installer from a virtual environment:
(venv) $ sudo python3 -m vm_agent.installer --orchestrator-url URL

# Output:
✓ Detected virtual environment, using: /path/to/venv/bin/python3
✓ Installed systemd service
```

#### Intelligent Wrapper Script

For complex environments, the wrapper script provides:

- **Environment Detection**: Automatically finds the correct Python interpreter
- **Fallback Mechanisms**: Tries multiple Python locations if the original is moved
- **Dependency Validation**: Tests if Python can import required modules
- **Clear Error Messages**: Provides actionable error information

Example wrapper script generated:

```bash
#!/bin/bash
# VM Agent Wrapper Script - Auto-generated

cd /opt/vm-agent

# Auto-detect Python environment
DETECTED_PYTHON="/root/vm_ai_agent/venv/bin/python3"

# Test if Python can import required modules
if ! "$DETECTED_PYTHON" -c "import aiofiles, aiohttp, vm_agent" 2>/dev/null; then
    echo "❌ Python cannot import required modules"
    # Try fallback locations...
    exit 1
fi

# Execute the vm-agent server
exec "$DETECTED_PYTHON" -m vm_agent.server "$@"
```

### Communication Flow

```
┌─────────────────┐    HTTP/WebSocket    ┌──────────────────┐
│   Orchestrator  │ ◄─────────────────► │    VM Agent      │
│                 │                      │                  │
│  - Provisioning │                      │ - Command Exec   │
│  - Commands      │                      │ - File Ops       │
│  - Monitoring    │                      │ - Monitoring     │
└─────────────────┘                      └──────────────────┘
                                                   │
                                                   ▼
                                          ┌──────────────────┐
                                          │   Target VM      │
                                          │                  │
                                          │ - OS Operations  │
                                          │ - Applications   │
                                          │ - Services       │
                                          └──────────────────┘
```

## Configuration

### Environment Variables

```bash
# Required
export ORCHESTRATOR_URL="https://orchestrator.example.com"
export VM_ID="vm-12345"  # Auto-generated if not provided

# Optional
export PROVISIONING_TOKEN="eyJ..."  # For automated setup
export API_KEY="your-api-key"       # For authentication
```

### Configuration File

```yaml
# config/agent_config.yaml
agent:
  id: vm-agent-example
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
```

## CLI Commands

### Server Management

```bash
# Start server
vm-agent server --host 0.0.0.0 --port 8080

# Start with SSL disabled
vm-agent server --no-ssl

# Run in daemon mode (future feature)
vm-agent server --daemon
```

### Installation & Setup

```bash
# Automated installation
vm-agent install --orchestrator-url URL --provisioning-token TOKEN

# Manual installation
vm-agent install --orchestrator-url URL --tenant-id TENANT

# Installation with wrapper script
vm-agent install --orchestrator-url URL --use-wrapper

# Force reinstall
vm-agent install --orchestrator-url URL --provisioning-token TOKEN --force

# Uninstall
vm-agent install --uninstall
```

### Operations

```bash
# Check status
vm-agent status

# Execute commands
vm-agent exec "ps aux"
vm-agent exec "docker ps" --timeout 60

# File operations
vm-agent ls /var/log
vm-agent ls /home/user --path /home/user

# System monitoring
vm-agent metrics

# Log analysis
vm-agent logs /var/log/syslog --lines 1000

# Run diagnostics
vm-agent test

# Show configuration
vm-agent config
vm-agent config --output config.yaml
```

### 🆕 Diagnostic Commands

```bash
# Comprehensive environment diagnostics
python3 scripts/diagnose_environment.py

# Test server functionality
python3 scripts/test_server.py

# Check Python environment
python3 -c "import vm_agent; print('✅ VM Agent works')"
```

## API Reference

### MCP Protocol Endpoints

The agent implements the Model Context Protocol (MCP) for tool integration:

#### Tools Available

- `execute_shell_command(command: str, timeout: int = 300)`
- `read_file(file_path: str, encoding: str = 'utf-8')`
- `write_file(file_path: str, content: str, encoding: str = 'utf-8')`
- `list_directory(directory_path: str)`
- `get_system_metrics()`
- `get_process_list()`
- `analyze_log_file(log_path: str, lines: int = 100)`

#### HTTP Endpoints

- `GET /health` - Health check (🔧 Enhanced with security status)
- `GET /info` - Agent information
- `GET /api/v1/ca-certificate` - Get CA certificate (🔧 Improved error handling)
- `POST /mcp` - MCP protocol requests

### 🔧 Enhanced Health Check Response

```json
{
  "status": "healthy",
  "vm_id": "vm-12345",
  "version": "1.0.0",
  "tenant_status": "provisioned",
  "security_status": "fully_initialized",
  "tools_enabled": ["shell", "file", "system", "logs"],
  "websocket_connected": true,
  "timestamp": "2024-01-01T12:00:00Z"
}
```

## Security

### Authentication Methods

1. **API Key Authentication**
   ```python
   client = VMAgentClient("https://agent:8080", api_key="your-key")
   ```

2. **Certificate-based Authentication (mTLS)**
   ```python
   client = VMAgentClient(
       "https://agent:8080",
       ca_cert_path="/path/to/ca.crt",
       client_cert_path="/path/to/client.crt",
       client_key_path="/path/to/client.key"
   )
   ```

### 🔧 Enhanced Security Features

The security manager now includes:

- **🔍 Smart Credential Loading**: Automatically loads credentials from disk with fallbacks
- **🛡️ Improved API Key Verification**: Better error handling and validation
- **🔐 Enhanced Certificate Management**: Graceful handling of missing certificates
- **⚡ Initialization Detection**: Checks if security is properly configured

### Certificate Management

The agent automatically manages certificates for secure communication:

```bash
# Certificates are stored in:
/opt/vm-agent/security/
├── ca.crt              # CA certificate
├── server.crt          # Server certificate
├── server.key          # Server private key
├── vm.crt              # VM agent certificate
├── vm.key              # VM agent private key
└── api.key             # API key file
```

## Development

### Setting up Development Environment

```bash
# Clone repository
git clone https://github.com/ai-infra/vm-agent.git
cd vm-agent

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install development dependencies
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=vm_agent --cov-report=html

# Run specific test file
pytest tests/test_server.py

# Run with verbose output
pytest -v

# 🆕 Run server functionality tests
python scripts/test_server.py
```

### Code Quality

```bash
# Format code
black vm_agent/

# Lint code
flake8 vm_agent/

# Type checking
mypy vm_agent/
```

## Deployment

### Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY . /app

RUN pip install ai-infra-vm-agent

CMD ["vm-agent", "server"]
```

### Systemd Service (🔧 Enhanced)

The installer now creates optimized systemd services:

```bash
# Install as system service (auto-detects environment)
sudo python3 -m vm_agent.installer --orchestrator-url URL

# Service file is automatically generated at:
# /etc/systemd/system/vm-agent.service
```

Example generated service file:

```ini
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
ExecStart=/root/vm_ai_agent/venv/bin/python3 -m vm_agent.server
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true

[Install]
WantedBy=multi-user.target
```

### Kubernetes

```yaml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: vm-agent
spec:
  template:
    spec:
      containers:
      - name: vm-agent
        image: ai-infra/vm-agent:latest
        env:
        - name: ORCHESTRATOR_URL
          value: "https://orchestrator.example.com"
        ports:
        - containerPort: 8080
```

## Monitoring & Observability

### Health Checks

```bash
# Check agent health
curl https://agent:8080/health

# Expected response (🔧 Enhanced):
{
  "status": "healthy",
  "vm_id": "vm-12345",
  "version": "1.0.0",
  "tenant_status": "provisioned",
  "security_status": "fully_initialized",
  "tools_enabled": ["shell", "file", "system", "logs"],
  "websocket_connected": true,
  "timestamp": "2024-01-01T12:00:00Z"
}
```

### Metrics Collection

The agent provides Prometheus-compatible metrics:

```bash
# System metrics
curl https://agent:8080/metrics
```

### Logging

Logs are written to `/var/log/vm-agent.log` with structured format:

```
2024-01-01 12:00:00 - vm_agent.server - INFO - VM Agent Server vm-12345 started
2024-01-01 12:00:01 - vm_agent.tools.shell - INFO - Command executed: ls -la
2024-01-01 12:00:02 - vm_agent.security - INFO - API key validated for request
```

## Troubleshooting

### 🆕 Comprehensive Diagnostic Tool

**First step for any issue**: Run the diagnostic tool

```bash
python3 scripts/diagnose_environment.py
```

This provides:
- ✅ Complete Python environment analysis
- ✅ Dependency verification
- ✅ VM agent module testing
- ✅ Installation path validation
- ✅ Systemd service status
- ✅ Specific fix recommendations

### Common Issues

#### 🔧 Environment Issues

**ModuleNotFoundError: No module named 'aiofiles'**

```bash
# Diagnosis
python3 scripts/diagnose_environment.py

# Quick fixes
sudo python3 -m vm_agent.installer --orchestrator-url URL --use-wrapper
# OR
sudo pip3 install aiofiles aiohttp aiohttp-cors pyyaml cryptography psutil
```

**Service fails to start**

```bash
# Check service status
sudo systemctl status vm-agent

# Check detailed logs
sudo journalctl -u vm-agent -f --no-pager

# Run diagnostics
python3 scripts/diagnose_environment.py

# Test Python environment
python3 -c "import vm_agent; print('✅ VM Agent works')"
```

#### Connection Refused
```bash
# Check if service is running
sudo systemctl status vm-agent

# Check logs
sudo journalctl -u vm-agent -f

# Test connectivity
curl http://localhost:8080/health

# Run diagnostic
python3 scripts/diagnose_environment.py
```

#### Certificate Issues
```bash
# Check CA certificate endpoint
curl http://localhost:8080/api/v1/ca-certificate

# Verify certificates exist
ls -la /opt/vm-agent/security/

# Regenerate certificates (reinstall)
sudo python3 -m vm_agent.installer --uninstall
sudo python3 -m vm_agent.installer --orchestrator-url URL
```

#### Permission Denied
```bash
# Check file permissions
ls -la /opt/vm-agent/

# Fix permissions
sudo chown -R vm-agent:vm-agent /opt/vm-agent/
sudo chmod 600 /opt/vm-agent/security/*
```

### 🆕 Step-by-Step Troubleshooting

1. **Run Diagnostic Tool**
   ```bash
   python3 scripts/diagnose_environment.py
   ```

2. **Check Service Status**
   ```bash
   sudo systemctl status vm-agent
   sudo journalctl -u vm-agent -f
   ```

3. **Test Manual Startup**
   ```bash
   cd /opt/vm-agent
   sudo -u vm-agent python3 -m vm_agent.server
   ```

4. **Verify Dependencies**
   ```bash
   python3 -c "import aiofiles, aiohttp, vm_agent; print('✅ All modules work')"
   ```

5. **Reinstall if Needed**
   ```bash
   sudo python3 -m vm_agent.installer --uninstall
   sudo python3 -m vm_agent.installer --orchestrator-url YOUR_URL --use-wrapper
   ```

## Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Reporting Issues

Please report issues on [GitHub Issues](https://github.com/ai-infra/vm-agent/issues) with:
- VM Agent version
- Operating system and version
- Configuration (sanitized)
- Output from `python3 scripts/diagnose_environment.py`
- Steps to reproduce
- Expected vs actual behavior

## Recent Improvements (v1.1.0)

### 🆕 Major Enhancements

- **🔍 Smart Environment Detection**: Automatic Python environment detection and configuration
- **🛡️ Intelligent Wrapper Scripts**: Advanced fallback mechanisms for complex environments  
- **🧪 Comprehensive Diagnostics**: Built-in troubleshooting and validation tools
- **🔧 Enhanced Security**: Improved credential management and error handling
- **⚡ Better Error Recovery**: Graceful handling of missing dependencies and partial states
- **📋 Improved Documentation**: Comprehensive installation and troubleshooting guides

### 🔧 Technical Improvements

- **SecurityManager**: Added credential loading, API key verification, and certificate management
- **Installer**: Smart Python environment detection and flexible installation options  
- **Server**: Enhanced initialization flow and better SSL handling
- **WebSocket Handler**: Improved credential validation and registration flow
- **Diagnostic Tools**: Environment analysis and specific fix recommendations

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

- 📖 [Documentation](https://docs.ai-infra.com/vm-agent)
- 💬 [Discord Community](https://discord.gg/ai-infra)
- 📧 [Email Support](mailto:support@ai-infra.com)
- 🐛 [Issue Tracker](https://github.com/ai-infra/vm-agent/issues)
- 🧪 [Diagnostic Tool](scripts/diagnose_environment.py)

---

**AI Infra VM Agent** - Making VM management simple, secure, and scalable. 

*Now with intelligent environment detection and comprehensive troubleshooting tools!* 🚀 