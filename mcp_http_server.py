from aiohttp import web, WSMsgType
import aiohttp
import json
import logging
from datetime import datetime
import asyncio
from typing import Dict, Any
import traceback

from server import VMAgent

logger = logging.getLogger(__name__)

class MCPHTTPServer:
    def __init__(self, vm_agent: VMAgent, config: Dict[str, Any]):
        self.vm_agent = vm_agent
        self.config = config
        self.app = web.Application()
        self.setup_routes()
        
    def setup_routes(self):
        """Setup HTTP routes"""
        # MCP JSON-RPC endpoint
        self.app.router.add_post('/mcp', self.handle_mcp_request)
        
        # WebSocket endpoint for real-time communication
        self.app.router.add_get('/mcp/ws', self.handle_websocket)
        
        # Health check endpoint
        self.app.router.add_get('/health', self.health_check)
        
        # Info endpoint
        self.app.router.add_get('/info', self.get_info)
        
        # CORS support
        self.app.router.add_options('/{path:.*}', self.handle_options)
        
        # Add middleware
        self.app.middlewares.append(self.cors_middleware)
        self.app.middlewares.append(self.logging_middleware)
    
    @web.middleware
    async def cors_middleware(self, request, handler):
        """Handle CORS"""
        if request.method == 'OPTIONS':
            return web.Response(
                headers={
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
                    'Access-Control-Allow-Headers': 'Content-Type, Authorization'
                }
            )
        
        response = await handler(request)
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response
    
    @web.middleware
    async def logging_middleware(self, request, handler):
        """Request logging middleware"""
        start_time = datetime.now()
        
        try:
            response = await handler(request)
            duration = (datetime.now() - start_time).total_seconds()
            
            logger.info(f"{request.method} {request.path} - {response.status} ({duration:.3f}s)")
            return response
            
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            logger.error(f"{request.method} {request.path} - ERROR ({duration:.3f}s): {e}")
            raise
    
    async def handle_mcp_request(self, request):
        """Handle MCP JSON-RPC requests"""
        try:
            # Parse JSON request
            data = await request.json()
            logger.debug(f"MCP Request: {data}")
            
            # Validate JSON-RPC format
            if not isinstance(data, dict) or 'jsonrpc' not in data:
                return web.json_response({
                    'jsonrpc': '2.0',
                    'error': {
                        'code': -32600,
                        'message': 'Invalid Request'
                    },
                    'id': data.get('id')
                }, status=400)
            
            # Handle different MCP methods
            method = data.get('method')
            params = data.get('params', {})
            request_id = data.get('id')
            
            if method == 'tools/list':
                # List available tools
                tools = await self.vm_agent.server._tool_list_handler()
                response = {
                    'jsonrpc': '2.0',
                    'result': {'tools': [tool.model_dump() for tool in tools]},
                    'id': request_id
                }
                
            elif method == 'tools/call':
                # Call a tool
                tool_name = params.get('name')
                arguments = params.get('arguments', {})
                
                if not tool_name:
                    return web.json_response({
                        'jsonrpc': '2.0',
                        'error': {
                            'code': -32602,
                            'message': 'Invalid params: missing tool name'
                        },
                        'id': request_id
                    }, status=400)
                
                # Execute tool
                result = await self.vm_agent.server._tool_call_handler(tool_name, arguments)
                
                response = {
                    'jsonrpc': '2.0',
                    'result': {
                        'content': [content.model_dump() for content in result]
                    },
                    'id': request_id
                }
                
            else:
                # Unknown method
                response = {
                    'jsonrpc': '2.0',
                    'error': {
                        'code': -32601,
                        'message': f'Method not found: {method}'
                    },
                    'id': request_id
                }
            
            logger.debug(f"MCP Response: {response}")
            return web.json_response(response)
            
        except json.JSONDecodeError:
            return web.json_response({
                'jsonrpc': '2.0',
                'error': {
                    'code': -32700,
                    'message': 'Parse error'
                },
                'id': None
            }, status=400)
            
        except Exception as e:
            logger.error(f"MCP request handling failed: {e}")
            logger.error(traceback.format_exc())
            
            return web.json_response({
                'jsonrpc': '2.0',
                'error': {
                    'code': -32603,
                    'message': f'Internal error: {str(e)}'
                },
                'id': data.get('id') if 'data' in locals() else None
            }, status=500)
    
    async def handle_websocket(self, request):
        """Handle WebSocket connections for real-time communication"""
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        
        logger.info("WebSocket connection established")
        
        try:
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    try:
                        data = json.loads(msg.data)
                        # Handle WebSocket MCP requests similarly to HTTP
                        # For now, just echo back
                        await ws.send_str(json.dumps({
                            'type': 'response',
                            'data': data,
                            'timestamp': datetime.now().isoformat()
                        }))
                    except json.JSONDecodeError:
                        await ws.send_str(json.dumps({
                            'type': 'error',
                            'message': 'Invalid JSON'
                        }))
                        
                elif msg.type == WSMsgType.ERROR:
                    logger.error(f"WebSocket error: {ws.exception()}")
                    
        except Exception as e:
            logger.error(f"WebSocket handling failed: {e}")
        finally:
            logger.info("WebSocket connection closed")
        
        return ws
    
    async def health_check(self, request):
        """Health check endpoint"""
        return web.json_response({
            'status': 'healthy',
            'vm_id': self.vm_agent.vm_id,
            'timestamp': datetime.now().isoformat(),
            'uptime': 'TODO',  # Could add uptime tracking
            'tools_enabled': list(self.vm_agent.tools.keys())
        })
    
    async def get_info(self, request):
        """Get VM agent information"""
        return web.json_response({
            'vm_id': self.vm_agent.vm_id,
            'name': self.vm_agent.config['agent']['name'],
            'version': self.vm_agent.config['agent'].get('version', '1.0.0'),
            'tools': list(self.vm_agent.tools.keys()),
            'config': {
                'server': self.vm_agent.config['server'],
                # Don't expose sensitive config
            }
        })
    
    async def handle_options(self, request):
        """Handle OPTIONS requests for CORS"""
        return web.Response(
            headers={
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type, Authorization'
            }
        )
    
    async def start_server(self):
        """Start the HTTP server"""
        host = self.config['server']['host']
        port = self.config['server']['port']
        
        runner = web.AppRunner(self.app)
        await runner.setup()
        
        site = web.TCPSite(runner, host, port)
        await site.start()
        
        logger.info(f"MCP HTTP Server started on {host}:{port}")
        return runner

# Main entry point
async def main():
    """Main entry point for the VM agent"""
    # Initialize VM agent
    config_path = os.environ.get('AGENT_CONFIG', 'config/agent_config.yaml')
    vm_agent = VMAgent(config_path)
    
    # Create HTTP server
    http_server = MCPHTTPServer(vm_agent, vm_agent.config)
    runner = await http_server.start_server()
    
    logger.info(f"VM Agent {vm_agent.vm_id} is running and ready to accept requests")
    
    try:
        # Keep the server running
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down VM Agent...")
    finally:
        await runner.cleanup()
        logger.info("VM Agent stopped")

if __name__ == "__main__":
    asyncio.run(main())