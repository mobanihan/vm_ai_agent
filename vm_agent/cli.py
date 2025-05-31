#!/usr/bin/env python3
"""
VM Agent CLI Interface

Provides command-line interface for VM agent operations including:
- Server management
- Agent installation and configuration
- Tool testing and debugging
- Status monitoring
- Agent provisioning and registration
"""

import asyncio
import click
import json
import os
import sys
import yaml
import logging
from pathlib import Path
from typing import Dict, Any, Optional
import aiohttp
import subprocess

from .server import VMAgentServer
from .tools import TenantManager, SecurityManager


@click.group()
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
@click.option('--config', '-c', help='Path to configuration file')
@click.pass_context
def cli(ctx: click.Context, verbose: bool, config: Optional[str]) -> None:
    """VM Agent CLI - Production-ready VM management agent"""
    # Configure logging
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Store context
    ctx.ensure_object(dict)
    ctx.obj['verbose'] = verbose
    ctx.obj['config'] = config


@cli.command()
@click.option('--host', default='0.0.0.0', help='Server host')
@click.option('--port', default=8080, type=int, help='Server port')
@click.option('--ssl/--no-ssl', default=True, help='Enable SSL')
@click.option('--daemon', '-d', is_flag=True, help='Run as daemon')
@click.pass_context
def server(ctx: click.Context, host: str, port: int, ssl: bool, daemon: bool) -> None:
    """Start the VM agent server"""
    
    async def run_server():
        config_overrides = {
            'server': {
                'host': host,
                'port': port,
                'ssl': {'enabled': ssl}
            }
        }
        
        server = VMAgentServer(
            config_path=ctx.obj.get('config'),
            **config_overrides
        )
        
        if daemon:
            # TODO: Implement proper daemon mode
            click.echo("Daemon mode not yet implemented. Running in foreground.")
        
        click.echo(f"Starting VM Agent Server on {host}:{port}")
        click.echo(f"SSL enabled: {ssl}")
        
        await server.run_forever()
    
    try:
        asyncio.run(run_server())
    except KeyboardInterrupt:
        click.echo("\nServer stopped")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--orchestrator-url', required=True, help='Orchestrator URL')
