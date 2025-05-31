"""
Tenant management for VM agents
Handles provisioning token validation and organization setup
"""

import os
import json
import jwt
import asyncio
import aiohttp
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class TenantManager:
    """Manages tenant/organization configuration for VM agents"""
    
    def __init__(self):
        self.tenant_config_file = "/opt/vm-agent/tenant/tenant.json"
    
    async def load_tenant_config(self) -> Optional[Dict[str, Any]]:
        """Load tenant configuration"""
        try:
            if os.path.exists(self.tenant_config_file):
                with open(self.tenant_config_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load tenant config: {e}")
        
        return None
    
    async def save_tenant_config(self, config: Dict[str, Any]) -> bool:
        """Save tenant configuration"""
        try:
            os.makedirs(os.path.dirname(self.tenant_config_file), exist_ok=True)
            
            with open(self.tenant_config_file, 'w') as f:
                json.dump(config, f, indent=2)
            
            os.chmod(self.tenant_config_file, 0o600)
            logger.info("Tenant configuration saved")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save tenant config: {e}")
            return False
    
    async def provision_vm(self, tenant_data: Dict[str, Any]) -> Dict[str, Any]:
        """Provision VM for tenant"""
        try:
            config = {
                "organization_id": tenant_data.get("organization_id"),
                "orchestrator_url": tenant_data.get("orchestrator_url"),
                "provisioned_at": datetime.now().isoformat(),
                "status": "active"
            }
            
            if await self.save_tenant_config(config):
                return {
                    "status": "success",
                    "message": "VM provisioned successfully",
                    "config": config
                }
            else:
                return {
                    "status": "error",
                    "message": "Failed to save tenant configuration"
                }
                
        except Exception as e:
            logger.error(f"Failed to provision VM: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    async def _provision_with_token(self, token: str) -> Dict[str, Any]:
        """Provision VM using a provisioning token"""
        try:
            # Decode token to get basic info (without verification for now)
            # The actual verification will happen on the server side
            unverified_payload = jwt.decode(token, options={"verify_signature": False})
            
            # Extract organization info
            self._tenant_data = {
                "token_id": unverified_payload.get("token_id"),
                "organization_id": unverified_payload.get("organization_id"),
                "provisioning_token": token,
                "provisioned_at": datetime.utcnow().isoformat(),
                "provisioning_mode": "token",
                "metadata": unverified_payload.get("metadata", {})
            }
            
            # Save configuration
            await self._save_tenant_config()
            
            logger.info(f"VM provisioned for organization: {self._tenant_data['organization_id']}")
            return {
                "status": "success",
                "organization_id": self._tenant_data["organization_id"],
                "message": "VM successfully provisioned with token"
            }
            
        except jwt.DecodeError as e:
            logger.error(f"Invalid provisioning token: {e}")
            raise ValueError(f"Invalid provisioning token: {e}")
        except Exception as e:
            logger.error(f"Provisioning failed: {e}")
            raise
    
    async def _provision_manual(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Manual VM provisioning"""
        required_fields = ["organization_id"]
        
        # Validate required fields
        for field in required_fields:
            if field not in data:
                raise ValueError(f"Missing required field: {field}")
        
        self._tenant_data = {
            "organization_id": data["organization_id"],
            "provisioned_at": datetime.utcnow().isoformat(),
            "provisioning_mode": "manual",
            "metadata": data.get("metadata", {})
        }
        
        # Save configuration
        await self._save_tenant_config()
        
        logger.info(f"VM manually provisioned for organization: {self._tenant_data['organization_id']}")
        return {
            "status": "success",
            "organization_id": self._tenant_data["organization_id"],
            "message": "VM successfully provisioned manually"
        }
    
    async def _save_tenant_config(self):
        """Save tenant configuration to disk"""
        try:
            with open(self.tenant_config_file, 'w') as f:
                json.dump(self._tenant_data, f, indent=2)
            
            # Secure the file
            os.chmod(self.tenant_config_file, 0o600)
            
        except Exception as e:
            logger.error(f"Failed to save tenant config: {e}")
            raise
    
    def get_organization_id(self) -> Optional[str]:
        """Get the organization ID for this VM"""
        if self._tenant_data:
            return self._tenant_data.get("organization_id")
        return None
    
    def get_provisioning_token(self) -> Optional[str]:
        """Get the provisioning token if available"""
        if self._tenant_data:
            return self._tenant_data.get("provisioning_token")
        return None
    
    def is_provisioned(self) -> bool:
        """Check if VM is provisioned for a tenant"""
        return self._tenant_data is not None and "organization_id" in self._tenant_data
    
    async def validate_access(self, resource_type: str, resource_id: str) -> bool:
        """Validate access to a resource (placeholder for future implementation)"""
        # In the future, this could check resource access against organization policies
        # For now, just ensure VM is provisioned
        return self.is_provisioned()
    
    async def report_usage(self, usage_data: Dict[str, Any]):
        """Report resource usage (placeholder for future implementation)"""
        # In the future, this could report usage metrics for billing/quotas
        if not self.is_provisioned():
            logger.warning("Cannot report usage - VM not provisioned")
            return
        
        logger.info(f"Usage reported for org {self.get_organization_id()}: {usage_data}") 