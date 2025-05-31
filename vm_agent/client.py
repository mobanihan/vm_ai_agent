#!/usr/bin/env python3
"""
VM Agent Client

Client interface for connecting to and controlling VM agents remotely.
Supports both HTTP and WebSocket communication.
"""

import asyncio
import aiohttp
import json
import logging
from typing import Dict, Any, Optional, List
from urllib.parse import urljoin
import ssl
import websockets

logger = logging.getLogger(__name__)


class VMAgentClient:
    """
    Client for communicating with VM Agent servers
    
    Provides both HTTP and WebSocket-based communication with VM agents.
    Supports certificate-based authentication and secure connections.
    """
    
    def __init__(
        self,
        agent_url: str,
        api_key: Optional[str] = None,
        ca_cert_path: Optional[str] = None,
        client_cert_path: Optional[str] = None,
        client_key_path: Optional[str] = None,
        verify_ssl: bool = True
    ):
        """
        Initialize VM Agent Client
        
        Args:
            agent_url: Base URL of the VM agent (e.g., https://vm-agent:8080)
            api_key: API key for authentication
            ca_cert_path: Path to CA certificate for SSL verification
            client_cert_path: Path to client certificate for mTLS
            client_key_path: Path to client key for mTLS
            verify_ssl: Whether to verify SSL certificates
        """
        self.agent_url = agent_url.rstrip('/')
        self.api_key = api_key
        self.ca_cert_path = ca_cert_path
        self.client_cert_path = client_cert_path
        self.client_key_path = client_key_path
        self.verify_ssl = verify_ssl
        
        # Create SSL context if certificates are provided
        self.ssl_context = self._create_ssl_context()
        
        # HTTP session
        self._session: Optional[aiohttp.ClientSession] = None
        
    def _create_ssl_context(self) -> Optional[ssl.SSLContext]:
        """Create SSL context for secure connections"""
        if not self.verify_ssl:
            return False  # Disable SSL verification
        
        if not (self.ca_cert_path or self.client_cert_path):
            return None  # Use default SSL context
        
        # Create custom SSL context
        ssl_context = ssl.create_default_context()
        
        # Load CA certificate if provided
        if self.ca_cert_path:
            ssl_context.load_verify_locations(self.ca_cert_path)
        
        # Load client certificate if provided (for mTLS)
        if self.client_cert_path and self.client_key_path:
            ssl_context.load_cert_chain(self.client_cert_path, self.client_key_path)
        
        return ssl_context
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.disconnect()
    
    async def connect(self) -> None:
        """Establish connection to the agent"""
        if self._session:
            return
        
        # Create headers
        headers = {'Content-Type': 'application/json'}
        if self.api_key:
            headers['X-API-Key'] = self.api_key
        
        # Create session with SSL context
        connector = aiohttp.TCPConnector(ssl=self.ssl_context)
        self._session = aiohttp.ClientSession(
            connector=connector,
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=30)
        )
    
    async def disconnect(self) -> None:
        """Close connection to the agent"""
        if self._session:
            await self._session.close()
            self._session = None
    
    async def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make HTTP request to the agent"""
        if not self._session:
            await self.connect()
        
        url = urljoin(self.agent_url, endpoint)
        
        try:
            async with self._session.request(
                method,
                url,
                json=data,
                params=params
            ) as response:
                if response.content_type == 'application/json':
                    result = await response.json()
                else:
                    result = {'text': await response.text()}
                
                if response.status >= 400:
                    raise Exception(f"HTTP {response.status}: {result}")
                
                return result
                
        except Exception as e:
            logger.error(f"Request failed: {e}")
            raise
    
    async def health_check(self) -> Dict[str, Any]:
        """Check agent health status"""
        return await self._request('GET', '/health')
    
    async def get_info(self) -> Dict[str, Any]:
        """Get agent information and capabilities"""
        return await self._request('GET', '/info')
    
    async def execute_command(
        self,
        command: str,
        timeout: int = 300
    ) -> Dict[str, Any]:
        """Execute shell command on the agent"""
        mcp_request = {
            'method': 'tools/call',
            'params': {
                'name': 'execute_shell_command',
                'arguments': {
                    'command': command,
                    'timeout': timeout
                }
            }
        }
        return await self._request('POST', '/mcp', data=mcp_request)
    
    async def read_file(
        self,
        file_path: str,
        encoding: str = 'utf-8'
    ) -> Dict[str, Any]:
        """Read file contents from the agent"""
        mcp_request = {
            'method': 'tools/call',
            'params': {
                'name': 'read_file',
                'arguments': {
                    'file_path': file_path,
                    'encoding': encoding
                }
            }
        }
        return await self._request('POST', '/mcp', data=mcp_request)
    
    async def write_file(
        self,
        file_path: str,
        content: str,
        encoding: str = 'utf-8'
    ) -> Dict[str, Any]:
        """Write content to file on the agent"""
        mcp_request = {
            'method': 'tools/call',
            'params': {
                'name': 'write_file',
                'arguments': {
                    'file_path': file_path,
                    'content': content,
                    'encoding': encoding
                }
            }
        }
        return await self._request('POST', '/mcp', data=mcp_request)
    
    async def list_directory(
        self,
        directory_path: str = '/'
    ) -> Dict[str, Any]:
        """List directory contents on the agent"""
        mcp_request = {
            'method': 'tools/call',
            'params': {
                'name': 'list_directory',
                'arguments': {
                    'directory_path': directory_path
                }
            }
        }
        return await self._request('POST', '/mcp', data=mcp_request)
    
    async def get_system_metrics(self) -> Dict[str, Any]:
        """Get system metrics from the agent"""
        mcp_request = {
            'method': 'tools/call',
            'params': {
                'name': 'get_system_metrics',
                'arguments': {}
            }
        }
        return await self._request('POST', '/mcp', data=mcp_request)
    
    async def get_process_list(self) -> Dict[str, Any]:
        """Get process list from the agent"""
        mcp_request = {
            'method': 'tools/call',
            'params': {
                'name': 'get_process_list',
                'arguments': {}
            }
        }
        return await self._request('POST', '/mcp', data=mcp_request)
    
    async def analyze_log_file(
        self,
        log_path: str,
        lines: int = 100
    ) -> Dict[str, Any]:
        """Analyze log file on the agent"""
        mcp_request = {
            'method': 'tools/call',
            'params': {
                'name': 'analyze_log_file',
                'arguments': {
                    'log_path': log_path,
                    'lines': lines
                }
            }
        }
        return await self._request('POST', '/mcp', data=mcp_request)
    
    async def get_ca_certificate(self) -> str:
        """Get CA certificate from the agent"""
        result = await self._request('GET', '/api/v1/ca-certificate')
        return result.get('text', '')


# Convenience function for quick connections
async def connect_to_agent(
    agent_url: str,
    api_key: Optional[str] = None,
    **kwargs
) -> VMAgentClient:
    """
    Convenience function to create and connect to a VM agent
    
    Args:
        agent_url: Agent URL
        api_key: API key for authentication
        **kwargs: Additional arguments for VMAgentClient
    
    Returns:
        Connected VMAgentClient instance
    """
    client = VMAgentClient(agent_url, api_key, **kwargs)
    await client.connect()
    return client 