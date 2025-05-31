#!/usr/bin/env python3
"""
VM Agent Server Module

Production-ready VM agent server with MCP protocol support, 
multi-tenant isolation, and comprehensive security features.
"""

import asyncio
import json
import os
import logging
import sys
from datetime import datetime
from typing import Dict, Any, List, Optional, Union
from pathlib import Path
import yaml
import signal

# Import MCP FastMCP server
try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    raise ImportError("MCP library is required. Install with: pip install mcp")

# Import our tool implementations
from .tools import (
    ShellExecutor,
    FileManager, 
    SystemMonitor,
    LogAnalyzer,
    SecurityManager,
    WebSocketCommandHandler,
    TenantManager,
)

# Import aiohttp for HTTP server
from aiohttp import web
import aiohttp_cors
import ssl
from cryptography import x509
from cryptography.hazmat.backends import default_backend

# Configure logging
logger = logging.getLogger(__name__)


class VMAgentServer:
    """
    Production-ready VM Agent Server
    
    Provides secure, multi-tenant VM management capabilities with:
    - MCP protocol support
    - Certificate-based authentication
    - Real-time WebSocket communication
    - Comprehensive tool suite
    - Security isolation
    """
    
    def __init__(self, config_path: Optional[str] = None, **kwargs):
        """
        Initialize VM Agent Server
        
        Args:
            config_path: Path to configuration file
            **kwargs: Additional configuration overrides
        """
        # Load configuration
        self.config = self._load_config(config_path or "config/agent_config.yaml")
        
        # Apply any configuration overrides
        if kwargs:
            self._update_config(self.config, kwargs)
        
        # Initialize security manager first
        self.security_manager = SecurityManager()
        
        # Try to load existing credentials
        self._credentials_loaded = False
        
        # Get VM identification
        self.vm_id = os.environ.get('VM_ID', self.config['agent']['id'])
        
        # Initialize tenant manager
        self.tenant_manager = TenantManager()
        
        # Initialize MCP server using FastMCP
        self.mcp = FastMCP(self.config['agent']['name'])
        
        # Initialize tools
        self.tools: Dict[str, Any] = {}
        self._init_tools()
        
        # Register MCP tools
        self._register_mcp_tools()
        
        # Initialize WebSocket handler if orchestrator URL is configured
        # Note: We'll initialize this after loading credentials
        self.ws_handler: Optional[WebSocketCommandHandler] = None
        
        # Server state
        self._app: Optional[web.Application] = None
        self._runner: Optional[web.AppRunner] = None
        self._site: Optional[web.TCPSite] = None
        self._running = False
        
        logger.info(f"VM Agent Server {self.vm_id} initialized")
    
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from YAML file with environment variable substitution"""
        try:
            # Try to load from package resources first
            if not os.path.isabs(config_path):
                package_config = Path(__file__).parent / config_path
                if package_config.exists():
                    config_path = str(package_config)
            
            # Expand environment variables in config path
            config_path = os.path.expandvars(config_path)
            
            if not os.path.exists(config_path):
                logger.warning(f"Config file not found: {config_path}, using defaults")
                return self._get_default_config()
            
            with open(config_path, 'r') as f:
                config_content = f.read()
            
            # Replace environment variables in config content
            import re
            config_content = re.sub(
                r'\$\{([^}]+)\}',
                lambda m: os.environ.get(m.group(1), m.group(0)),
                config_content
            )
            
            config = yaml.safe_load(config_content)
            return config
            
        except Exception as e:
            logger.error(f"Failed to load config from {config_path}: {e}")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration"""
        return {
            'agent': {
                'id': f'vm-agent-{os.environ.get("HOSTNAME", "unknown")}',
                'name': 'VM Agent',
                'version': '1.0.0'
            },
            'server': {
                'host': '0.0.0.0',
                'port': 8080,
                'ssl': {
                    'enabled': True,
                    'cert_file': '/opt/vm-agent/security/server.crt',
                    'key_file': '/opt/vm-agent/security/server.key'
                }
            },
            'orchestrator': {
                'url': os.environ.get('ORCHESTRATOR_URL'),
                'heartbeat_interval': 30,
                'command_poll_interval': 5
            },
            'security': {
                'enabled': True,
                'mtls': True,
                'api_key_required': True
            },
            'tools': {
                'shell_executor': {'enabled': True, 'timeout': 300},
                'file_manager': {'enabled': True, 'max_file_size': '100MB'},
                'system_monitor': {'enabled': True, 'interval': 60},
                'log_analyzer': {'enabled': True, 'max_lines': 10000}
            },
            'logging': {
                'level': 'INFO',
                'file': '/var/log/vm-agent.log',
                'max_size': '100MB',
                'backup_count': 5
            }
        }
    
    def _update_config(self, config: Dict[str, Any], updates: Dict[str, Any]) -> None:
        """Update configuration with new values"""
        for key, value in updates.items():
            if isinstance(value, dict) and key in config and isinstance(config[key], dict):
                self._update_config(config[key], value)
            else:
                config[key] = value
    
    def _init_tools(self) -> None:
        """Initialize tool instances based on configuration"""
        tools_config = self.config.get('tools', {})
        
        # Initialize Shell Executor
        if tools_config.get('shell_executor', {}).get('enabled', True):
            self.tools['shell'] = ShellExecutor(tools_config.get('shell_executor', {}))
            logger.info("Shell Executor tool enabled")
        
        # Initialize File Manager
        if tools_config.get('file_manager', {}).get('enabled', True):
            self.tools['file'] = FileManager(tools_config.get('file_manager', {}))
            logger.info("File Manager tool enabled")
        
        # Initialize System Monitor
        if tools_config.get('system_monitor', {}).get('enabled', True):
            self.tools['system'] = SystemMonitor(tools_config.get('system_monitor', {}))
            logger.info("System Monitor tool enabled")
        
        # Initialize Log Analyzer
        if tools_config.get('log_analyzer', {}).get('enabled', True):
            self.tools['logs'] = LogAnalyzer(tools_config.get('log_analyzer', {}))
            logger.info("Log Analyzer tool enabled")
    
    def _register_mcp_tools(self) -> None:
        """Register tools with FastMCP server"""
        
        # Shell execution tools
        if 'shell' in self.tools:
            @self.mcp.tool()
            async def execute_shell_command(command: str, timeout: int = 300) -> Dict[str, Any]:
                """Execute shell command on the VM"""
                result = await self.tools['shell'].execute_command(command, timeout=timeout)
                return self._add_vm_context(result)
            
            @self.mcp.tool()
            async def get_command_history() -> Dict[str, Any]:
                """Get shell command execution history"""
                result = await self.tools['shell'].get_command_history()
                return self._add_vm_context(result)
        
        # File management tools
        if 'file' in self.tools:
            @self.mcp.tool()
            async def read_file(file_path: str, encoding: str = 'utf-8') -> Dict[str, Any]:
                """Read file contents"""
                result = await self.tools['file'].read_file(file_path, encoding)
                return self._add_vm_context(result)
            
            @self.mcp.tool()
            async def write_file(file_path: str, content: str, encoding: str = 'utf-8') -> Dict[str, Any]:
                """Write content to file"""
                result = await self.tools['file'].write_file(file_path, content, encoding)
                return self._add_vm_context(result)
            
            @self.mcp.tool()
            async def list_directory(directory_path: str) -> Dict[str, Any]:
                """List directory contents"""
                result = await self.tools['file'].list_directory(directory_path)
                return self._add_vm_context(result)
        
        # System monitoring tools
        if 'system' in self.tools:
            @self.mcp.tool()
            async def get_system_metrics() -> Dict[str, Any]:
                """Get current system metrics"""
                result = await self.tools['system'].get_system_metrics()
                return self._add_vm_context(result)
            
            @self.mcp.tool()
            async def get_process_list() -> Dict[str, Any]:
                """Get list of running processes"""
                result = await self.tools['system'].get_process_list()
                return self._add_vm_context(result)
        
        # Log analysis tools
        if 'logs' in self.tools:
            @self.mcp.tool()
            async def analyze_log_file(log_path: str, lines: int = 100) -> Dict[str, Any]:
                """Analyze log file for patterns and errors"""
                result = await self.tools['logs'].analyze_log_file(log_path, lines)
                return self._add_vm_context(result)
    
    def _add_vm_context(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Add VM context information to results"""
        if isinstance(result, dict):
            result.setdefault("vm_id", self.vm_id)
            result.setdefault("vm_name", self.config['agent']['name'])
            result.setdefault("timestamp", datetime.now().isoformat())
        return result
    
    async def create_app(self) -> web.Application:
        """Create and configure the web application"""
        app = web.Application()
        
        # Configure CORS
        cors = aiohttp_cors.setup(app, defaults={
            "*": aiohttp_cors.ResourceOptions(
                allow_credentials=True,
                expose_headers=["X-Request-ID"],
                allow_headers=["Content-Type", "Authorization", "X-VM-ID", "X-API-Key"],
                allow_methods=["GET", "POST", "OPTIONS"]
            )
        })
        
        # Add security middleware
        @web.middleware
        async def auth_middleware(request, handler):
            """Verify API key for protected endpoints"""
            # Skip auth for public endpoints
            if request.path in ['/health', '/api/v1/ca-certificate']:
                return await handler(request)
            
            # Verify API key
            api_key = (
                request.headers.get('X-API-Key') or 
                request.headers.get('Authorization', '').replace('Bearer ', '')
            )
            
            if not self.security_manager.verify_api_key(api_key):
                return web.json_response({'error': 'Unauthorized'}, status=401)
            
            return await handler(request)
        
        app.middlewares.append(auth_middleware)
        
        # Add routes
        app.router.add_get('/health', self._handle_health)
        app.router.add_get('/info', self._handle_info)
        app.router.add_get('/api/v1/ca-certificate', self._handle_ca_certificate)
        app.router.add_post('/mcp', self._handle_mcp_request)
        
        # Add CORS to all routes
        for route in list(app.router.routes()):
            cors.add(route)
        
        return app
    
    async def _handle_health(self, request: web.Request) -> web.Response:
        """Health check endpoint"""
        try:
            tenant_status = "unknown"
            if await self.tenant_manager.load_tenant_config():
                tenant_status = "provisioned"
            
            # Check security status
            security_status = "uninitialized"
            if self.security_manager.is_initialized():
                security_status = "fully_initialized"
            elif self._credentials_loaded:
                security_status = "credentials_loaded"
            
            health_data = {
                "status": "healthy",
                "vm_id": self.vm_id,
                "version": self.config['agent']['version'],
                "tenant_status": tenant_status,
                "security_status": security_status,
                "tools_enabled": list(self.tools.keys()),
                "websocket_connected": self.ws_handler is not None and self.ws_handler._running if self.ws_handler else False,
                "timestamp": datetime.now().isoformat()
            }
            return web.json_response(health_data)
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return web.json_response({
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }, status=500)
    
    async def _handle_info(self, request: web.Request) -> web.Response:
        """Agent information endpoint"""
        info = {
            "agent": self.config['agent'],
            "vm_id": self.vm_id,
            "tools": {name: tool.__class__.__name__ for name, tool in self.tools.items()},
            "tenant": await self.tenant_manager.load_tenant_config(),
            "capabilities": [
                "shell_execution",
                "file_management", 
                "system_monitoring",
                "log_analysis",
                "websocket_communication",
                "mcp_protocol"
            ]
        }
        return web.json_response(info)
    
    async def _handle_ca_certificate(self, request: web.Request) -> web.Response:
        """Get CA certificate for client verification"""
        try:
            ca_cert = self.security_manager.get_ca_certificate()
            return web.Response(text=ca_cert, content_type='application/x-pem-file')
        except FileNotFoundError:
            logger.warning("CA certificate not available yet")
            return web.json_response({
                'error': 'CA certificate not available', 
                'message': 'Agent may not be fully registered yet'
            }, status=404)
        except Exception as e:
            logger.error(f"Failed to get CA certificate: {e}")
            return web.json_response({'error': 'Internal server error'}, status=500)
    
    async def _handle_mcp_request(self, request: web.Request) -> web.Response:
        """Handle MCP protocol requests"""
        try:
            data = await request.json()
            result = await self.mcp.handle_request(data)
            return web.json_response(result)
        except Exception as e:
            logger.error(f"MCP request error: {e}")
            return web.json_response({'error': str(e)}, status=500)
    
    def _create_ssl_context(self) -> Optional[ssl.SSLContext]:
        """Create SSL context for HTTPS server"""
        ssl_config = self.config.get('server', {}).get('ssl', {})
        cert_file = ssl_config.get('cert_file')
        key_file = ssl_config.get('key_file')
        
        # Return None if SSL is not configured or certificates don't exist yet
        if not cert_file or not key_file:
            logger.warning("SSL cert_file and key_file not specified in config")
            return None
        
        if not os.path.exists(cert_file) or not os.path.exists(key_file):
            logger.warning(f"SSL certificates not found: {cert_file}, {key_file}")
            logger.info("Server will start without SSL until certificates are available")
            return None
        
        try:
            ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            ssl_context.load_cert_chain(cert_file, key_file)
            logger.info("SSL context created successfully")
            return ssl_context
        except Exception as e:
            logger.error(f"Failed to create SSL context: {e}")
            return None

    async def register_with_orchestrator(self, provisioning_token: Optional[str] = None) -> bool:
        """Register this agent with the orchestrator"""
        try:
            # First, ensure we have basic credentials
            if not await self._ensure_credentials():
                logger.error("Failed to ensure basic credentials")
                return False
            
            # Initialize WebSocket handler now that we have credentials
            orchestrator_url = self.config.get('orchestrator', {}).get('url')
            if not orchestrator_url:
                logger.error("Orchestrator URL not configured")
                return False
            
            if not self.ws_handler:
                self.ws_handler = WebSocketCommandHandler(
                    self, self.security_manager, orchestrator_url
                )
            
            # Perform registration
            success = await self.ws_handler.register_agent(provisioning_token)
            
            if success:
                logger.info("Successfully registered with orchestrator")
                # Update VM ID from security manager if it changed
                vm_id = self.security_manager.get_vm_id()
                if vm_id and vm_id != self.vm_id:
                    self.vm_id = vm_id
            else:
                logger.error("Failed to register with orchestrator")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to register with orchestrator: {e}")
            return False
    
    async def _ensure_credentials(self) -> bool:
        """Ensure we have the basic credentials needed for operation"""
        try:
            # Try to load existing credentials first
            if await self.security_manager.load_existing_credentials():
                self._credentials_loaded = True
                # Update VM ID from loaded credentials
                vm_id = self.security_manager.get_vm_id()
                if vm_id:
                    self.vm_id = vm_id
                return True
            
            # If no existing credentials, generate basic ones
            logger.info("No existing credentials found, generating new ones...")
            
            # Generate VM ID and API key
            self.security_manager._vm_id = await self.security_manager._get_or_create_vm_id()
            self.security_manager._api_key = await self.security_manager._get_or_create_api_key()
            
            # Update our VM ID
            self.vm_id = self.security_manager._vm_id
            
            self._credentials_loaded = True
            logger.info(f"Generated basic credentials for VM {self.vm_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to ensure credentials: {e}")
            return False

    async def start(self) -> None:
        """Start the VM agent server"""
        if self._running:
            logger.warning("Server is already running")
            return
        
        try:
            # Ensure we have basic credentials before starting
            if not self._credentials_loaded:
                await self._ensure_credentials()
            
            # Create application
            self._app = await self.create_app()
            
            # Create runner
            self._runner = web.AppRunner(self._app)
            await self._runner.setup()
            
            # Configure SSL if enabled and certificates are available
            ssl_context = None
            if self.config.get('server', {}).get('ssl', {}).get('enabled', False):
                ssl_context = self._create_ssl_context()
            
            # Create site
            host = self.config.get('server', {}).get('host', '0.0.0.0')
            port = self.config.get('server', {}).get('port', 8080)
            
            self._site = web.TCPSite(
                self._runner, 
                host, 
                port, 
                ssl_context=ssl_context
            )
            
            await self._site.start()
            self._running = True
            
            # Start WebSocket handler if configured and we have credentials
            if self.ws_handler and self._credentials_loaded:
                await self.ws_handler.start()
            
            protocol = "HTTPS" if ssl_context else "HTTP"
            logger.info(f"VM Agent Server started on {host}:{port} ({protocol})")
            
        except Exception as e:
            logger.error(f"Failed to start server: {e}", exc_info=True)
            await self.stop()
            raise
    
    async def stop(self) -> None:
        """Stop the VM agent server"""
        if not self._running:
            return
        
        try:
            # Stop WebSocket handler
            if self.ws_handler:
                await self.ws_handler.stop()
            
            # Stop web server
            if self._site:
                await self._site.stop()
            
            if self._runner:
                await self._runner.cleanup()
            
            self._running = False
            logger.info("VM Agent Server stopped")
            
        except Exception as e:
            logger.error(f"Error stopping server: {e}")
    
    async def run_forever(self) -> None:
        """Run the server forever until interrupted"""
        try:
            await self.start()
            
            # Set up signal handlers for graceful shutdown
            def signal_handler(signum, frame):
                logger.info(f"Received signal {signum}, shutting down...")
                loop = asyncio.get_event_loop()
                loop.create_task(self.stop())
            
            signal.signal(signal.SIGINT, signal_handler)
            signal.signal(signal.SIGTERM, signal_handler)
            
            # Keep running until stopped
            while self._running:
                await asyncio.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt")
        finally:
            await self.stop()

    def is_ready(self) -> bool:
        """Check if the server is ready to accept requests"""
        return (
            self._credentials_loaded and 
            self.security_manager.get_vm_id() is not None and
            self.security_manager.get_api_key() is not None
        )


async def main() -> None:
    """Main entry point for VM agent server"""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('/var/log/vm-agent.log'),
            logging.StreamHandler()
        ]
    )
    
    # Create and run server
    server = VMAgentServer()
    await server.run_forever()


if __name__ == "__main__":
    asyncio.run(main()) 