import psutil
import platform
import json
from typing import Dict, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class SystemMonitor:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.cache_ttl = config.get('metrics_cache_ttl', 5)
        self._cache = {}
        self._last_update = {}
    
    def _is_cache_valid(self, metric_type: str) -> bool:
        """Check if cached metric is still valid"""
        if metric_type not in self._last_update:
            return False
        
        elapsed = datetime.now().timestamp() - self._last_update[metric_type]
        return elapsed < self.cache_ttl
    
    async def get_cpu_info(self) -> Dict[str, Any]:
        """Get CPU information and usage"""
        if self._is_cache_valid('cpu'):
            return self._cache['cpu']
        
        try:
            cpu_info = {
                "physical_cores": psutil.cpu_count(logical=False),
                "logical_cores": psutil.cpu_count(logical=True),
                "current_freq": psutil.cpu_freq()._asdict() if psutil.cpu_freq() else None,
                "usage_percent": psutil.cpu_percent(interval=1),
                "usage_per_core": psutil.cpu_percent(interval=1, percpu=True),
                "load_average": psutil.getloadavg() if hasattr(psutil, 'getloadavg') else None,
                "architecture": platform.machine(),
                "processor": platform.processor()
            }
            
            self._cache['cpu'] = cpu_info
            self._last_update['cpu'] = datetime.now().timestamp()
            
            return cpu_info
            
        except Exception as e:
            logger.error(f"Failed to get CPU info: {e}")
            raise
    
    async def get_memory_info(self) -> Dict[str, Any]:
        """Get memory information"""
        if self._is_cache_valid('memory'):
            return self._cache['memory']
        
        try:
            virtual_mem = psutil.virtual_memory()
            swap_mem = psutil.swap_memory()
            
            memory_info = {
                "virtual": {
                    "total": virtual_mem.total,
                    "available": virtual_mem.available,
                    "used": virtual_mem.used,
                    "percentage": virtual_mem.percent,
                    "free": virtual_mem.free,
                    "buffers": getattr(virtual_mem, 'buffers', 0),
                    "cached": getattr(virtual_mem, 'cached', 0)
                },
                "swap": {
                    "total": swap_mem.total,
                    "used": swap_mem.used,
                    "free": swap_mem.free,
                    "percentage": swap_mem.percent
                }
            }
            
            self._cache['memory'] = memory_info
            self._last_update['memory'] = datetime.now().timestamp()
            
            return memory_info
            
        except Exception as e:
            logger.error(f"Failed to get memory info: {e}")
            raise
    
    async def get_disk_info(self) -> Dict[str, Any]:
        """Get disk information"""
        if self._is_cache_valid('disk'):
            return self._cache['disk']
        
        try:
            disk_info = {
                "partitions": [],
                "io_counters": psutil.disk_io_counters()._asdict() if psutil.disk_io_counters() else None
            }
            
            # Get partition information
            for partition in psutil.disk_partitions():
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    partition_info = {
                        "device": partition.device,
                        "mountpoint": partition.mountpoint,
                        "fstype": partition.fstype,
                        "total": usage.total,
                        "used": usage.used,
                        "free": usage.free,
                        "percentage": (usage.used / usage.total) * 100 if usage.total > 0 else 0
                    }
                    disk_info["partitions"].append(partition_info)
                except PermissionError:
                    # Skip partitions we can't access
                    continue
            
            self._cache['disk'] = disk_info
            self._last_update['disk'] = datetime.now().timestamp()
            
            return disk_info
            
        except Exception as e:
            logger.error(f"Failed to get disk info: {e}")
            raise
    
    async def get_network_info(self) -> Dict[str, Any]:
        """Get network information"""
        if self._is_cache_valid('network'):
            return self._cache['network']
        
        try:
            # Network interfaces
            interfaces = {}
            for interface, addrs in psutil.net_if_addrs().items():
                interface_info = {
                    "addresses": [],
                    "stats": psutil.net_if_stats()[interface]._asdict() if interface in psutil.net_if_stats() else None
                }
                
                for addr in addrs:
                    interface_info["addresses"].append({
                        "family": str(addr.family),
                        "address": addr.address,
                        "netmask": addr.netmask,
                        "broadcast": addr.broadcast
                    })
                
                interfaces[interface] = interface_info
            
            # Network IO counters
            io_counters = psutil.net_io_counters()._asdict() if psutil.net_io_counters() else None
            
            network_info = {
                "interfaces": interfaces,
                "io_counters": io_counters,
                "connections": len(psutil.net_connections())
            }
            
            self._cache['network'] = network_info
            self._last_update['network'] = datetime.now().timestamp()
            
            return network_info
            
        except Exception as e:
            logger.error(f"Failed to get network info: {e}")
            raise
    
    async def get_system_info(self) -> Dict[str, Any]:
        """Get general system information"""
        try:
            boot_time = datetime.fromtimestamp(psutil.boot_time())
            
            system_info = {
                "hostname": platform.node(),
                "platform": platform.platform(),
                "system": platform.system(),
                "release": platform.release(),
                "version": platform.version(),
                "machine": platform.machine(),
                "processor": platform.processor(),
                "boot_time": boot_time.isoformat(),
                "uptime_seconds": datetime.now().timestamp() - psutil.boot_time(),
                "users": [user._asdict() for user in psutil.users()],
                "process_count": len(psutil.pids())
            }
            
            return system_info
            
        except Exception as e:
            logger.error(f"Failed to get system info: {e}")
            raise
    
    async def get_all_info(self) -> Dict[str, Any]:
        """Get comprehensive system information"""
        return {
            "cpu": await self.get_cpu_info(),
            "memory": await self.get_memory_info(),
            "disk": await self.get_disk_info(),
            "network": await self.get_network_info(),
            "system": await self.get_system_info(),
            "timestamp": datetime.now().isoformat()
        }