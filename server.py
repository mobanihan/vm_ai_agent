#!/usr/bin/env python3

import asyncio
import json
import os
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
import yaml
import sys
from pathlib import Path

# Add the current directory to Python path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import MCP FastMCP server
from mcp.server.fastmcp import FastMCP

# Import our tool implementations
from tools.shell_executor import ShellExecutor
from tools.file_manager import FileManager
from tools.system_monitor import SystemMonitor
from tools.log_analyzer import LogAnalyzer

# Import aiohttp for HTTP server
from aiohttp import web
import aiohttp_cors

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/vm-agent.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class VMAgentServer:
    def __init__(self, config_path: str = "config/agent_config.yaml"):
        # Load configuration
        self.config = self._load_config(config_path)
        
        # Get VM identification
        self.vm_id = os.environ.get('VM_ID', self.config['agent']['id'])
        
        # Initialize MCP server using FastMCP
        self.mcp = FastMCP(self.config['agent']['name'])
        
        # Initialize tools
        self.tools = {}
        self._init_tools()
        
        # Register MCP tools
        self._register_mcp_tools()
        
        logger.info(f"VM Agent Server {self.vm_id} initialized")
    
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        try:
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
                'id': 'vm-agent-unknown',
                'name': 'VM Agent',
                'version': '1.0.0'
            },
            'server': {
                'host': '0.0.0.0',
                'port': 8080
            },
            'tools': {
                'shell_executor': {'enabled': True, 'allowed_commands': [], 'restricted_paths': []},
                'file_manager': {'enabled': True, 'allowed_paths': ['/'], 'max_file_size': 10485760},
                'system_monitor': {'enabled': True},
                'log_analyzer': {'enabled': True, 'allowed_log_paths': ['/var/log']}
            }
        }
    
    def _init_tools(self):
        """Initialize tool instances"""
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
    
    def _register_mcp_tools(self):
        """Register tools with FastMCP"""
        
        # Shell execution tools
        if 'shell' in self.tools:
            @self.mcp.tool()
            async def execute_shell(command: str, timeout: int = 30, working_dir: str = "/", 
                                  env_vars: Dict[str, str] = None, capture_output: bool = True) -> Dict[str, Any]:
                """Execute shell commands on this VM"""
                try:
                    result = await self.tools['shell'].execute(
                        command=command,
                        timeout=timeout,
                        working_dir=working_dir,
                        env_vars=env_vars or {},
                        capture_output=capture_output
                    )
                    return self._add_vm_context(result)
                except Exception as e:
                    return self._add_vm_context({"error": str(e)})
            
            @self.mcp.tool()
            async def execute_script(script_content: str, interpreter: str = "bash", 
                                   timeout: int = 30) -> Dict[str, Any]:
                """Execute a script from string content"""
                try:
                    result = await self.tools['shell'].execute_script(
                        script_content=script_content,
                        interpreter=interpreter,
                        timeout=timeout
                    )
                    return self._add_vm_context(result)
                except Exception as e:
                    return self._add_vm_context({"error": str(e)})
        
        # File management tools
        if 'file' in self.tools:
            @self.mcp.tool()
            async def read_file(path: str, max_lines: int = 1000, encoding: str = "utf-8") -> Dict[str, Any]:
                """Read file contents"""
                try:
                    result = await self.tools['file'].read_file(
                        path=path,
                        max_lines=max_lines,
                        encoding=encoding
                    )
                    return self._add_vm_context(result)
                except Exception as e:
                    return self._add_vm_context({"error": str(e)})
            
            @self.mcp.tool()
            async def write_file(path: str, content: str, encoding: str = "utf-8", 
                               mode: str = "w", create_dirs: bool = False) -> Dict[str, Any]:
                """Write content to file"""
                try:
                    result = await self.tools['file'].write_file(
                        path=path,
                        content=content,
                        encoding=encoding,
                        mode=mode,
                        create_dirs=create_dirs
                    )
                    return self._add_vm_context(result)
                except Exception as e:
                    return self._add_vm_context({"error": str(e)})
            
            @self.mcp.tool()
            async def list_directory(path: str, recursive: bool = False, 
                                   include_hidden: bool = False) -> Dict[str, Any]:
                """List directory contents"""
                try:
                    result = await self.tools['file'].list_directory(
                        path=path,
                        recursive=recursive,
                        include_hidden=include_hidden
                    )
                    return self._add_vm_context(result)
                except Exception as e:
                    return self._add_vm_context({"error": str(e)})
        
        # System monitoring tools
        if 'system' in self.tools:
            @self.mcp.tool()
            async def get_system_info(info_type: str = "all") -> Dict[str, Any]:
                """Get system information and metrics
                
                Args:
                    info_type: Type of info to get (cpu, memory, disk, network, system, all)
                """
                try:
                    if info_type == 'cpu':
                        result = await self.tools['system'].get_cpu_info()
                    elif info_type == 'memory':
                        result = await self.tools['system'].get_memory_info()
                    elif info_type == 'disk':
                        result = await self.tools['system'].get_disk_info()
                    elif info_type == 'network':
                        result = await self.tools['system'].get_network_info()
                    elif info_type == 'system':
                        result = await self.tools['system'].get_system_info()
                    else:  # 'all'
                        result = await self.tools['system'].get_all_info()
                    
                    return self._add_vm_context(result)
                except Exception as e:
                    return self._add_vm_context({"error": str(e)})
        
        # Log analysis tools
        if 'logs' in self.tools:
            @self.mcp.tool()
            async def analyze_logs(log_path: str, pattern: str = None, lines: int = 1000,
                                 time_range: str = None, format: str = "auto", 
                                 include_stats: bool = True) -> Dict[str, Any]:
                """Analyze log files with patterns and statistics"""
                try:
                    kwargs = {
                        'log_path': log_path,
                        'lines': lines,
                        'format': format,
                        'include_stats': include_stats
                    }
                    if pattern:
                        kwargs['pattern'] = pattern
                    if time_range:
                        kwargs['time_range'] = time_range
                    
                    result = await self.tools['logs'].analyze_log(**kwargs)
                    return self._add_vm_context(result)
                except Exception as e:
                    return self._add_vm_context({"error": str(e)})
            
            @self.mcp.tool()
            async def tail_log(log_path: str, lines: int = 50) -> Dict[str, Any]:
                """Get last N lines from log file"""
                try:
                    result = await self.tools['logs'].tail_log(log_path=log_path, lines=lines)
                    return self._add_vm_context(result)
                except Exception as e:
                    return self._add_vm_context({"error": str(e)})
            
            @self.mcp.tool()
            async def search_logs(log_path: str, search_term: str, context_lines: int = 2,
                                max_results: int = 100, case_sensitive: bool = False) -> Dict[str, Any]:
                """Search for specific terms in log files"""
                try:
                    result = await self.tools['logs'].search_logs(
                        log_path=log_path,
                        search_term=search_term,
                        context_lines=context_lines,
                        max_results=max_results,
                        case_sensitive=case_sensitive
                    )
                    return self._add_vm_context(result)
                except Exception as e:
                    return self._add_vm_context({"error": str(e)})
    
    def _add_vm_context(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Add VM context to results"""
        if isinstance(result, dict):
            result["vm_id"] = self.vm_id
            result["vm_name"] = self.config['agent']['name']
            result["timestamp"] = datetime.now().isoformat()
        return result

async def create_http_server(vm_agent_server: VMAgentServer):
    """Create HTTP server to serve MCP over HTTP"""
    app = web.Application()
    
    # Configure CORS
    cors = aiohttp_cors.setup(app, defaults={
        "*": aiohttp_cors.ResourceOptions(
            allow_credentials=True,
            expose_headers="*",
            allow_headers="*",
            allow_methods="*"
        )
    })
    
    async def handle_health(request):
        """Health check endpoint"""
        return web.json_response({
            'status': 'healthy',
            'vm_id': vm_agent_server.vm_id,
            'timestamp': datetime.now().isoformat(),
            'tools_enabled': list(vm_agent_server.tools.keys())
        })
    
    async def handle_info(request):
        """VM information endpoint"""
        return web.json_response({
            'vm_id': vm_agent_server.vm_id,
            'name': vm_agent_server.config['agent']['name'],
            'version': vm_agent_server.config['agent'].get('version', '1.0.0'),
            'tools': list(vm_agent_server.tools.keys())
        })
    
    # Add routes
    app.router.add_get('/health', handle_health)
    app.router.add_get('/info', handle_info)
    
    # Mount MCP server - this creates the /mcp endpoint automatically
    # We'll serve the FastMCP app directly since it handles HTTP/JSON-RPC
    app.router.add_route('*', '/mcp', lambda request: handle_mcp_request(request, vm_agent_server))
    
    added_routes = set()
    
    # Add CORS to all routes
    # for route in list(app.router.routes()):
    #     if route not in added_routes:
    #         cors.add(route)
    #         added_routes.add(route)
            
    return app

async def handle_mcp_request(request, vm_agent_server):
    """Handle MCP requests by forwarding to FastMCP"""
    try:
        # Get request data
        if request.method == 'POST':
            data = await request.json()
        else:
            data = dict(request.query)
        
        # For now, we'll create a simple JSON-RPC handler
        # This is a simplified version - in production you'd want full MCP protocol support
        
        if request.method == 'POST' and 'method' in data:
            method = data.get('method')
            params = data.get('params', {})
            request_id = data.get('id')
            
            if method == 'tools/list':
                # List available tools
                tools_info = []
                
                if 'shell' in vm_agent_server.tools:
                    tools_info.extend([
                        {
                            "name": "execute_shell",
                            "description": "Execute shell commands on this VM",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "command": {"type": "string", "description": "Shell command to execute"},
                                    "timeout": {"type": "number", "default": 30},
                                    "working_dir": {"type": "string", "default": "/"},
                                    "env_vars": {"type": "object"},
                                    "capture_output": {"type": "boolean", "default": True}
                                },
                                "required": ["command"]
                            }
                        },
                        {
                            "name": "execute_script",
                            "description": "Execute a script from string content",
                            "inputSchema": {
                                "type": "object", 
                                "properties": {
                                    "script_content": {"type": "string", "description": "Script content"},
                                    "interpreter": {"type": "string", "default": "bash"},
                                    "timeout": {"type": "number", "default": 30}
                                },
                                "required": ["script_content"]
                            }
                        }
                    ])
                
                if 'file' in vm_agent_server.tools:
                    tools_info.extend([
                        {
                            "name": "read_file",
                            "description": "Read file contents",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "path": {"type": "string", "description": "File path"},
                                    "max_lines": {"type": "number", "default": 1000},
                                    "encoding": {"type": "string", "default": "utf-8"}
                                },
                                "required": ["path"]
                            }
                        },
                        {
                            "name": "write_file", 
                            "description": "Write content to file",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "path": {"type": "string", "description": "File path"},
                                    "content": {"type": "string", "description": "Content to write"},
                                    "encoding": {"type": "string", "default": "utf-8"},
                                    "mode": {"type": "string", "default": "w"},
                                    "create_dirs": {"type": "boolean", "default": False}
                                },
                                "required": ["path", "content"]
                            }
                        },
                        {
                            "name": "list_directory",
                            "description": "List directory contents", 
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "path": {"type": "string", "description": "Directory path"},
                                    "recursive": {"type": "boolean", "default": False},
                                    "include_hidden": {"type": "boolean", "default": False}
                                },
                                "required": ["path"]
                            }
                        }
                    ])
                
                if 'system' in vm_agent_server.tools:
                    tools_info.append({
                        "name": "get_system_info",
                        "description": "Get system information and metrics",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "info_type": {
                                    "type": "string",
                                    "enum": ["cpu", "memory", "disk", "network", "system", "all"],
                                    "default": "all"
                                }
                            }
                        }
                    })
                
                if 'logs' in vm_agent_server.tools:
                    tools_info.extend([
                        {
                            "name": "analyze_logs",
                            "description": "Analyze log files with patterns and statistics",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "log_path": {"type": "string", "description": "Path to log file"},
                                    "pattern": {"type": "string", "description": "Pattern to search for"},
                                    "lines": {"type": "number", "default": 1000},
                                    "time_range": {"type": "string", "description": "Time range (e.g., '1h', '24h')"},
                                    "format": {"type": "string", "default": "auto"},
                                    "include_stats": {"type": "boolean", "default": True}
                                },
                                "required": ["log_path"]
                            }
                        },
                        {
                            "name": "tail_log",
                            "description": "Get last N lines from log file",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "log_path": {"type": "string", "description": "Path to log file"},
                                    "lines": {"type": "number", "default": 50}
                                },
                                "required": ["log_path"]
                            }
                        },
                        {
                            "name": "search_logs", 
                            "description": "Search for specific terms in log files",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "log_path": {"type": "string", "description": "Path to log file"},
                                    "search_term": {"type": "string", "description": "Term to search for"},
                                    "context_lines": {"type": "number", "default": 2},
                                    "max_results": {"type": "number", "default": 100},
                                    "case_sensitive": {"type": "boolean", "default": False}
                                },
                                "required": ["log_path", "search_term"]
                            }
                        }
                    ])
                
                response = {
                    'jsonrpc': '2.0',
                    'result': {'tools': tools_info},
                    'id': request_id
                }
                
            elif method == 'tools/call':
                # Call a tool
                tool_name = params.get('name')
                arguments = params.get('arguments', {})
                
                if not tool_name:
                    return web.json_response({
                        'jsonrpc': '2.0',
                        'error': {'code': -32602, 'message': 'Invalid params: missing tool name'},
                        'id': request_id
                    }, status=400)
                
                # Execute the tool
                try:
                    result = None
                    
                    if tool_name == "execute_shell" and 'shell' in vm_agent_server.tools:
                        result = await vm_agent_server.tools['shell'].execute(**arguments)
                    elif tool_name == "execute_script" and 'shell' in vm_agent_server.tools:
                        result = await vm_agent_server.tools['shell'].execute_script(**arguments)
                    elif tool_name == "read_file" and 'file' in vm_agent_server.tools:
                        result = await vm_agent_server.tools['file'].read_file(**arguments)
                    elif tool_name == "write_file" and 'file' in vm_agent_server.tools:
                        result = await vm_agent_server.tools['file'].write_file(**arguments)
                    elif tool_name == "list_directory" and 'file' in vm_agent_server.tools:
                        result = await vm_agent_server.tools['file'].list_directory(**arguments)
                    elif tool_name == "get_system_info" and 'system' in vm_agent_server.tools:
                        info_type = arguments.get('info_type', 'all')
                        if info_type == 'cpu':
                            result = await vm_agent_server.tools['system'].get_cpu_info()
                        elif info_type == 'memory':
                            result = await vm_agent_server.tools['system'].get_memory_info()
                        elif info_type == 'disk':
                            result = await vm_agent_server.tools['system'].get_disk_info()
                        elif info_type == 'network':
                            result = await vm_agent_server.tools['system'].get_network_info()
                        elif info_type == 'system':
                            result = await vm_agent_server.tools['system'].get_system_info()
                        else:
                            result = await vm_agent_server.tools['system'].get_all_info()
                    elif tool_name == "analyze_logs" and 'logs' in vm_agent_server.tools:
                        result = await vm_agent_server.tools['logs'].analyze_log(**arguments)
                    elif tool_name == "tail_log" and 'logs' in vm_agent_server.tools:
                        result = await vm_agent_server.tools['logs'].tail_log(**arguments)
                    elif tool_name == "search_logs" and 'logs' in vm_agent_server.tools:
                        result = await vm_agent_server.tools['logs'].search_logs(**arguments)
                    else:
                        raise ValueError(f"Unknown tool: {tool_name}")
                    
                    # Add VM context
                    result = vm_agent_server._add_vm_context(result)
                    
                    response = {
                        'jsonrpc': '2.0',
                        'result': {
                            'content': [{'type': 'text', 'text': json.dumps(result, default=str)}]
                        },
                        'id': request_id
                    }
                    
                except Exception as e:
                    logger.error(f"Tool execution failed: {e}")
                    response = {
                        'jsonrpc': '2.0',
                        'error': {'code': -32603, 'message': f'Internal error: {str(e)}'},
                        'id': request_id
                    }
            else:
                response = {
                    'jsonrpc': '2.0',
                    'error': {'code': -32601, 'message': f'Method not found: {method}'},
                    'id': request_id
                }
            
            return web.json_response(response)
        else:
            return web.json_response({
                'jsonrpc': '2.0',
                'error': {'code': -32600, 'message': 'Invalid Request'},
                'id': None
            }, status=400)
            
    except json.JSONDecodeError:
        return web.json_response({
            'jsonrpc': '2.0',
            'error': {'code': -32700, 'message': 'Parse error'},
            'id': None
        }, status=400)
    except Exception as e:
        logger.error(f"MCP request handling failed: {e}")
        return web.json_response({
            'jsonrpc': '2.0',
            'error': {'code': -32603, 'message': f'Internal error: {str(e)}'},
            'id': None
        }, status=500)

async def main():
    """Main entry point"""
    try:
        # Initialize VM agent server
        config_path = os.environ.get('AGENT_CONFIG', 'config/agent_config.yaml')
        vm_agent_server = VMAgentServer(config_path)
        
        # Create HTTP server
        http_app = await create_http_server(vm_agent_server)
        
        # Start HTTP server
        host = vm_agent_server.config['server']['host']
        port = vm_agent_server.config['server']['port']
        
        runner = web.AppRunner(http_app)
        await runner.setup()
        
        site = web.TCPSite(runner, host, port)
        await site.start()
        
        logger.info(f"VM Agent Server {vm_agent_server.vm_id} started on {host}:{port}")
        logger.info("Server is ready to accept MCP requests")
        
        # Keep the server running
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("Shutting down VM Agent Server...")
        finally:
            await runner.cleanup()
            logger.info("VM Agent Server stopped")
            
    except Exception as e:
        logger.error(f"Failed to start VM Agent Server: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())