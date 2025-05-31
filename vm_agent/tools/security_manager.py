import os
import ssl
import json
import uuid
import asyncio
import aiohttp
import hashlib
import secrets
from pathlib import Path
from datetime import datetime, timedelta
from cryptography import x509
from cryptography.x509.oid import NameOID, ExtensionOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from typing import Dict, Any, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

class SecurityManager:
    """Manages certificates, keys, and secure communication for VM agents"""
    
    def __init__(self, config_dir: Path = Path("/opt/vm-agent/security")):
        self.config_dir = config_dir
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # File paths
        self.ca_cert_path = self.config_dir / "ca.crt"
        self.vm_key_path = self.config_dir / "vm.key"
        self.vm_cert_path = self.config_dir / "vm.crt"
        self.vm_csr_path = self.config_dir / "vm.csr"
        self.api_key_path = self.config_dir / "api.key"
        self.vm_id_path = self.config_dir / "vm.id"
        
        # In-memory storage
        self._vm_id = None
        self._api_key = None
        self._ssl_context = None
    
    async def initialize(self, orchestrator_url: str, ca_cert_content: Optional[str] = None):
        """Initialize security components during installation"""
        
        # Generate or load VM ID
        self._vm_id = await self._get_or_create_vm_id()
        
        # Generate API key
        self._api_key = await self._get_or_create_api_key()
        
        # Save CA certificate if provided
        if ca_cert_content:
            with open(self.ca_cert_path, 'w') as f:
                f.write(ca_cert_content)
        
        # Generate VM keypair and CSR
        private_key, csr = await self._generate_keypair_and_csr()
        
        # Request certificate from orchestrator
        certificate = await self._request_certificate(orchestrator_url, csr)
        
        # Save certificate
        with open(self.vm_cert_path, 'w') as f:
            f.write(certificate)
        
        # Create SSL context
        self._ssl_context = self._create_ssl_context()
        
        logger.info(f"Security initialized for VM {self._vm_id}")
        return self._vm_id, self._api_key
    
    async def _get_or_create_vm_id(self) -> str:
        """Generate or retrieve unique VM ID"""
        if self.vm_id_path.exists():
            with open(self.vm_id_path, 'r') as f:
                return f.read().strip()
        
        # Generate new VM ID
        vm_id = f"vm-{uuid.uuid4().hex[:12]}"
        with open(self.vm_id_path, 'w') as f:
            f.write(vm_id)
        
        return vm_id
    
    async def _get_or_create_api_key(self) -> str:
        """Generate or retrieve API key"""
        if self.api_key_path.exists():
            with open(self.api_key_path, 'r') as f:
                return f.read().strip()
        
        # Generate new API key
        api_key = secrets.token_urlsafe(32)
        with open(self.api_key_path, 'w') as f:
            f.write(api_key)
        
        # Secure the file
        os.chmod(self.api_key_path, 0o600)
        
        return api_key
    
    async def _generate_keypair_and_csr(self) -> Tuple[str, str]:
        """Generate RSA keypair and certificate signing request"""
        
        # Generate private key
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )
        
        # Save private key
        private_key_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        
        with open(self.vm_key_path, 'wb') as f:
            f.write(private_key_pem)
        
        os.chmod(self.vm_key_path, 0o600)
        
        # Create CSR
        subject = x509.Name([
            x509.NameAttribute(NameOID.COMMON_NAME, self._vm_id),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "VM-Agent"),
        ])
        
        csr = x509.CertificateSigningRequestBuilder().subject_name(
            subject
        ).add_extension(
            x509.SubjectAlternativeName([
                x509.DNSName(self._vm_id),
            ]),
            critical=False,
        ).sign(private_key, hashes.SHA256(), backend=default_backend())
        
        csr_pem = csr.public_bytes(serialization.Encoding.PEM).decode('utf-8')
        
        with open(self.vm_csr_path, 'w') as f:
            f.write(csr_pem)
        
        return private_key_pem.decode('utf-8'), csr_pem
    
    async def _request_certificate(self, orchestrator_url: str, csr: str) -> str:
        """Request certificate from orchestrator"""
        
        # Prepare registration data
        registration_data = {
            "vm_id": self._vm_id,
            "api_key": self._api_key,
            "csr": csr,
            "hostname": os.uname().nodename,
            "registration_time": datetime.utcnow().isoformat(),
            "agent_version": "1.0.0",
            "capabilities": {
                "shell_executor": True,
                "file_manager": True,
                "system_monitor": True,
                "log_analyzer": True
            }
        }
        
        # Initial registration without mTLS (using API key)
        async with aiohttp.ClientSession() as session:
            headers = {
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json"
            }
            
            try:
                async with session.post(
                    f"{orchestrator_url}/api/v1/agents/register",
                    json=registration_data,
                    headers=headers,
                    ssl=False  # Initial registration might use self-signed cert
                ) as response:
                    if response.status != 200:
                        raise Exception(f"Registration failed: {await response.text()}")
                    
                    result = await response.json()
                    return result["certificate"]
                    
            except Exception as e:
                logger.error(f"Certificate request failed: {e}")
                raise
    
    def _create_ssl_context(self) -> ssl.SSLContext:
        """Create SSL context for mTLS"""
        context = ssl.create_default_context(
            purpose=ssl.Purpose.CLIENT_AUTH,
            cafile=str(self.ca_cert_path) if self.ca_cert_path.exists() else None
        )
        
        if self.vm_cert_path.exists() and self.vm_key_path.exists():
            context.load_cert_chain(
                certfile=str(self.vm_cert_path),
                keyfile=str(self.vm_key_path)
            )
        
        # Set strong ciphers
        context.set_ciphers('ECDHE+AESGCM:ECDHE+CHACHA20:DHE+AESGCM:DHE+CHACHA20:!aNULL:!MD5:!DSS')
        
        return context
    
    def get_ssl_context(self) -> ssl.SSLContext:
        """Get SSL context for secure connections"""
        if not self._ssl_context:
            self._ssl_context = self._create_ssl_context()
        return self._ssl_context
    
    async def encrypt_payload(self, data: Dict[str, Any], recipient_public_key: Optional[str] = None) -> Dict[str, Any]:
        """Encrypt sensitive payload data"""
        
        # Generate AES key for this message
        aes_key = secrets.token_bytes(32)  # 256-bit key
        iv = secrets.token_bytes(16)  # 128-bit IV
        
        # Encrypt data with AES
        cipher = Cipher(
            algorithms.AES(aes_key),
            modes.CBC(iv),
            backend=default_backend()
        )
        encryptor = cipher.encryptor()
        
        # Prepare and pad data
        json_data = json.dumps(data).encode('utf-8')
        padding_length = 16 - (len(json_data) % 16)
        padded_data = json_data + (bytes([padding_length]) * padding_length)
        
        # Encrypt
        encrypted_data = encryptor.update(padded_data) + encryptor.finalize()
        
        # Create payload
        payload = {
            "encrypted_data": encrypted_data.hex(),
            "iv": iv.hex(),
            "timestamp": datetime.utcnow().isoformat(),
            "vm_id": self._vm_id
        }
        
        # If recipient public key is provided, encrypt AES key with RSA
        if recipient_public_key:
            public_key = serialization.load_pem_public_key(
                recipient_public_key.encode('utf-8'),
                backend=default_backend()
            )
            
            encrypted_key = public_key.encrypt(
                aes_key,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )
            
            payload["encrypted_key"] = encrypted_key.hex()
        else:
            # Use pre-shared key derivation
            payload["key_id"] = hashlib.sha256(aes_key).hexdigest()[:16]
        
        return payload
    
    def verify_certificate(self, cert_pem: str) -> bool:
        """Verify a certificate against our CA"""
        try:
            cert = x509.load_pem_x509_certificate(
                cert_pem.encode('utf-8'),
                backend=default_backend()
            )
            
            if not self.ca_cert_path.exists():
                logger.warning("CA certificate not found, cannot verify")
                return False
            
            with open(self.ca_cert_path, 'rb') as f:
                ca_cert = x509.load_pem_x509_certificate(
                    f.read(),
                    backend=default_backend()
                )
            
            # Verify signature
            ca_public_key = ca_cert.public_key()
            ca_public_key.verify(
                cert.signature,
                cert.tbs_certificate_bytes,
                padding.PKCS1v15(),
                cert.signature_hash_algorithm
            )
            
            # Check validity period
            now = datetime.utcnow()
            if now < cert.not_valid_before or now > cert.not_valid_after:
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Certificate verification failed: {e}")
            return False


class SecureHTTPClient:
    """Simplified secure HTTP client"""
    
    def __init__(self, security_manager: SecurityManager):
        self.security_manager = security_manager
    
    def get_headers(self) -> Dict[str, str]:
        """Get headers with API key"""
        return {
            "X-API-Key": self.security_manager._api_key,
            "Content-Type": "application/json"
        }