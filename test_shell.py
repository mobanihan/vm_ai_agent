#!/usr/bin/env python3

import asyncio
import sys
import os

# Add the current directory to Python path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from tools.shell_executor import ShellExecutor

async def test_shell_commands():
    """Test basic shell commands"""
    
    # Initialize shell executor with basic config
    config = {
        'timeout_default': 30,
        'timeout_max': 300,
        'blocked_commands': []
    }
    
    executor = ShellExecutor(config)
    
    # Test commands
    test_commands = [
        "uname -r",
        "echo 'Hello World'",
        "whoami",
        "pwd",
        "ls -la /",
        "which uname",
        "echo $PATH"
    ]
    
    print("Testing Shell Executor Commands:")
    print("=" * 50)
    
    for command in test_commands:
        print(f"\nTesting: {command}")
        try:
            result = await executor.execute(command)
            print(f"Return Code: {result['return_code']}")
            print(f"Success: {result['success']}")
            if result['stdout']:
                print(f"STDOUT:\n{result['stdout']}")
            if result['stderr']:
                print(f"STDERR:\n{result['stderr']}")
            if result.get('error_hint'):
                print(f"Error Hint: {result['error_hint']}")
        except Exception as e:
            print(f"Exception: {e}")
        print("-" * 30)

if __name__ == "__main__":
    asyncio.run(test_shell_commands()) 