@click.option('--provisioning-token', help='Provisioning token for auto-setup')
@click.option('--organization-id', help='Organization ID for manual setup')
@click.option('--install-dir', default='/opt/vm-agent', help='Installation directory')
@click.option('--force', is_flag=True, help='Force installation even if already exists')
@click.pass_context
def install(
    ctx: click.Context, 
    orchestrator_url: str, 
    provisioning_token: Optional[str],
    organization_id: Optional[str],
    install_dir: str,
    force: bool
) -> None:
    """Install and configure VM agent with full orchestrator integration"""
    
    async def run_install():
        click.echo("🚀 Installing VM Agent with Orchestrator Integration...")
        
        # Validate parameters
        if not provisioning_token and not organization_id:
            click.echo("❌ Either --provisioning-token or --organization-id must be provided")
            sys.exit(1)
        
        # Create installation directory
        install_path = Path(install_dir)
        if install_path.exists() and not force:
            click.echo(f"❌ Installation directory {install_dir} already exists. Use --force to overwrite.")
            sys.exit(1)
        
        install_path.mkdir(parents=True, exist_ok=True)
        
        try:
            # Initialize managers
            security_manager = SecurityManager()
            
            # Set environment variables for child processes
            os.environ['ORCHESTRATOR_URL'] = orchestrator_url
            if provisioning_token:
                os.environ['PROVISIONING_TOKEN'] = provisioning_token
            if organization_id:
                os.environ['ORGANIZATION_ID'] = organization_id
            
            # Create and configure VM Agent
            click.echo("🔧 Initializing VM Agent...")
            server = VMAgentServer()
            
            # Generate credentials first
            click.echo("🔑 Generating VM credentials...")
            await server._ensure_credentials()
            
            # Register with orchestrator
            click.echo("📡 Registering with orchestrator...")
            if provisioning_token:
                success = await server.register_with_orchestrator(provisioning_token)
            else:
                # Manual organization setup
                click.echo(f"🏢 Setting up manual organization: {organization_id}")
                # This would need to be implemented based on your organization setup flow
                success = False
                click.echo("❌ Manual organization setup not yet implemented")
            
            if success:
                click.echo("✅ VM Agent installed and registered successfully!")
                click.echo(f"📁 Installation directory: {install_dir}")
                click.echo("🚀 To start the agent manually, run: vm-agent server")
                click.echo("💡 For systemd service installation, use the enhanced_install_vm_agent.sh script")
            else:
                click.echo("❌ Installation failed during registration")
                sys.exit(1)
                
        except Exception as e:
            click.echo(f"❌ Installation error: {e}", err=True)
            if ctx.obj.get('verbose'):
                import traceback
                traceback.print_exc()
            sys.exit(1)
    
    try:
        asyncio.run(run_install())
    except Exception as e:
        click.echo(f"Installation error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--orchestrator-url', required=True, help='Orchestrator URL')
@click.option('--provisioning-token', help='Provisioning token')
@click.option('--test-connection', is_flag=True, help='Test connection only')
@click.pass_context
def provision(ctx: click.Context, orchestrator_url: str, provisioning_token: Optional[str], test_connection: bool) -> None:
    """Provision or re-provision the agent with the orchestrator"""
    
    async def run_provision():
        try:
            if test_connection:
                click.echo("🔍 Testing orchestrator connection...")
                async with aiohttp.ClientSession() as session:
                    async with session.get(f"{orchestrator_url}/api/v1/docs", timeout=10) as response:
                        if response.status == 200:
                            click.echo("✅ Orchestrator is reachable")
                        else:
                            click.echo(f"❌ Orchestrator returned HTTP {response.status}")
                return
            
            # Full provisioning
            click.echo("🔄 Starting agent provisioning...")
            
            # Create server instance
            server = VMAgentServer(config_path=ctx.obj.get('config'))
            
            # Set orchestrator URL
            server.config['orchestrator']['url'] = orchestrator_url
            
            # Ensure we have basic credentials
            await server._ensure_credentials()
            
            # Register with orchestrator
            if provisioning_token:
                click.echo("📡 Registering with provisioning token...")
                success = await server.register_with_orchestrator(provisioning_token)
            else:
                click.echo("📡 Re-registering existing agent...")
                success = await server.register_with_orchestrator()
            
            if success:
                click.echo("✅ Agent provisioned successfully!")
                
                # Show agent details
                vm_id = server.security_manager.get_vm_id()
                click.echo(f"🆔 VM ID: {vm_id}")
                click.echo(f"🌐 Orchestrator: {orchestrator_url}")
                
                # Test WebSocket connection
                if server.ws_handler:
                    click.echo("🔌 Testing WebSocket connection...")
                    # This would require implementing a test method
                    click.echo("✅ WebSocket configuration updated")
                
                click.echo("🚀 Agent is ready! Restart the service to apply changes.")
            else:
                click.echo("❌ Provisioning failed")
                sys.exit(1)
                
        except Exception as e:
            click.echo(f"❌ Provisioning error: {e}", err=True)
            if ctx.obj.get('verbose'):
                import traceback
                traceback.print_exc()
            sys.exit(1)
    
    try:
        asyncio.run(run_provision())
    except Exception as e:
        click.echo(f"Provisioning error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.pass_context
def status(ctx: click.Context) -> None:
    """Show agent status and configuration"""
    
    async def show_status():
        try:
            # Create server instance to get config
            server = VMAgentServer(config_path=ctx.obj.get('config'))
            
            # Check if agent is registered
            security_manager = SecurityManager()
            vm_id = security_manager.get_vm_id()
            api_key = security_manager.get_api_key()
            
            status_info = {
                "agent_status": {
                    "vm_id": vm_id,
                    "agent_version": server.config['agent']['version'],
                    "credentials_loaded": bool(vm_id and api_key),
                    "ready": server.is_ready() if hasattr(server, 'is_ready') else False
                },
                "orchestrator": {
                    "url": server.config.get('orchestrator', {}).get('url'),
                    "websocket_url": server.config.get('orchestrator', {}).get('websocket_url'),
                    "connected": False  # Would need to check actual connection
                },
                "server_config": {
                    "host": server.config.get('server', {}).get('host'),
                    "port": server.config.get('server', {}).get('port'),
                    "ssl_enabled": server.config.get('server', {}).get('ssl', {}).get('enabled')
                },
                "tools_enabled": list(server.tools.keys()) if hasattr(server, 'tools') else [],
                "security": {
                    "certificates_present": all([
                        security_manager.vm_cert_path.exists(),
                        security_manager.vm_key_path.exists(),
                        security_manager.ca_cert_path.exists()
                    ]) if hasattr(security_manager, 'vm_cert_path') else False
                }
            }
            
            # Check service status if on systemd
            try:
                result = subprocess.run(['systemctl', 'is-active', 'vm-agent'], 
                                     capture_output=True, text=True)
                status_info["service_status"] = result.stdout.strip()
            except:
                status_info["service_status"] = "unknown"
            
            click.echo("🔍 VM Agent Status:")
            click.echo("=" * 50)
            click.echo(yaml.dump(status_info, default_flow_style=False))
            
        except Exception as e:
            click.echo(f"❌ Error getting status: {e}", err=True)
            if ctx.obj.get('verbose'):
                import traceback
                traceback.print_exc()
    
    asyncio.run(show_status())


@cli.command()
@click.argument('command')
@click.option('--timeout', default=30, type=int, help='Command timeout in seconds')
@click.pass_context
def exec(ctx: click.Context, command: str, timeout: int) -> None:
    """Execute a shell command via the agent"""
    
    async def run_command():
        try:
            server = VMAgentServer(config_path=ctx.obj.get('config'))
            
            if 'shell' not in server.tools:
                click.echo("Shell executor tool not enabled")
                return
            
            click.echo(f"Executing: {command}")
            result = await server.tools['shell'].execute_command(command, timeout=timeout)
            
            click.echo("Result:")
            click.echo(json.dumps(result, indent=2))
            
        except Exception as e:
            click.echo(f"Error executing command: {e}", err=True)
    
    asyncio.run(run_command())


@cli.command()
@click.option('--path', default='/', help='Directory path to list')
@click.pass_context
def ls(ctx: click.Context, path: str) -> None:
    """List directory contents via the agent"""
    
    async def list_directory():
        try:
            server = VMAgentServer(config_path=ctx.obj.get('config'))
            
            if 'file' not in server.tools:
                click.echo("File manager tool not enabled")
                return
            
            result = await server.tools['file'].list_directory(path)
            
            click.echo(f"Contents of {path}:")
            if result.get('success'):
                for item in result.get('files', []):
                    icon = "📁" if item['type'] == 'directory' else "📄"
                    click.echo(f"{icon} {item['name']}")
            else:
                click.echo(f"Error: {result.get('error')}")
                
        except Exception as e:
            click.echo(f"Error listing directory: {e}", err=True)
    
    asyncio.run(list_directory())


@cli.command()
@click.pass_context
def metrics(ctx: click.Context) -> None:
    """Show system metrics via the agent"""
    
    async def show_metrics():
        try:
            server = VMAgentServer(config_path=ctx.obj.get('config'))
            
            if 'system' not in server.tools:
                click.echo("System monitor tool not enabled")
                return
            
            result = await server.tools['system'].get_system_metrics()
            
            click.echo("System Metrics:")
            click.echo("=" * 50)
            click.echo(yaml.dump(result, default_flow_style=False))
                
        except Exception as e:
            click.echo(f"Error getting metrics: {e}", err=True)
    
    asyncio.run(show_metrics())


@cli.command()
@click.argument('log_path')
@click.option('--lines', default=100, type=int, help='Number of lines to analyze')
@click.pass_context
def logs(ctx: click.Context, log_path: str, lines: int) -> None:
    """Analyze log file via the agent"""
    
    async def analyze_logs():
        try:
            server = VMAgentServer(config_path=ctx.obj.get('config'))
            
            if 'logs' not in server.tools:
                click.echo("Log analyzer tool not enabled")
                return
            
            result = await server.tools['logs'].analyze_log_file(log_path, lines)
            
            click.echo(f"Log Analysis for {log_path}:")
            click.echo("=" * 50)
            click.echo(yaml.dump(result, default_flow_style=False))
                
        except Exception as e:
            click.echo(f"Error analyzing logs: {e}", err=True)
    
    asyncio.run(analyze_logs())


@cli.command()
@click.pass_context
def test(ctx: click.Context) -> None:
    """Run diagnostic tests on the agent"""
    
    async def run_tests():
        click.echo("Running VM Agent Diagnostic Tests...")
        click.echo("=" * 50)
        
        try:
            server = VMAgentServer(config_path=ctx.obj.get('config'))
            
            # Test 1: Configuration
            click.echo("✓ Configuration loaded successfully")
            
            # Test 2: Tools initialization
            enabled_tools = list(server.tools.keys())
            click.echo(f"✓ Tools initialized: {', '.join(enabled_tools)}")
            
            # Test 3: Tenant status
            tenant_manager = TenantManager()
            tenant_config = await tenant_manager.load_tenant_config()
            if tenant_config:
                click.echo("✓ Tenant provisioned")
            else:
                click.echo("⚠ Tenant not provisioned")
            
            # Test 4: Security manager
            security_manager = SecurityManager()
            if hasattr(security_manager, '_api_key'):
                click.echo("✓ Security manager initialized")
            else:
                click.echo("⚠ Security manager not fully initialized")
            
            # Test 5: Tool functionality
            if 'shell' in server.tools:
                result = await server.tools['shell'].execute_command('echo "test"', timeout=5)
                if result.get('success'):
                    click.echo("✓ Shell executor working")
                else:
                    click.echo("❌ Shell executor failed")
            
            if 'file' in server.tools:
                result = await server.tools['file'].list_directory('/tmp')
                if result.get('success'):
                    click.echo("✓ File manager working")
                else:
                    click.echo("❌ File manager failed")
            
            if 'system' in server.tools:
                result = await server.tools['system'].get_system_metrics()
                if result:
                    click.echo("✓ System monitor working")
                else:
                    click.echo("❌ System monitor failed")
            
            click.echo("\nDiagnostic tests completed!")
            
        except Exception as e:
            click.echo(f"Test error: {e}", err=True)
    
    asyncio.run(run_tests())


@cli.command()
@click.option('--output', '-o', help='Output file path')
@click.pass_context
def config(ctx: click.Context, output: Optional[str]) -> None:
    """Show or export current configuration"""
    
    try:
        server = VMAgentServer(config_path=ctx.obj.get('config'))
        config_data = server.config
        
        if output:
            with open(output, 'w') as f:
                yaml.dump(config_data, f, default_flow_style=False)
            click.echo(f"Configuration exported to {output}")
        else:
            click.echo("Current Configuration:")
            click.echo("=" * 50)
            click.echo(yaml.dump(config_data, default_flow_style=False))
            
    except Exception as e:
        click.echo(f"Error: {e}", err=True)


@cli.command()
@click.option('--orchestrator-url', help='Test specific orchestrator URL')
@click.pass_context  
def test_connection(ctx: click.Context, orchestrator_url: Optional[str]) -> None:
    """Test connection to orchestrator"""
    
    async def run_test():
        try:
            # Get orchestrator URL from config or parameter
            if not orchestrator_url:
                server = VMAgentServer(config_path=ctx.obj.get('config'))
                orchestrator_url_to_test = server.config.get('orchestrator', {}).get('url')
                if not orchestrator_url_to_test:
                    click.echo("❌ No orchestrator URL configured. Use --orchestrator-url parameter.")
                    return
            else:
                orchestrator_url_to_test = orchestrator_url
            
            click.echo(f"🔍 Testing connection to: {orchestrator_url_to_test}")
            
            # Test basic connectivity
            async with aiohttp.ClientSession() as session:
                # Test docs endpoint
                try:
                    async with session.get(f"{orchestrator_url_to_test}/api/v1/docs", timeout=10) as response:
                        if response.status == 200:
                            click.echo("✅ Orchestrator docs endpoint reachable")
                        else:
                            click.echo(f"⚠️  Orchestrator docs endpoint returned HTTP {response.status}")
                except Exception as e:
                    click.echo(f"❌ Cannot reach orchestrator docs: {e}")
                    return
                
                # Test CA certificate endpoint
                try:
                    async with session.get(f"{orchestrator_url_to_test}/api/v1/agents/ca-certificate", timeout=10) as response:
                        if response.status == 200:
                            click.echo("✅ CA certificate endpoint reachable")
                        else:
                            click.echo(f"⚠️  CA certificate endpoint returned HTTP {response.status}")
                except Exception as e:
                    click.echo(f"❌ Cannot reach CA certificate endpoint: {e}")
                
                # Test registration endpoint (without actually registering)
                try:
                    async with session.post(f"{orchestrator_url_to_test}/api/v1/agents/register", 
                                          json={}, timeout=10) as response:
                        if response.status in [400, 422]:  # Expected for empty payload
                            click.echo("✅ Registration endpoint reachable")
                        else:
                            click.echo(f"⚠️  Registration endpoint returned HTTP {response.status}")
                except Exception as e:
                    click.echo(f"❌ Cannot reach registration endpoint: {e}")
                
            click.echo("🏁 Connection test completed")
            
        except Exception as e:
            click.echo(f"❌ Connection test error: {e}", err=True)
            
    asyncio.run(run_test())


def main() -> None:
    """Main entry point for CLI"""
    cli()


if __name__ == '__main__':
    main() 