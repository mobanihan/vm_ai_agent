# Lazy imports to avoid circular dependency issues during installation
__all__ = [
    'SecurityManager', 
    'ShellExecutor', 
    'FileManager', 
    'SystemMonitor', 
    'LogAnalyzer', 
    'WebSocketCommandHandler',
    'TenantManager'
]

def __getattr__(name):
    """Lazy import of tools to avoid dependency issues during installation"""
    if name == 'SecurityManager':
        from .security_manager import SecurityManager
        return SecurityManager
    elif name == 'ShellExecutor':
        from .shell_executor import ShellExecutor
        return ShellExecutor
    elif name == 'FileManager':
        from .file_manager import FileManager
        return FileManager
    elif name == 'SystemMonitor':
        from .system_monitor import SystemMonitor
        return SystemMonitor
    elif name == 'LogAnalyzer':
        from .log_analyzer import LogAnalyzer
        return LogAnalyzer
    elif name == 'WebSocketCommandHandler':
        from .websocket_handler import WebSocketCommandHandler
        return WebSocketCommandHandler
    elif name == 'TenantManager':
        from .tenant_manager import TenantManager
        return TenantManager
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")