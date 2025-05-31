import asyncio
import subprocess
import json
import os
import shlex
from typing import Dict, Any, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class ShellExecutor:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.timeout_default = config.get('timeout_default', 30)
        self.timeout_max = config.get('timeout_max', 300)
        self.blocked_commands = config.get('blocked_commands', [])
        
    def is_command_allowed(self, command: str) -> bool:
        """Check if command is allowed to execute"""
        # Check blocked commands
        for blocked in self.blocked_commands:
            if blocked in command:
                return False
        return True
    
    async def execute_command(self, command: str, timeout: int = 300, **kwargs) -> Dict[str, Any]:
        """Execute shell command with security checks"""
        
        # Security check
        if not self.is_command_allowed(command):
            raise ValueError(f"Command blocked by security policy: {command}")
        
        # Parse arguments
        timeout = min(timeout, self.timeout_max)
        working_dir = kwargs.get('working_dir', os.getcwd())
        env_vars = kwargs.get('env_vars', {})
        capture_output = kwargs.get('capture_output', True)
        
        # Prepare environment with proper PATH
        env = os.environ.copy()
        # Ensure PATH includes common binary locations
        if 'PATH' not in env or not env['PATH']:
            env['PATH'] = '/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin'
        else:
            # Add common paths if not already present
            common_paths = ['/usr/local/sbin', '/usr/local/bin', '/usr/sbin', '/usr/bin', '/sbin', '/bin']
            current_paths = env['PATH'].split(':')
            for path in common_paths:
                if path not in current_paths:
                    env['PATH'] = f"{env['PATH']}:{path}"
        
        env.update(env_vars)
        
        logger.info(f"Executing command: {command} (timeout: {timeout}s, cwd: {working_dir})")
        
        try:
            # Create subprocess with explicit shell
            if capture_output:
                process = await asyncio.create_subprocess_shell(
                    command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=working_dir,
                    env=env,
                    executable='/bin/bash'  # Explicitly use bash
                )
            else:
                process = await asyncio.create_subprocess_shell(
                    command,
                    cwd=working_dir,
                    env=env,
                    executable='/bin/bash'  # Explicitly use bash
                )
            
            # Execute with timeout
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                # Kill process on timeout
                try:
                    process.kill()
                    await process.wait()
                except:
                    pass
                raise asyncio.TimeoutError(f"Command timed out after {timeout} seconds")
            
            # Prepare result
            result = {
                "command": command,
                "return_code": process.returncode,
                "stdout": stdout.decode('utf-8', errors='replace') if stdout else "",
                "stderr": stderr.decode('utf-8', errors='replace') if stderr else "",
                "working_dir": working_dir,
                "timestamp": datetime.now().isoformat(),
                "success": process.returncode == 0
            }
            
            # Add helpful error message for command not found
            if process.returncode == 127:
                result["error_hint"] = f"Command not found: '{command.split()[0] if command.split() else command}'. Check if the command is installed and PATH is correct."
                logger.warning(f"Command not found (return code 127): {command}")
            
            logger.info(f"Command completed: return_code={process.returncode}")
            return result
            
        except Exception as e:
            logger.error(f"Command execution failed: {e}")
            return {
                "command": command,
                "return_code": -1,
                "stdout": "",
                "stderr": str(e),
                "working_dir": working_dir,
                "timestamp": datetime.now().isoformat(),
                "success": False,
                "error": str(e)
            }
    
    async def get_command_history(self) -> Dict[str, Any]:
        """Get command execution history"""
        # This would typically read from a log file or database
        return {
            "history": [],
            "total_commands": 0,
            "timestamp": datetime.now().isoformat()
        }

    async def execute_script(self, script_content: str, interpreter: str = "bash") -> Dict[str, Any]:
        """Execute a script from string content"""
        import tempfile
        
        # Create temporary script file
        with tempfile.NamedTemporaryFile(mode='w', suffix=f'.{interpreter}', delete=False) as f:
            f.write(script_content)
            script_path = f.name
        
        try:
            # Make script executable
            os.chmod(script_path, 0o755)
            
            # Execute script
            command = f"{interpreter} {script_path}"
            result = await self.execute_command(command)
            result["script_content"] = script_content
            result["interpreter"] = interpreter
            
            return result
            
        finally:
            # Clean up temporary file
            try:
                os.unlink(script_path)
            except:
                pass