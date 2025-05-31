import os
import aiofiles
import json
import mimetypes
from typing import Dict, Any, List, Optional
from pathlib import Path
import fnmatch
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class FileManager:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.max_file_size = config.get('max_file_size', 100 * 1024 * 1024)  # 100MB default
        self.allowed_paths = config.get('allowed_paths', [])
        self.blocked_paths = config.get('blocked_paths', [])
    
    def is_path_allowed(self, path: str) -> bool:
        """Check if file path is allowed"""
        abs_path = os.path.abspath(path)
        
        # Check blocked paths first
        for blocked_pattern in self.blocked_paths:
            if fnmatch.fnmatch(abs_path, blocked_pattern):
                return False
        
        # Check allowed paths
        if not self.allowed_paths or "*" in self.allowed_paths:
            return True
            
        for allowed_pattern in self.allowed_paths:
            if fnmatch.fnmatch(abs_path, allowed_pattern):
                return True
                
        return False
    
    async def read_file(self, file_path: str, encoding: str = 'utf-8') -> Dict[str, Any]:
        """Read file contents"""
        try:
            # Security check
            if not os.path.exists(file_path):
                return {
                    "success": False,
                    "error": f"File not found: {file_path}",
                    "timestamp": datetime.now().isoformat()
                }
            
            # Check file size
            file_size = os.path.getsize(file_path)
            if file_size > self.max_file_size:
                return {
                    "success": False,
                    "error": f"File too large: {file_size} bytes (max: {self.max_file_size})",
                    "timestamp": datetime.now().isoformat()
                }
            
            async with aiofiles.open(file_path, 'r', encoding=encoding) as f:
                content = await f.read()
            
            return {
                "success": True,
                "file_path": file_path,
                "content": content,
                "size": file_size,
                "encoding": encoding,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to read file {file_path}: {e}")
            return {
                "success": False,
                "error": str(e),
                "file_path": file_path,
                "timestamp": datetime.now().isoformat()
            }
    
    async def write_file(self, file_path: str, content: str, encoding: str = 'utf-8') -> Dict[str, Any]:
        """Write content to file"""
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            async with aiofiles.open(file_path, 'w', encoding=encoding) as f:
                await f.write(content)
            
            file_size = os.path.getsize(file_path)
            
            return {
                "success": True,
                "file_path": file_path,
                "size": file_size,
                "encoding": encoding,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to write file {file_path}: {e}")
            return {
                "success": False,
                "error": str(e),
                "file_path": file_path,
                "timestamp": datetime.now().isoformat()
            }
    
    async def list_directory(self, directory_path: str) -> Dict[str, Any]:
        """List directory contents"""
        try:
            if not os.path.exists(directory_path):
                return {
                    "success": False,
                    "error": f"Directory not found: {directory_path}",
                    "timestamp": datetime.now().isoformat()
                }
            
            if not os.path.isdir(directory_path):
                return {
                    "success": False,
                    "error": f"Path is not a directory: {directory_path}",
                    "timestamp": datetime.now().isoformat()
                }
            
            files = []
            for item in os.listdir(directory_path):
                item_path = os.path.join(directory_path, item)
                item_stat = os.stat(item_path)
                
                files.append({
                    "name": item,
                    "path": item_path,
                    "type": "directory" if os.path.isdir(item_path) else "file",
                    "size": item_stat.st_size,
                    "modified": datetime.fromtimestamp(item_stat.st_mtime).isoformat(),
                    "permissions": oct(item_stat.st_mode)[-3:]
                })
            
            return {
                "success": True,
                "directory_path": directory_path,
                "files": sorted(files, key=lambda x: (x["type"], x["name"])),
                "total_items": len(files),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to list directory {directory_path}: {e}")
            return {
                "success": False,
                "error": str(e),
                "directory_path": directory_path,
                "timestamp": datetime.now().isoformat()
            }