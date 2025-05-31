#!/usr/bin/env python3
"""
Tests for VM Agent Client
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from vm_agent.client import VMAgentClient, connect_to_agent


class TestVMAgentClient:
    """Test cases for VMAgentClient"""
    
    def test_client_initialization(self):
        """Test client initialization"""
        client = VMAgentClient(
            agent_url="https://test-agent:8080",
            api_key="test-key"
        )
        
        assert client.agent_url == "https://test-agent:8080"
        assert client.api_key == "test-key"
        assert client._session is None
    
    def test_client_url_normalization(self):
        """Test URL normalization"""
        client = VMAgentClient("https://test-agent:8080/")
        assert client.agent_url == "https://test-agent:8080"
    
    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test async context manager"""
        with patch.object(VMAgentClient, 'connect', new_callable=AsyncMock) as mock_connect:
            with patch.object(VMAgentClient, 'disconnect', new_callable=AsyncMock) as mock_disconnect:
                async with VMAgentClient("https://test:8080") as client:
                    assert client is not None
                
                mock_connect.assert_called_once()
                mock_disconnect.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_health_check(self):
        """Test health check"""
        client = VMAgentClient("https://test:8080")
        
        with patch.object(client, '_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {"status": "healthy"}
            
            result = await client.health_check()
            
            assert result["status"] == "healthy"
            mock_request.assert_called_once_with('GET', '/health')
    
    @pytest.mark.asyncio
    async def test_execute_command(self):
        """Test command execution"""
        client = VMAgentClient("https://test:8080")
        
        with patch.object(client, '_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {"result": "success"}
            
            result = await client.execute_command("ls -la")
            
            assert result["result"] == "success"
            mock_request.assert_called_once()
            
            # Check the MCP request structure
            call_args = mock_request.call_args
            assert call_args[0] == ('POST', '/mcp')
            assert 'execute_shell_command' in str(call_args[1]['data'])


@pytest.mark.asyncio
async def test_connect_to_agent():
    """Test convenience function"""
    with patch.object(VMAgentClient, 'connect', new_callable=AsyncMock):
        client = await connect_to_agent("https://test:8080", api_key="test")
        assert isinstance(client, VMAgentClient)
        assert client.api_key == "test" 