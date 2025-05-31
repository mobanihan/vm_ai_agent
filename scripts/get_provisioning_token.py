#!/usr/bin/env python3
"""
Provisioning Token Generator

Script to manually obtain provisioning tokens from the AI-Infra backend
for VM agent enrollment. Supports both interactive and command-line modes.
"""

import argparse
import json
import sys
import getpass
from pathlib import Path
from datetime import datetime, timedelta
import requests
from typing import Dict, Any, Optional
import urllib3

# Disable SSL warnings for development (remove in production)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class ProvisioningTokenClient:
    """Client for obtaining provisioning tokens from AI-Infra backend"""
    
    def __init__(self, backend_url: str, verify_ssl: bool = True):
        self.backend_url = backend_url.rstrip('/')
        self.verify_ssl = verify_ssl
        self.session = requests.Session()
        self.session.verify = verify_ssl
        
    def authenticate(self, username: str, password: str) -> bool:
        """Authenticate with the backend and get access token"""
        try:
            response = self.session.post(
                f"{self.backend_url}/api/v1/auth/login",
                json={"username": username, "password": password},
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                access_token = data.get("access_token")
                if access_token:
                    self.session.headers.update({
                        "Authorization": f"Bearer {access_token}"
                    })
                    print("✅ Authentication successful")
                    return True
            
            print(f"❌ Authentication failed: {response.status_code}")
            if response.text:
                print(f"   Error: {response.text}")
            return False
            
        except Exception as e:
            print(f"❌ Authentication error: {e}")
            return False
    
    def authenticate_with_api_key(self, api_key: str) -> bool:
        """Authenticate using API key"""
        try:
            self.session.headers.update({
                "X-API-Key": api_key,
                "Content-Type": "application/json"
            })
            
            # Test the API key with a simple request
            response = self.session.get(f"{self.backend_url}/api/v1/health")
            if response.status_code == 200:
                print("✅ API key authentication successful")
                return True
            else:
                print(f"❌ API key authentication failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ API key authentication error: {e}")
            return False
    
    def list_organizations(self) -> Dict[str, Any]:
        """List available organizations"""
        try:
            response = self.session.get(f"{self.backend_url}/api/v1/organizations")
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"❌ Failed to list organizations: {response.status_code}")
                return {}
                
        except Exception as e:
            print(f"❌ Error listing organizations: {e}")
            return {}
    
    def create_provisioning_token(
        self, 
        organization_id: str,
        name: str = None,
        description: str = None,
        expires_in_hours: int = 24,
        max_uses: int = 1,
        metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Create a new provisioning token"""
        
        # Prepare token data
        token_data = {
            "organization_id": organization_id,
            "name": name or f"Manual token - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "description": description or "Manually generated provisioning token",
            "expires_at": (datetime.utcnow() + timedelta(hours=expires_in_hours)).isoformat(),
            "max_uses": max_uses,
            "metadata": metadata or {}
        }
        
        try:
            response = self.session.post(
                f"{self.backend_url}/api/v1/organizations/{organization_id}/provisioning-tokens",
                json=token_data,
                timeout=30
            )
            
            if response.status_code == 201:
                return response.json()
            else:
                print(f"❌ Failed to create token: {response.status_code}")
                if response.text:
                    print(f"   Error: {response.text}")
                return {}
                
        except Exception as e:
            print(f"❌ Error creating token: {e}")
            return {}
    
    def get_provisioning_tokens(self, organization_id: str) -> Dict[str, Any]:
        """List existing provisioning tokens for an organization"""
        try:
            response = self.session.get(
                f"{self.backend_url}/api/v1/organizations/{organization_id}/provisioning-tokens"
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"❌ Failed to get tokens: {response.status_code}")
                return {}
                
        except Exception as e:
            print(f"❌ Error getting tokens: {e}")
            return {}


def interactive_mode(client: ProvisioningTokenClient):
    """Interactive mode for token generation"""
    print("\n🔐 AI-Infra Provisioning Token Generator")
    print("=" * 50)
    
    # List organizations
    print("\n📋 Available Organizations:")
    orgs_data = client.list_organizations()
    organizations = orgs_data.get("organizations", [])
    
    if not organizations:
        print("❌ No organizations found or access denied")
        return
    
    for i, org in enumerate(organizations, 1):
        print(f"  {i}. {org['name']} (ID: {org['id']})")
    
    # Select organization
    while True:
        try:
            choice = input(f"\nSelect organization (1-{len(organizations)}): ").strip()
            org_index = int(choice) - 1
            if 0 <= org_index < len(organizations):
                selected_org = organizations[org_index]
                break
            else:
                print("❌ Invalid choice. Please try again.")
        except ValueError:
            print("❌ Please enter a valid number.")
    
    print(f"\n✅ Selected: {selected_org['name']}")
    
    # Get token parameters
    name = input("Token name (optional): ").strip() or None
    description = input("Token description (optional): ").strip() or None
    
    while True:
        try:
            expires_hours = input("Token validity in hours (default: 24): ").strip()
            expires_hours = int(expires_hours) if expires_hours else 24
            break
        except ValueError:
            print("❌ Please enter a valid number of hours.")
    
    while True:
        try:
            max_uses = input("Maximum uses (default: 1): ").strip()
            max_uses = int(max_uses) if max_uses else 1
            break
        except ValueError:
            print("❌ Please enter a valid number.")
    
    # Create token
    print(f"\n🔄 Creating provisioning token...")
    token_data = client.create_provisioning_token(
        organization_id=selected_org['id'],
        name=name,
        description=description,
        expires_in_hours=expires_hours,
        max_uses=max_uses
    )
    
    if token_data:
        print("\n✅ Provisioning token created successfully!")
        print("=" * 50)
        print(f"Organization: {selected_org['name']}")
        print(f"Token ID: {token_data.get('id')}")
        print(f"Name: {token_data.get('name')}")
        print(f"Expires: {token_data.get('expires_at')}")
        print(f"Max Uses: {token_data.get('max_uses')}")
        print(f"\n🔑 TOKEN: {token_data.get('token')}")
        print("=" * 50)
        print("\n💡 Usage:")
        print(f"   sudo vm-agent-install --orchestrator-url {client.backend_url} --provisioning-token '{token_data.get('token')}'")
        
        # Save to file option
        save_file = input("\nSave token to file? (y/N): ").strip().lower()
        if save_file == 'y':
            filename = f"provisioning_token_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            with open(filename, 'w') as f:
                f.write(f"# Provisioning Token for {selected_org['name']}\n")
                f.write(f"# Created: {datetime.now().isoformat()}\n")
                f.write(f"# Expires: {token_data.get('expires_at')}\n")
                f.write(f"# Organization ID: {selected_org['id']}\n\n")
                f.write(f"TOKEN={token_data.get('token')}\n\n")
                f.write(f"# Installation command:\n")
                f.write(f"# sudo vm-agent-install --orchestrator-url {client.backend_url} --provisioning-token '{token_data.get('token')}'\n")
            print(f"✅ Token saved to: {filename}")


def main():
    parser = argparse.ArgumentParser(
        description="Generate provisioning tokens for VM agent enrollment",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive mode
  python get_provisioning_token.py --backend-url https://api.ai-infra.com

  # Command line mode
  python get_provisioning_token.py --backend-url https://api.ai-infra.com \\
    --org-id org-123 --name "Dev Token" --expires-hours 48

  # Using API key
  python get_provisioning_token.py --backend-url https://api.ai-infra.com \\
    --api-key "your-api-key" --org-id org-123
        """
    )
    
    parser.add_argument(
        "--backend-url", 
        required=True,
        help="AI-Infra backend URL (e.g., https://api.ai-infra.com)"
    )
    
    auth_group = parser.add_mutually_exclusive_group()
    auth_group.add_argument(
        "--username", 
        help="Username for authentication"
    )
    auth_group.add_argument(
        "--api-key", 
        help="API key for authentication"
    )
    
    parser.add_argument(
        "--org-id", 
        help="Organization ID (for non-interactive mode)"
    )
    parser.add_argument(
        "--name", 
        help="Token name"
    )
    parser.add_argument(
        "--description", 
        help="Token description"
    )
    parser.add_argument(
        "--expires-hours", 
        type=int, 
        default=24,
        help="Token validity in hours (default: 24)"
    )
    parser.add_argument(
        "--max-uses", 
        type=int, 
        default=1,
        help="Maximum token uses (default: 1)"
    )
    parser.add_argument(
        "--no-ssl-verify", 
        action="store_true",
        help="Disable SSL certificate verification"
    )
    parser.add_argument(
        "--output-file", 
        help="Save token to specified file"
    )
    parser.add_argument(
        "--list-tokens", 
        action="store_true",
        help="List existing tokens for the organization"
    )
    
    args = parser.parse_args()
    
    # Create client
    client = ProvisioningTokenClient(args.backend_url, verify_ssl=not args.no_ssl_verify)
    
    # Authentication
    if args.api_key:
        if not client.authenticate_with_api_key(args.api_key):
            sys.exit(1)
    else:
        username = args.username
        if not username:
            username = input("Username: ")
        
        password = getpass.getpass("Password: ")
        
        if not client.authenticate(username, password):
            sys.exit(1)
    
    # List tokens mode
    if args.list_tokens:
        if not args.org_id:
            print("❌ Organization ID required for listing tokens")
            sys.exit(1)
        
        tokens_data = client.get_provisioning_tokens(args.org_id)
        tokens = tokens_data.get("tokens", [])
        
        if tokens:
            print(f"\n📋 Provisioning Tokens for Organization {args.org_id}:")
            print("=" * 70)
            for token in tokens:
                status = "🟢 Active" if token.get("is_active") else "🔴 Inactive"
                print(f"ID: {token.get('id')}")
                print(f"Name: {token.get('name')}")
                print(f"Status: {status}")
                print(f"Uses: {token.get('current_uses', 0)}/{token.get('max_uses')}")
                print(f"Expires: {token.get('expires_at')}")
                print("-" * 70)
        else:
            print("📭 No tokens found for this organization")
        return
    
    # Non-interactive mode
    if args.org_id:
        print(f"🔄 Creating provisioning token for organization {args.org_id}...")
        
        token_data = client.create_provisioning_token(
            organization_id=args.org_id,
            name=args.name,
            description=args.description,
            expires_in_hours=args.expires_hours,
            max_uses=args.max_uses
        )
        
        if token_data:
            print("✅ Token created successfully!")
            print(f"🔑 TOKEN: {token_data.get('token')}")
            
            if args.output_file:
                with open(args.output_file, 'w') as f:
                    f.write(token_data.get('token'))
                print(f"✅ Token saved to: {args.output_file}")
        else:
            sys.exit(1)
    else:
        # Interactive mode
        interactive_mode(client)


if __name__ == "__main__":
    main() 