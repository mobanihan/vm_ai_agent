#!/usr/bin/env python3
"""
Test script to verify VM Agent Server functionality
"""

import asyncio
import sys
import os
import tempfile
import shutil
from pathlib import Path

# Add the parent directory to the path so we can import vm_agent
sys.path.insert(0, str(Path(__file__).parent.parent))

from vm_agent.server import VMAgentServer
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

async def test_server_initialization():
    """Test server initialization without orchestrator"""
    logger.info("Testing server initialization...")
    
    # Create a temporary directory for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        security_dir = temp_path / "security"
        
        # Override config to use temp directory
        config_overrides = {
            'server': {
                'host': '127.0.0.1',
                'port': 0,  # Use any available port
                'ssl': {'enabled': False}  # Disable SSL for testing
            },
            'orchestrator': {
                'url': None  # No orchestrator for this test
            },
            'security': {
                'enabled': True,
                'config_dir': str(security_dir)
            }
        }
        
        try:
            # Initialize server
            server = VMAgentServer(**config_overrides)
            
            # Override security manager config dir
            server.security_manager.config_dir = security_dir
            server.security_manager.config_dir.mkdir(parents=True, exist_ok=True)
            
            # Update all the security manager paths
            server.security_manager.ca_cert_path = security_dir / "ca.crt"
            server.security_manager.vm_key_path = security_dir / "vm.key"
            server.security_manager.vm_cert_path = security_dir / "vm.crt"
            server.security_manager.vm_csr_path = security_dir / "vm.csr"
            server.security_manager.api_key_path = security_dir / "api.key"
            server.security_manager.vm_id_path = security_dir / "vm.id"
            
            logger.info("✅ Server initialized successfully")
            
            # Test credential generation
            success = await server._ensure_credentials()
            if success:
                logger.info("✅ Credentials generated successfully")
                
                vm_id = server.security_manager.get_vm_id()
                api_key = server.security_manager.get_api_key()
                
                logger.info(f"VM ID: {vm_id}")
                logger.info(f"API Key: {api_key[:10]}...")
                
                # Test API key verification
                if server.security_manager.verify_api_key(api_key):
                    logger.info("✅ API key verification works")
                else:
                    logger.error("❌ API key verification failed")
                    return False
                
            else:
                logger.error("❌ Failed to generate credentials")
                return False
            
            # Test server readiness
            if server.is_ready():
                logger.info("✅ Server is ready")
            else:
                logger.error("❌ Server is not ready")
                return False
            
            # Test server startup
            await server.start()
            logger.info("✅ Server started successfully")
            
            # Get the actual port being used
            actual_port = server._site._server.sockets[0].getsockname()[1]
            logger.info(f"Server listening on port {actual_port}")
            
            # Test server shutdown
            await server.stop()
            logger.info("✅ Server stopped successfully")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Test failed: {e}")
            import traceback
            traceback.print_exc()
            return False

async def test_with_existing_credentials():
    """Test loading existing credentials from disk"""
    logger.info("Testing with existing credentials...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        security_dir = temp_path / "security"
        security_dir.mkdir(parents=True, exist_ok=True)
        
        # Create mock credentials
        vm_id = "test-vm-123"
        api_key = "test-api-key-456"
        
        (security_dir / "vm.id").write_text(vm_id)
        (security_dir / "api.key").write_text(api_key)
        
        config_overrides = {
            'server': {
                'host': '127.0.0.1',
                'port': 0,
                'ssl': {'enabled': False}
            },
            'orchestrator': {'url': None}
        }
        
        try:
            server = VMAgentServer(**config_overrides)
            
            # Override security manager paths
            server.security_manager.config_dir = security_dir
            server.security_manager.ca_cert_path = security_dir / "ca.crt"
            server.security_manager.vm_key_path = security_dir / "vm.key"
            server.security_manager.vm_cert_path = security_dir / "vm.crt"
            server.security_manager.vm_csr_path = security_dir / "vm.csr"
            server.security_manager.api_key_path = security_dir / "api.key"
            server.security_manager.vm_id_path = security_dir / "vm.id"
            
            # Test loading existing credentials
            loaded = await server.security_manager.load_existing_credentials()
            if loaded:
                logger.info("✅ Existing credentials loaded successfully")
                
                if server.security_manager.get_vm_id() == vm_id:
                    logger.info("✅ VM ID loaded correctly")
                else:
                    logger.error(f"❌ VM ID mismatch: expected {vm_id}, got {server.security_manager.get_vm_id()}")
                    return False
                
                if server.security_manager.get_api_key() == api_key:
                    logger.info("✅ API key loaded correctly")
                else:
                    logger.error("❌ API key mismatch")
                    return False
                
            else:
                logger.error("❌ Failed to load existing credentials")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Test failed: {e}")
            import traceback
            traceback.print_exc()
            return False

async def main():
    """Run all tests"""
    logger.info("🧪 Starting VM Agent Server Tests")
    
    tests = [
        ("Server Initialization", test_server_initialization),
        ("Existing Credentials", test_with_existing_credentials),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        logger.info(f"\n--- Running {test_name} Test ---")
        
        try:
            result = await test_func()
            if result:
                logger.info(f"✅ {test_name} test PASSED")
                passed += 1
            else:
                logger.error(f"❌ {test_name} test FAILED")
        except Exception as e:
            logger.error(f"❌ {test_name} test FAILED with exception: {e}")
    
    logger.info(f"\n🏁 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 All tests passed!")
        return True
    else:
        logger.error("💥 Some tests failed!")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1) 