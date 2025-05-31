# Provisioning Token Scripts

This directory contains scripts to manually obtain provisioning tokens from the AI-Infra backend for VM agent enrollment.

## Scripts Available

### 1. `get_provisioning_token.py` - Python Script (Recommended)

A comprehensive Python script with full feature support including interactive mode, command-line interface, and token management.

#### Features:
- ✅ Interactive mode with organization selection
- ✅ Command-line mode for automation
- ✅ Username/password or API key authentication
- ✅ Token listing and management
- ✅ Token expiration and usage limits
- ✅ Save tokens to files
- ✅ SSL verification control

#### Requirements:
```bash
pip install requests urllib3
```

#### Usage Examples:

**Interactive Mode:**
```bash
python3 get_provisioning_token.py --backend-url https://your-backend-url.com
```

**Command Line Mode:**
```bash
# With username/password
python3 get_provisioning_token.py \
  --backend-url https://your-backend-url.com \
  --username admin \
  --org-id org-123 \
  --name "Production Token" \
  --expires-hours 48 \
  --max-uses 5

# With API key
python3 get_provisioning_token.py \
  --backend-url https://your-backend-url.com \
  --api-key "your-api-key" \
  --org-id org-123 \
  --output-file token.txt

# List existing tokens
python3 get_provisioning_token.py \
  --backend-url https://your-backend-url.com \
  --username admin \
  --org-id org-123 \
  --list-tokens
```

**For Development (no SSL verification):**
```bash
python3 get_provisioning_token.py \
  --backend-url https://localhost:8000 \
  --no-ssl-verify \
  --username admin
```

### 2. `get_token.sh` - Bash Script (Simple)

A lightweight bash script for quick token generation with minimal dependencies.

#### Requirements:
```bash
# Ubuntu/Debian
sudo apt-get install curl jq

# CentOS/RHEL
sudo yum install curl jq

# macOS
brew install curl jq
```

#### Usage Examples:

**Interactive Mode:**
```bash
./get_token.sh https://your-backend-url.com
```

**With Predefined Parameters:**
```bash
./get_token.sh https://your-backend-url.com admin org-123
```

## Quick Start Guide

### Step 1: Choose Your Script

- **Use Python script** if you need advanced features, API key auth, or token management
- **Use Bash script** if you want something simple and lightweight

### Step 2: Run the Script

**For Python script:**
```bash
cd scripts/
python3 get_provisioning_token.py --backend-url https://your-ai-infra-backend.com
```

**For Bash script:**
```bash
cd scripts/
chmod +x get_token.sh
./get_token.sh https://your-ai-infra-backend.com
```

### Step 3: Follow the Prompts

1. Enter your credentials (username/password or API key)
2. Select an organization (if multiple available)
3. Configure token parameters:
   - Name (optional)
   - Description (optional)
   - Validity period (default: 24 hours)
   - Maximum uses (default: 1)

### Step 4: Get Your Token

The script will display your provisioning token and provide the installation command:

```bash
sudo vm-agent-install --orchestrator-url https://your-backend-url.com --provisioning-token 'your-token-here'
```

## API Endpoints Used

The scripts interact with these AI-Infra backend endpoints:

- `POST /api/v1/auth/login` - Authentication
- `GET /api/v1/organizations` - List organizations
- `POST /api/v1/organizations/{org_id}/provisioning-tokens` - Create tokens
- `GET /api/v1/organizations/{org_id}/provisioning-tokens` - List tokens

## Security Notes

1. **Token Security**: Provisioning tokens are sensitive. Store them securely and use them promptly.

2. **SSL Verification**: Always use SSL verification in production. Only disable for development/testing.

3. **Token Expiration**: Set appropriate expiration times. Shorter is better for security.

4. **API Keys**: If using API keys, ensure they have appropriate permissions for token creation.

## Troubleshooting

### Common Issues:

**Authentication Failed:**
- Verify your username/password or API key
- Check if your account has permission to create tokens
- Ensure the backend URL is correct

**No Organizations Found:**
- Verify your account has access to organizations
- Check if organizations exist in the system
- Ensure you have the correct permissions

**Network Errors:**
- Check backend URL accessibility
- Verify SSL certificates (or use --no-ssl-verify for testing)
- Check firewall and network connectivity

**Token Creation Failed:**
- Verify organization ID is correct
- Check your permissions for the organization
- Ensure token parameters are valid

### Debug Mode:

For the Python script, you can enable debug output:
```bash
python3 -v get_provisioning_token.py --backend-url https://your-backend-url.com
```

For the bash script, enable verbose mode:
```bash
bash -x get_token.sh https://your-backend-url.com
```

## Integration Examples

### CI/CD Pipeline:

```bash
# Generate token in pipeline
TOKEN=$(python3 get_provisioning_token.py \
  --backend-url $BACKEND_URL \
  --api-key $API_KEY \
  --org-id $ORG_ID \
  --name "CI-${BUILD_NUMBER}" \
  --expires-hours 1 | grep "TOKEN:" | cut -d' ' -f2)

# Use token for VM setup
ssh $VM_HOST "sudo vm-agent-install --orchestrator-url $BACKEND_URL --provisioning-token '$TOKEN'"
```

### Automated Deployment:

```python
import subprocess
import os

def get_provisioning_token(org_id):
    cmd = [
        'python3', 'get_provisioning_token.py',
        '--backend-url', os.getenv('BACKEND_URL'),
        '--api-key', os.getenv('API_KEY'),
        '--org-id', org_id,
        '--expires-hours', '2'
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    # Parse token from output
    for line in result.stdout.split('\n'):
        if line.startswith('🔑 TOKEN:'):
            return line.split(':', 1)[1].strip()
    
    raise Exception("Failed to get token")
```

## Support

For issues with these scripts:
1. Check the troubleshooting section above
2. Verify your AI-Infra backend is running and accessible
3. Review the backend logs for any API errors
4. Check the script output for specific error messages 