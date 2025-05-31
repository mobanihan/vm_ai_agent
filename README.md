# AI Infra VM Agent

[![PyPI version](https://badge.fury.io/py/ai-infra-vm-agent.svg)](https://badge.fury.io/py/ai-infra-vm-agent)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A production-ready VM agent for AI infrastructure management with MCP (Model Context Protocol) support, providing secure, multi-tenant VM management capabilities with **full orchestrator integration**.

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

### ✨ **Orchestrator Integration**
- **🔐 Automatic Registration**: Full orchestrator registration with provisioning tokens
- **📜 Certificate Management**: Automatic CSR generation and certificate installation
- **🔄 Real-time Communication**: WebSocket connection with heartbeat monitoring
- **🏢 Organization Provisioning**: Multi-tenant setup with organization isolation
- **📡 Command Execution**: Remote command execution from orchestrator dashboard

### 🆕 **New Features**
- **🚀 One-Script Installation**: Complete setup with single command
- **🔍 Smart Environment Detection**: Automatically detects and sets up Python environments
- **🛡️ Intelligent Wrapper Scripts**: Handles environment changes and provides fallback mechanisms
- **🧪 Diagnostic Tools**: Comprehensive environment troubleshooting and validation
- **🔧 Flexible Installation**: Multiple installation modes for different deployment scenarios
- **⚡ Improved Error Handling**: Better error messages and recovery mechanisms

## Quick Start

### Prerequisites

- **Linux system** with systemd support
- **Root/sudo access** for system service installation
- **Network connectivity** to orchestrator
- **Valid orchestrator account** with organization membership

## 🚀 **One-Script Installation (RECOMMENDED)**

The simplest way to install and register a VM agent is with our unified setup script. This handles **everything automatically**:

### **Method 1: One-liner Installation (Production)**
```bash
curl -fsSL https://your-server.com/setup.sh | sudo bash -s -- \
  --provisioning-token "eyJhbGciOiJIUzI1NiIs..." \
  --server-url "https://your-orchestrator.com"
```

### **Method 2: Download and Run**
```bash
# Download the script
curl -fsSL https://your-server.com/setup.sh -o setup.sh
chmod +x setup.sh

# Run with your parameters
sudo ./setup.sh \
  --provisioning-token "prov_abc123..." \
  --server-url "https://your-orchestrator.com"
```

### **Available Options:**
- `--provisioning-token TOKEN` - **Required**: Get from orchestrator dashboard
- `--server-url URL` - **Required**: Your orchestrator URL
- `--skip-dependencies` - Skip system dependency installation
- `--force-reinstall` - Force reinstall even if already installed  
- `--debug` - Enable debug logging
- `--help` - Show detailed help

### **What This Script Does Automatically:**
1. 📦 **Installs system dependencies** (curl, openssl, jq, python3)
2. 🐍 **Sets up Python environment** and installs packages
3. 🔐 **Downloads CA certificate** from orchestrator
4. 🔑 **Generates VM credentials** and CSR
5. 📝 **Registers agent** with orchestrator using provisioning token
6. 📜 **Installs signed certificates** for mTLS authentication
7. ⚙️ **Creates complete agent configuration** with WebSocket URLs
8. 👤 **Sets up system user** and proper permissions
9. 🚀 **Creates and starts systemd service** with security hardening
10. ✅ **Verifies everything is working** and shows status

### **Result:**
- ✅ **Agent visible in orchestrator dashboard immediately**
- ✅ **Real-time WebSocket connection established**
- ✅ **Certificate-based authentication working**
- ✅ **Automatic heartbeat monitoring active**
- ✅ **Ready to receive commands from orchestrator**

### **Getting Your Provisioning Token:**

1. **Log in to your orchestrator dashboard**
2. **Navigate to Organizations → Your Org → Agent Management**
3. **Click "Create Provisioning Token"**
4. **Copy the token** (expires in 24 hours)
5. **Use in installation command above**

## 🔧 Alternative Installation Methods

### Method 2: CLI-based Installation

If you already have the VM agent code installed:

```bash
# Install with provisioning token
vm-agent install --orchestrator-url "https://your-orchestrator.com" \
                 --provisioning-token "prov_abc123..."

# Alternative: provision existing installation
vm-agent provision --orchestrator-url "https://your-orchestrator.com" \
                   --provisioning-token "prov_abc123..."

# Start server
vm-agent server --config /opt/vm-agent/config/agent_config.yaml
```

### Method 3: Development Installation

For development or when you have the source code:

```bash
# Clone and install
git clone https://github.com/ai-infra/vm-agent.git
cd vm-agent
pip install -e .

# Install and provision
vm-agent install --orchestrator-url "https://your-orchestrator.com" \
                 --provisioning-token "prov_abc123..."
```

## 🔧 Configuration

### Agent Configuration File

After installation, the agent configuration is located at `/opt/vm-agent/config/agent_config.yaml`:

```yaml
agent:
  id: vm-hostname-123456
  name: "VM Agent"
  version: "1.0.0"

server:
  host: "0.0.0.0"
  port: 8080
  ssl:
    enabled: true
    cert_file: "/opt/vm-agent/security/vm_agent.crt"
    key_file: "/opt/vm-agent/security/vm_agent.key"

orchestrator:
  url: "https://your-orchestrator.com"
  websocket_url: "wss://your-orchestrator.com/api/v1/agents/vm-id/ws"
  agent_id: "agent_789"
  heartbeat_interval: 30
  command_poll_interval: 5

security:
  enabled: true
  mtls: true
  api_key_required: true
  ca_cert_file: "/opt/vm-agent/security/ca.crt"

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
```

## 🔐 Security Architecture

### Certificate-based Authentication Flow

1. **Agent generates** a Certificate Signing Request (CSR) during installation
2. **Registration API call** sends CSR + provisioning token to orchestrator
3. **Orchestrator validates** token and signs the CSR
4. **Agent receives** signed certificate + CA certificate
5. **All communications** use mTLS with certificate validation
6. **WebSocket connection** established with certificate authentication

### Network Security

- All communication over HTTPS/WSS
- Agent validates orchestrator certificate using CA
- Orchestrator validates agent certificate
- API key authentication for REST endpoints
- No plain-text credentials in transit

### File Structure

```bash
/opt/vm-agent/
├── security/
│   ├── vm_id              # Generated VM identifier
│   ├── api_key            # Generated API key
│   ├── vm_agent.key       # Agent private key
│   ├── vm_agent.csr       # Certificate signing request
│   ├── vm_agent.crt       # Signed agent certificate
│   ├── ca.crt             # CA certificate chain
│   ├── agent_id           # Orchestrator-assigned agent ID
│   └── websocket_url      # WebSocket connection URL
├── config/
│   └── agent_config.yaml  # Main configuration file
├── venv/                  # Python virtual environment
└── src/
    └── vm_agent/          # Agent source code
```

## 📡 Communication Flow

```
┌─────────────────┐    HTTPS/WSS        ┌──────────────────┐
│   Orchestrator  │ ◄─────────────────► │    VM Agent      │
│                 │                      │                  │
│ 1. Registration │ ─ POST /agents/     │ 1. Generate CSR  │
│ 2. Cert Signing │   register          │ 2. Send Token    │
│ 3. Commands     │ ─ WebSocket         │ 3. Install Certs │
│ 4. Monitoring   │   /agents/vm-id/ws  │ 4. Connect WS    │
│ 5. Heartbeats   │                     │ 5. Execute Cmds  │
└─────────────────┘                     └──────────────────┘
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

## 🔧 Backend Integration Notes

### Registration API Changes (v1.0.0+)

**Important for Backend Developers**: The registration endpoint now receives CSR data as base64-encoded to avoid JSON escaping issues:

**Previous format (deprecated):**
```json
{
  "csr": "-----BEGIN CERTIFICATE REQUEST-----\nMIIC...\n-----END CERTIFICATE REQUEST-----"
}
```

**New format (current):**
```json
{
  "csr_base64": "LS0tLS1CRUdJTi..."
}
```

**Backend Handling:**
```python
import base64
from cryptography import x509

# Decode base64 CSR
csr_pem = base64.b64decode(request_data['csr_base64']).decode('utf-8')

# Parse with cryptography library
csr = x509.load_pem_x509_csr(csr_pem.encode('utf-8'))
```

This change resolves JSON parsing issues with escaped newlines in CSR data.

## 🛠️ CLI Commands

### Installation & Provisioning

```bash
# One-liner installation (RECOMMENDED)
curl -fsSL https://your-server.com/setup.sh | sudo bash -s -- \
  --provisioning-token "prov_abc123..." \
  --server-url "https://orchestrator.example.com"

# With additional options
curl -fsSL https://your-server.com/setup.sh | sudo bash -s -- \
  --provisioning-token "prov_abc123..." \
  --server-url "https://orchestrator.example.com" \
  --force-reinstall \
  --debug

# Direct script execution
sudo ./setup.sh \
  --provisioning-token "prov_abc123..." \
  --server-url "https://orchestrator.example.com"

# CLI installation (if vm-agent is already available)
vm-agent install --orchestrator-url "https://orchestrator.example.com" \
                 --provisioning-token "prov_123..."

# Provision existing installation
vm-agent provision --orchestrator-url "https://orchestrator.example.com" \
                   --provisioning-token "prov_123..."

# Test orchestrator connectivity
vm-agent test-connection --orchestrator-url "https://orchestrator.example.com"
```

### Server Management

```bash
# Start server
vm-agent server --host 0.0.0.0 --port 8080

# Start with custom configuration
vm-agent server --config /opt/vm-agent/config/agent_config.yaml

# Provision on startup
vm-agent server --provision --provisioning-token "prov_123..."
```

### Operations

```bash
# Check comprehensive status
vm-agent status

# Execute commands
vm-agent exec "ps aux"
vm-agent exec "docker ps" --timeout 60

# File operations
vm-agent ls /var/log

# System monitoring
vm-agent metrics

# Log analysis
vm-agent logs /var/log/syslog --lines 1000

# Run diagnostics
vm-agent test

# Show configuration
vm-agent config
```

## 🔍 Troubleshooting

### Step 1: Use Comprehensive Diagnostic Tool

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
- ✅ Orchestrator connectivity check
- ✅ Certificate validation
- ✅ Specific fix recommendations

### Common Installation Issues

#### 1. Registration Failures

**Symptoms:**
- Agent fails to register with orchestrator
- "Registration failed" error messages
- Agent not visible in orchestrator dashboard

**Diagnosis:**
```bash
# Test orchestrator connectivity
vm-agent test-connection --orchestrator-url "https://your-orchestrator.com"

# Check registration endpoint
curl -X POST "https://your-orchestrator.com/api/v1/agents/register" \
     -H "Content-Type: application/json" \
     -d '{}'

# Verify provisioning token hasn't expired
# Tokens typically expire in 24 hours
```

**Solutions:**
```bash
# Generate new provisioning token
./setup_provisioning_token.sh

# Re-run installation with new token
sudo ORCHESTRATOR_URL="https://your-orchestrator.com" \
     PROVISIONING_TOKEN="new-token-here" \
     ./enhanced_install_vm_agent.sh

# Or re-provision existing installation
vm-agent provision --orchestrator-url "https://your-orchestrator.com" \
                   --provisioning-token "new-token-here"
```

#### 2. Certificate Issues

**Symptoms:**
- SSL/TLS connection errors
- "Certificate verification failed"
- WebSocket connection failures

**Diagnosis:**
```bash
# Check certificate files exist
ls -la /opt/vm-agent/security/
# Should contain: vm_agent.key, vm_agent.crt, ca.crt

# Test certificate validity
openssl x509 -in /opt/vm-agent/security/vm_agent.crt -text -noout

# Check certificate chain
openssl verify -CAfile /opt/vm-agent/security/ca.crt \
               /opt/vm-agent/security/vm_agent.crt
```

**Solutions:**
```bash
# Re-provision to get new certificates
vm-agent provision --orchestrator-url "https://your-orchestrator.com" \
                   --provisioning-token "new-token-here"

# Or complete reinstallation
sudo ./enhanced_install_vm_agent.sh
```

#### 3. WebSocket Connection Issues

**Symptoms:**
- Agent appears registered but no real-time communication
- "WebSocket connection failed" errors
- Commands from orchestrator not received

**Diagnosis:**
```bash
# Check WebSocket URL in configuration
grep websocket_url /opt/vm-agent/config/agent_config.yaml

# Check network connectivity to WebSocket endpoint
curl -I "https://your-orchestrator.com/api/v1/agents/vm-id/ws"

# Check firewall settings
sudo ufw status
sudo iptables -L | grep 8080
```

**Solutions:**
```bash
# Verify WebSocket configuration
vm-agent status

# Restart service to retry connection
sudo systemctl restart vm-agent

# Check for network/firewall blocking WebSocket traffic
```

#### 4. Environment Issues

**ModuleNotFoundError: No module named 'aiofiles'**

```bash
# Diagnosis
python3 scripts/diagnose_environment.py

# Quick fixes
sudo python3 -m vm_agent.installer --fix-existing
# OR install system-wide
sudo pip3 install aiofiles aiohttp aiohttp-cors pyyaml cryptography psutil websockets
sudo systemctl restart vm-agent
```

#### 5. Service Start Issues

**Symptoms:**
- systemd service fails to start
- Permission errors
- Service immediately exits

**Diagnosis:**
```bash
# Check service status
sudo systemctl status vm-agent

# View detailed logs
sudo journalctl -u vm-agent -n 50

# Check file permissions
sudo ls -la /opt/vm-agent/
sudo ls -la /var/log/vm-agent/

# Test manual startup
cd /opt/vm-agent
sudo -u vm-agent python3 -m vm_agent.server
```

**Solutions:**
```bash
# Fix permissions
sudo chown -R vm-agent:vm-agent /opt/vm-agent
sudo chown -R vm-agent:vm-agent /var/log/vm-agent

# Reinstall service
sudo systemctl stop vm-agent
sudo ./enhanced_install_vm_agent.sh
```

### Debug Mode

Enable verbose logging for troubleshooting:

```bash
# Edit configuration for debug mode
sudo nano /opt/vm-agent/config/agent_config.yaml
# Change: level: DEBUG

# Restart service
sudo systemctl restart vm-agent

# View debug logs
sudo journalctl -u vm-agent -f
```

### Log Locations

- **Service logs**: `sudo journalctl -u vm-agent`
- **Application logs**: `/var/log/vm-agent/agent.log`
- **System logs**: `/var/log/vm-agent.log`

## 📊 API Reference

### MCP Protocol Endpoints

The agent implements the Model Context Protocol (MCP) for tool integration:

#### Available Tools

- `execute_shell_command(command: str, timeout: int = 300)`
- `read_file(file_path: str, encoding: str = 'utf-8')`
- `write_file(file_path: str, content: str, encoding: str = 'utf-8')`
- `list_directory(directory_path: str)`
- `get_system_metrics()`
- `get_process_list()`
- `analyze_log_file(log_path: str, lines: int = 100)`

#### HTTP Endpoints

- `GET /health` - Health check with orchestrator status
- `GET /info` - Agent information and capabilities
- `GET /api/v1/ca-certificate` - Get CA certificate for client verification
- `POST /mcp` - MCP protocol requests

### Enhanced Health Check Response

```json
{
  "status": "healthy",
  "vm_id": "vm-hostname-123456",
  "version": "1.0.0",
  "tenant_status": "provisioned",
  "security_status": "fully_initialized",
  "tools_enabled": ["shell", "file", "system", "logs"],
  "websocket_connected": true,
  "orchestrator_url": "https://your-orchestrator.com",
  "agent_id": "agent_789",
  "timestamp": "2024-01-01T12:00:00Z"
}
```

## 🔄 Monitoring and Maintenance

### Health Checks

```bash
# Basic health check
curl http://localhost:8080/health

# Detailed agent info
curl http://localhost:8080/info

# Check agent status in orchestrator dashboard
# The agent should appear online with recent heartbeat
```

### Regular Maintenance

1. **Certificate Renewal**: Handled automatically by agent (30-day renewal cycle)
2. **Log Rotation**: Configured automatically (100MB max, 5 backups)
3. **Heartbeat Monitoring**: Agent sends heartbeat every 30 seconds
4. **Updates**: Use your organization's update procedures

### Performance Monitoring

Monitor these metrics:
- CPU and memory usage of vm-agent process
- Network connectivity to orchestrator
- WebSocket connection stability
- Command execution success rate
- Certificate expiration dates

## 🏗️ Architecture

### Components

```
vm_agent/
├── server.py          # Main agent server with orchestrator integration
├── client.py          # Client library for connecting to agents
├── cli.py             # Enhanced CLI with provisioning commands
├── installer.py       # Smart installer with environment detection
├── tools/             # Tool implementations
│   ├── shell_executor.py      # Shell command execution
│   ├── file_manager.py        # File system operations
│   ├── system_monitor.py      # System metrics collection
│   ├── log_analyzer.py        # Log analysis and parsing
│   ├── security_manager.py    # Security and authentication
│   ├── websocket_handler.py   # WebSocket communication & registration
│   └── tenant_manager.py      # Multi-tenant management
├── config/            # Configuration files
├── systemd/           # System service files
└── scripts/           # Diagnostic and utility scripts
    ├── diagnose_environment.py    # Environment diagnostic tool
    └── test_server.py             # Server functionality tests
```

### Installation Scripts

```
enhanced_install_vm_agent.sh    # Complete orchestrator integration
setup_provisioning_token.sh     # Interactive token generation
install_vm_agent_fixed.sh       # Legacy/fallback installer
```

## 🚀 Development

### Setting up Development Environment

```bash
# Clone repository
git clone https://github.com/ai-infra/vm-agent.git
cd vm-agent

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install development dependencies
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install
```

### Testing with Orchestrator

```bash
# Set up test environment
export ORCHESTRATOR_URL="https://your-test-orchestrator.com"
export PROVISIONING_TOKEN="test-token"

# Test installation script
sudo ./enhanced_install_vm_agent.sh

# Test CLI commands
vm-agent test-connection
vm-agent provision
vm-agent status
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=vm_agent --cov-report=html

# Test server functionality
python scripts/test_server.py

# Test environment
python scripts/diagnose_environment.py
```

## 📋 Production Deployment

### Pre-deployment Checklist

- [ ] Orchestrator is accessible from target VMs
- [ ] Provisioning tokens generated for each organization
- [ ] Network firewall allows HTTPS/WSS to orchestrator
- [ ] Target VMs have Python 3.8+ and systemd
- [ ] DNS resolution works for orchestrator URL
- [ ] Time synchronization configured (important for certificates)

### Deployment Steps

1. **Prepare provisioning tokens:**
   ```bash
   ./setup_provisioning_token.sh
   ```

2. **Deploy to VMs:**
   ```bash
   # Copy script to each VM
   for vm in vm1 vm2 vm3; do
     scp enhanced_install_vm_agent.sh user@$vm:/tmp/
   done
   
   # Install on each VM
   for vm in vm1 vm2 vm3; do
     ssh user@$vm "sudo ORCHESTRATOR_URL='https://orchestrator.com' \
                        PROVISIONING_TOKEN='prov_123...' \
                        /tmp/enhanced_install_vm_agent.sh"
   done
   ```

3. **Verify deployment:**
   ```bash
   # Check each VM
   for vm in vm1 vm2 vm3; do
     echo "Checking $vm..."
     ssh user@$vm "curl -s http://localhost:8080/health | jq '.status'"
   done
   
   # Check orchestrator dashboard for all agents
   ```

### Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: vm-agent
spec:
  selector:
    matchLabels:
      app: vm-agent
  template:
    metadata:
      labels:
        app: vm-agent
    spec:
      hostNetwork: true
      containers:
      - name: vm-agent
        image: ai-infra/vm-agent:latest
        env:
        - name: ORCHESTRATOR_URL
          value: "https://orchestrator.example.com"
        - name: PROVISIONING_TOKEN
          valueFrom:
            secretKeyRef:
              name: vm-agent-token
              key: token
        ports:
        - containerPort: 8080
        volumeMounts:
        - name: vm-agent-data
          mountPath: /opt/vm-agent
      volumes:
      - name: vm-agent-data
        hostPath:
          path: /opt/vm-agent
```

## 🐛 Known Issues and Limitations

### Current Limitations

1. **Token Expiration**: Provisioning tokens expire in 24 hours
2. **Certificate Renewal**: Automatic renewal requires orchestrator connectivity
3. **Network Dependencies**: Agent requires persistent connection to orchestrator
4. **Single Orchestrator**: Each agent can only connect to one orchestrator

### Planned Improvements

- [ ] Multi-orchestrator support
- [ ] Offline operation mode
- [ ] Certificate pinning
- [ ] Enhanced monitoring integration
- [ ] Plugin system for custom tools

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Reporting Issues

Please report issues on [GitHub Issues](https://github.com/ai-infra/vm-agent/issues) with:
- VM Agent version
- Operating system and version
- Orchestrator URL (sanitized)
- Configuration (sanitized)
- Output from `python3 scripts/diagnose_environment.py`
- Steps to reproduce
- Expected vs actual behavior

## 📞 Support

- 📖 [Documentation](https://docs.ai-infra.com/vm-agent)
- 💬 [Discord Community](https://discord.gg/ai-infra)
- 📧 [Email Support](mailto:support@ai-infra.com)
- 🐛 [Issue Tracker](https://github.com/ai-infra/vm-agent/issues)
- 🧪 [Diagnostic Tool](scripts/diagnose_environment.py)

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

**AI Infra VM Agent** - Making VM management simple, secure, and scalable with full orchestrator integration. 

*Now with complete orchestrator integration, automatic registration, and comprehensive troubleshooting!* 🚀 