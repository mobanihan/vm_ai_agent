from mcp.server import Server
from mcp.types import Tool, TextContent, ImageContent, EmbeddedResource
import asyncio
import json
import os
import logging
from datetime import datetime
from typing import Dict, Any, List
import yaml
from pathlib import Path

# Import our tools
from tools.shell_executor import ShellExecutor
from tools.file_manager import FileManager
from tools.system_monitor import SystemMonitor
from tools.log_analyzer import LogAnalyzer

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

class VMAgent:
    def __init__(self, config_path: str = "config/agent_config.yaml"):
        # Load configuration
        self.config = self._load_config(config_path)
        
        # Initialize MCP server
        self.server = Server(self.config['agent']['name'])
        
        # Get VM identification
        self.vm_id = os.environ.get('VM_ID', self.config['agent']['id'])
        
        # Initialize tools
        self._init_tools()
        
        # Setup MCP handlers
        self._setup_mcp_handlers()
        
        logger.info(f"VM Agent {self.vm_id} initialized")
    
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        try:
            # Expand environment variables in config path
            config_path = os.path.expandvars(config_path)
            
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
            # Return default config
            return {
                'agent': {'id': 'unknown', 'name': 'VM Agent'},
                'server': {'host': '0.0.0.0', 'port': 8080},
                'tools': {
                    'shell_executor': {'enabled': True},
                    'file_manager': {'enabled': True},
                    'system_monitor': {'enabled': True},
                    'log_analyzer': {'enabled': True}
                }
            }
    
    def _init_tools(self):
        """Initialize tool instances"""
        self.tools = {}
        
        tools_config = self.config.get('tools', {})
        
        # Initialize Shell Executor
        if tools_config.get('shell_executor', {}).get('enabled', True):
            self.tools['shell'] = ShellExecutor(tools_config['shell_executor'])
            logger.info("Shell Executor tool enabled")
        
        # Initialize File Manager
        if tools_config.get('file_manager', {}).get('enabled', True):
            self.tools['file'] = FileManager(tools_config['file_manager'])
            logger.info("File Manager tool enabled")
        
        # Initialize System Monitor
        if tools_config.get('system_monitor', {}).get('enabled', True):
            self.tools['system'] = SystemMonitor(tools_config['system_monitor'])
            logger.info("System Monitor tool enabled")
        
        # Initialize Log Analyzer
        if tools_config.get('log_analyzer', {}).get('enabled', True):
            self.tools['logs'] = LogAnalyzer(tools_config['log_analyzer'])
            logger.info("Log Analyzer tool enabled")
    
    def _setup_mcp_handlers(self):
        """Setup MCP protocol handlers"""
        
        @self.server.list_tools()
        async def list_tools() -> List[Tool]:
            """List available tools"""
            available_tools = []
            
            # Shell execution tools
            if 'shell' in self.tools:
                available_tools.extend([
                    Tool(
                        name="execute_shell",
                        description="Execute shell commands on this VM",
                        inputSchema={
                            "type": "object",
                            "properties": {
                                "command": {"type": "string", "description": "Shell command to execute"},
                                "timeout": {"type": "number", "default": 30, "description": "Timeout in seconds"},
                                "working_dir": {"type": "string", "default": "/", "description": "Working directory"},
                                "env_vars": {"type": "object", "description": "Environment variables"},
                                "capture_output": {"type": "boolean", "default": True}
                            },
                            "required": ["command"]
                        }
                    ),
                    Tool(
                        name="execute_script",
                        description="Execute a script from string content",
                        inputSchema={
                            "type": "object",
                            "properties": {
                                "script_content": {"type": "string", "description": "Script content to execute"},
                                "interpreter": {"type": "string", "default": "bash", "description": "Script interpreter"}
                            },
                            "required": ["script_content"]
                        }
                    )
                ])
            
            # File management tools
            if 'file' in self.tools:
                available_tools.extend([
                    Tool(
                        name="read_file",
                        description="Read file contents",
                        inputSchema={
                            "type": "object",
                            "properties": {
                                "path": {"type": "string", "description": "File path to read"},
                                "max_lines": {"type": "number", "default": 1000, "description": "Maximum lines to read"},
                                "encoding": {"type": "string", "default": "utf-8", "description": "File encoding"}
                            },
                            "required": ["path"]
                        }
                    ),
                    Tool(
                        name="write_file",
                        description="Write content to file",
                        inputSchema={
                            "type": "object",
                            "properties": {
                                "path": {"type": "string", "description": "File path to write"},
                                "content": {"type": "string", "description": "Content to write"},
                                "encoding": {"type": "string", "default": "utf-8"},
                                "mode": {"type": "string", "default": "w", "description": "Write mode (w, a, etc.)"},
                                "create_dirs": {"type": "boolean", "default": False}
                            },
                            "required": ["path", "content"]
                        }
                    ),
                    Tool(
                        name="list_directory",
                        description="List directory contents",
                        inputSchema={
                            "type": "object",
                            "properties": {
                                "path": {"type": "string", "description": "Directory path to list"},
                                "recursive": {"type": "boolean", "default": False},
                                "include_hidden": {"type": "boolean", "default": False}
                            },
                            "required": ["path"]
                        }
                    )
                ])
            
            # System monitoring tools
            if 'system' in self.tools:
                available_tools.extend([
                    Tool(
                        name="get_system_info",
                        description="Get system information and metrics",
                        inputSchema={
                            "type": "object",
                            "properties": {
                                "info_type": {
                                    "type": "string",
                                    "enum": ["cpu", "memory", "disk", "network", "system", "all"],
                                    "default": "all",
                                    "description": "Type of system information to retrieve"
                                }
                            }
                        }
                    )
                ])
            
            # Log analysis tools
            if 'logs' in self.tools:
                available_tools.extend([
                    Tool(
                        name="analyze_logs",
                        description="Analyze log files with patterns and statistics",
                        inputSchema={
                            "type": "object",
                            "properties": {
                                "log_path": {"type": "string", "description": "Path to log file"},
                                "pattern": {"type": "string", "description": "Pattern to search for (regex or string)"},
                                "lines": {"type": "number", "default": 1000, "description": "Number of lines to analyze"},
                                "time_range": {"type": "string", "description": "Time range (e.g., '1h', '24h', '7d')"},
                                "format": {"type": "string", "default": "auto", "description": "Log format (auto, apache, nginx, syslog)"},
                                "include_stats": {"type": "boolean", "default": True}
                            },
                            "required": ["log_path"]
                        }
                    ),
                    Tool(
                        name="tail_log",
                        description="Get last N lines from log file",
                        inputSchema={
                            "type": "object",
                            "properties": {
                                "log_path": {"type": "string", "description": "Path to log file"},
                                "lines": {"type": "number", "default": 50, "description": "Number of lines to return"}
                            },
                            "required": ["log_path"]
                        }
                    ),
                    Tool(
                        name="search_logs",
                        description="Search for specific terms in log files",
                        inputSchema={
                            "type": "object",
                            "properties": {
                                "log_path": {"type": "string", "description": "Path to log file"},
                                "search_term": {"type": "string", "description": "Term to search for"},
                                "context_lines": {"type": "number", "default": 2, "description": "Context lines around matches"},
                                "max_results": {"type": "number", "default": 100, "description": "Maximum number of results"},
                                "case_sensitive": {"type": "boolean", "default": False}
                            },
                            "required": ["log_path", "search_term"]
                        }
                    )
                ])
            
            return available_tools
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict) -> List[TextContent]:
            """Handle tool calls"""
            try:
                logger.info(f"Tool call: {name} with args: {arguments}")
                
                # Add VM ID to all responses
                def add_vm_context(result: dict) -> dict:
                    if isinstance(result, dict):
                        result["vm_id"] = self.vm_id
                        result["vm_name"] = self.config['agent']['name']
                    return result
                
                # Route to appropriate tool
                if name == "execute_shell" and 'shell' in self.tools:
                    result = await self.tools['shell'].execute(**arguments)
                    result = add_vm_context(result)
                    
                elif name == "execute_script" and 'shell' in self.tools:
                    result = await self.tools['shell'].execute_script(**arguments)
                    result = add_vm_context(result)
                    
                elif name == "read_file" and 'file' in self.tools:
                    result = await self.tools['file'].read_file(**arguments)
                    result = add_vm_context(result)
                    
                elif name == "write_file" and 'file' in self.tools:
                    result = await self.tools['file'].write_file(**arguments)
                    result = add_vm_context(result)
                    
                elif name == "list_directory" and 'file' in self.tools:
                    result = await self.tools['file'].list_directory(**arguments)
                    result = add_vm_context(result)
                    
                elif name == "get_system_info" and 'system' in self.tools:
                    info_type = arguments.get('info_type', 'all')
                    
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
                    
                    result = add_vm_context(result)
                    
                elif name == "analyze_logs" and 'logs' in self.tools:
                    result = await self.tools['logs'].analyze_log(**arguments)
                    result = add_vm_context(result)
                    
                elif name == "tail_log" and 'logs' in self.tools:
                    result = await self.tools['logs'].tail_log(**arguments)
                    result = add_vm_context(result)
                    
                elif name == "search_logs" and 'logs' in self.tools:
                    result = await self.tools['logs'].search_logs(**arguments)
                    result = add_vm_context(result)
                    
                else:
                    raise ValueError(f"Unknown tool: {name}")
                
                # Format response
                response_text = json.dumps(result, indent=2, default=str)
                return [TextContent(type="text", text=response_text)]
                
            except Exception as e:
                logger.error(f"Tool execution failed: {e}")
                error_response = {
                    "vm_id": self.vm_id,
                    "error": str(e),
                    "tool": name,
                    "arguments": arguments,
                    "timestamp": datetime.now().isoformat()
                }
                return [TextContent(type="text", text=json.dumps(error_response, indent=2))]
    
    def get_server(self):
        """Get the MCP server instance"""
        return self.server