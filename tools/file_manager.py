import os
import aiofiles
import json
import mimetypes
from typing import Dict, Any, List, Optional
from pathlib import Path
import fnmatch
import logging

logger = logging.getLogger(__name__)

class FileManager:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.max_file_size = config.get('max_file_size', 10485760)  # 10MB
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
    
    async def read_file(self, path: str, **kwargs) -> Dict[str, Any]:
        """Read file contents with security checks"""
        
        if not self.is_path_allowed(path):
            raise PermissionError(f"Access denied to path: {path}")
        
        if not os.path.exists(path):
            raise FileNotFoundError(f"File not found: {path}")
        
        if not os.path.isfile(path):
            raise ValueError(f"Path is not a file: {path}")
        
        # Check file size
        file_size = os.path.getsize(path)
        if file_size > self.max_file_size:
            raise ValueError(f"File too large: {file_size} bytes (max: {self.max_file_size})")
        
        max_lines = kwargs.get('max_lines', 1000)
        encoding = kwargs.get('encoding', 'utf-8')
        
        try:
            async with aiofiles.open(path, 'r', encoding=encoding) as f:
                if max_lines:
                    lines = []
                    line_count = 0
                    async for line in f:
                        lines.append(line)
                        line_count += 1
                        if line_count >= max_lines:
                            break
                    content = ''.join(lines)
                else:
                    content = await f.read()
            
            # Get file info
            stat = os.stat(path)
            mime_type, _ = mimetypes.guess_type(path)
            
            return {
                "path": path,
                "content": content,
                "size": file_size,
                "lines_read": line_count if max_lines else content.count('\n') + 1,
                "mime_type": mime_type,
                "modified_time": stat.st_mtime,
                "permissions": oct(stat.st_mode)[-3:],
                "encoding": encoding
            }
            
        except UnicodeDecodeError as e:
            # Try binary read for non-text files
            async with aiofiles.open(path, 'rb') as f:
                content = await f.read()
                
            return {
                "path": path,
                "content": content.hex(),  # Return as hex string
                "size": file_size,
                "type": "binary",
                "mime_type": mime_type,
                "encoding": "binary"
            }
    
    async def write_file(self, path: str, content: str, **kwargs) -> Dict[str, Any]:
        """Write content to file with security checks"""
        
        if not self.is_path_allowed(path):
            raise PermissionError(f"Access denied to path: {path}")
        
        encoding = kwargs.get('encoding', 'utf-8')
        mode = kwargs.get('mode', 'w')
        create_dirs = kwargs.get('create_dirs', False)
        
        # Create directories if needed
        if create_dirs:
            os.makedirs(os.path.dirname(path), exist_ok=True)
        
        try:
            async with aiofiles.open(path, mode, encoding=encoding) as f:
                await f.write(content)
            
            # Get file info
            stat = os.stat(path)
            
            return {
                "path": path,
                "bytes_written": len(content.encode(encoding)),
                "mode": mode,
                "encoding": encoding,
                "modified_time": stat.st_mtime
            }
            
        except Exception as e:
            logger.error(f"Failed to write file {path}: {e}")
            raise
    
    async def list_directory(self, path: str, **kwargs) -> Dict[str, Any]:
        """List directory contents"""
        
        if not self.is_path_allowed(path):
            raise PermissionError(f"Access denied to path: {path}")
        
        if not os.path.isdir(path):
            raise ValueError(f"Path is not a directory: {path}")
        
        recursive = kwargs.get('recursive', False)
        include_hidden = kwargs.get('include_hidden', False)
        
        entries = []
        
        if recursive:
            for root, dirs, files in os.walk(path):
                # Filter hidden directories
                if not include_hidden:
                    dirs[:] = [d for d in dirs if not d.startswith('.')]
                
                for name in files + dirs:
                    if not include_hidden and name.startswith('.'):
                        continue
                        
                    full_path = os.path.join(root, name)
                    stat = os.stat(full_path)
                    
                    entries.append({
                        "name": name,
                        "path": full_path,
                        "type": "directory" if os.path.isdir(full_path) else "file",
                        "size": stat.st_size,
                        "modified_time": stat.st_mtime,
                        "permissions": oct(stat.st_mode)[-3:]
                    })
        else:
            for entry in os.listdir(path):
                if not include_hidden and entry.startswith('.'):
                    continue
                    
                full_path = os.path.join(path, entry)
                stat = os.stat(full_path)
                
                entries.append({
                    "name": entry,
                    "path": full_path,
                    "type": "directory" if os.path.isdir(full_path) else "file",
                    "size": stat.st_size,
                    "modified_time": stat.st_mtime,
                    "permissions": oct(stat.st_mode)[-3:]
                })
        
        return {
            "path": path,
            "entries": entries,
            "total_entries": len(entries),
            "recursive": recursive
        }