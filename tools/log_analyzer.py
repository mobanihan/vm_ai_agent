import re
import os
from typing import Dict, Any, List, Optional, Pattern
from datetime import datetime, timedelta
import json
import logging

logger = logging.getLogger(__name__)

class LogAnalyzer:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.max_lines_default = config.get('max_lines_default', 1000)
        self.max_lines_max = config.get('max_lines_max', 10000)
        
        # Common log patterns
        self.patterns = {
            'apache_common': re.compile(
                r'(?P<ip>\S+) \S+ \S+ \[(?P<timestamp>[^\]]+)\] "(?P<method>\S+) (?P<path>\S+) (?P<protocol>\S+)" (?P<status>\d+) (?P<size>\S+)'
            ),
            'apache_combined': re.compile(
                r'(?P<ip>\S+) \S+ \S+ \[(?P<timestamp>[^\]]+)\] "(?P<method>\S+) (?P<path>\S+) (?P<protocol>\S+)" (?P<status>\d+) (?P<size>\S+) "(?P<referer>[^"]*)" "(?P<user_agent>[^"]*)"'
            ),
            'nginx': re.compile(
                r'(?P<ip>\S+) - \S+ \[(?P<timestamp>[^\]]+)\] "(?P<method>\S+) (?P<path>\S+) (?P<protocol>\S+)" (?P<status>\d+) (?P<size>\d+) "(?P<referer>[^"]*)" "(?P<user_agent>[^"]*)"'
            ),
            'syslog': re.compile(
                r'(?P<timestamp>\w+\s+\d+\s+\d+:\d+:\d+) (?P<hostname>\S+) (?P<process>\S+)(?:\[(?P<pid>\d+)\])?: (?P<message>.*)'
            ),
            'error': re.compile(r'error|fail|exception|critical', re.IGNORECASE),
            'warning': re.compile(r'warn|warning|alert', re.IGNORECASE),
            'timestamp_iso': re.compile(r'\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}'),
            'timestamp_common': re.compile(r'\d{2}/\w{3}/\d{4}:\d{2}:\d{2}:\d{2}'),
            'ip_address': re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b')
        }
    
    async def analyze_log(self, log_path: str, **kwargs) -> Dict[str, Any]:
        """Analyze log file with various options"""
        
        if not os.path.exists(log_path):
            raise FileNotFoundError(f"Log file not found: {log_path}")
        
        # Parse arguments
        pattern = kwargs.get('pattern')
        lines_to_read = min(kwargs.get('lines', self.max_lines_default), self.max_lines_max)
        time_range = kwargs.get('time_range')  # e.g., "1h", "24h", "7d"
        log_format = kwargs.get('format', 'auto')  # auto, apache, nginx, syslog
        include_stats = kwargs.get('include_stats', True)
        
        try:
            # Read log lines
            lines = await self._read_log_lines(log_path, lines_to_read, time_range)
            
            # Parse lines based on format
            parsed_entries = self._parse_log_lines(lines, log_format)
            
            # Apply pattern filtering
            if pattern:
                filtered_entries = self._filter_by_pattern(parsed_entries, pattern)
            else:
                filtered_entries = parsed_entries
            
            # Generate statistics
            stats = self._generate_stats(filtered_entries) if include_stats else None
            
            result = {
                "log_path": log_path,
                "total_lines_read": len(lines),
                "matching_entries": len(filtered_entries),
                "entries": filtered_entries,
                "statistics": stats,
                "analysis_time": datetime.now().isoformat(),
                "pattern": pattern,
                "time_range": time_range,
                "format": log_format
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to analyze log {log_path}: {e}")
            raise
    
    async def _read_log_lines(self, log_path: str, max_lines: int, time_range: Optional[str]) -> List[str]:
        """Read log lines with optional time filtering"""
        lines = []
        
        # Calculate time threshold if time_range is specified
        time_threshold = None
        if time_range:
            time_threshold = self._parse_time_range(time_range)
        
        try:
            with open(log_path, 'r', encoding='utf-8', errors='replace') as f:
                # Read from end of file for recent logs
                if max_lines and not time_range:
                    # Efficient tail reading
                    lines = self._tail_file(f, max_lines)
                else:
                    # Read all lines and filter
                    for line_num, line in enumerate(f):
                        if time_threshold and not self._is_line_in_time_range(line, time_threshold):
                            continue
                        
                        lines.append(line.strip())
                        
                        if max_lines and len(lines) >= max_lines:
                            break
            
            return lines
            
        except UnicodeDecodeError:
            # Try with different encoding
            with open(log_path, 'r', encoding='latin-1') as f:
                return [line.strip() for line in f.readlines()[-max_lines:] if line.strip()]
    
    def _tail_file(self, file_obj, num_lines: int) -> List[str]:
        """Efficiently read last N lines from file"""
        file_obj.seek(0, 2)  # Go to end of file
        file_size = file_obj.tell()
        
        if file_size == 0:
            return []
        
        # Read in chunks from the end
        lines = []
        chunk_size = 8192
        pos = file_size
        
        while len(lines) < num_lines and pos > 0:
            chunk_start = max(0, pos - chunk_size)
            file_obj.seek(chunk_start)
            chunk = file_obj.read(pos - chunk_start)
            
            chunk_lines = chunk.split('\n')
            if pos < file_size:  # Not the first chunk
                chunk_lines = chunk_lines[1:]  # Remove partial line
            
            lines = chunk_lines + lines
            pos = chunk_start
        
        return [line for line in lines if line.strip()][-num_lines:]
    
    def _parse_log_lines(self, lines: List[str], log_format: str) -> List[Dict[str, Any]]:
        """Parse log lines based on format"""
        parsed_entries = []
        
        for line_num, line in enumerate(lines):
            entry = {
                "line_number": line_num + 1,
                "raw_line": line,
                "parsed": {},
                "timestamp": None,
                "level": self._detect_log_level(line)
            }
            
            # Auto-detect format if needed
            if log_format == 'auto':
                detected_format = self._detect_log_format(line)
            else:
                detected_format = log_format
            
            # Parse based on format
            if detected_format in self.patterns:
                match = self.patterns[detected_format].search(line)
                if match:
                    entry["parsed"] = match.groupdict()
                    entry["format"] = detected_format
                    
                    # Extract timestamp if available
                    if "timestamp" in entry["parsed"]:
                        entry["timestamp"] = self._parse_timestamp(entry["parsed"]["timestamp"])
            
            # Extract additional information
            entry["ip_addresses"] = self.patterns['ip_address'].findall(line)
            
            parsed_entries.append(entry)
        
        return parsed_entries
    
    def _detect_log_format(self, line: str) -> str:
        """Auto-detect log format"""
        for format_name, pattern in self.patterns.items():
            if format_name in ['apache_common', 'apache_combined', 'nginx', 'syslog']:
                if pattern.search(line):
                    return format_name
        return 'unknown'
    
    def _detect_log_level(self, line: str) -> str:
        """Detect log level from line"""
        line_lower = line.lower()
        
        if any(word in line_lower for word in ['error', 'err', 'critical', 'crit', 'fatal']):
            return 'ERROR'
        elif any(word in line_lower for word in ['warn', 'warning']):
            return 'WARNING'
        elif any(word in line_lower for word in ['info', 'information']):
            return 'INFO'
        elif any(word in line_lower for word in ['debug', 'dbg']):
            return 'DEBUG'
        else:
            return 'UNKNOWN'
    
    def _filter_by_pattern(self, entries: List[Dict[str, Any]], pattern: str) -> List[Dict[str, Any]]:
        """Filter log entries by pattern"""
        try:
            # Try as regex first
            regex_pattern = re.compile(pattern, re.IGNORECASE)
            return [entry for entry in entries if regex_pattern.search(entry["raw_line"])]
        except re.error:
            # Fall back to simple string matching
            pattern_lower = pattern.lower()
            return [entry for entry in entries if pattern_lower in entry["raw_line"].lower()]
    
    def _parse_time_range(self, time_range: str) -> datetime:
        """Parse time range string (e.g., '1h', '24h', '7d')"""
        import re
        
        match = re.match(r'(\d+)([hdw])', time_range.lower())
        if not match:
            raise ValueError(f"Invalid time range format: {time_range}")
        
        value, unit = match.groups()
        value = int(value)
        
        now = datetime.now()
        
        if unit == 'h':
            return now - timedelta(hours=value)
        elif unit == 'd':
            return now - timedelta(days=value)
        elif unit == 'w':
            return now - timedelta(weeks=value)
        else:
            raise ValueError(f"Unsupported time unit: {unit}")
    
    def _is_line_in_time_range(self, line: str, time_threshold: datetime) -> bool:
        """Check if log line is within time range"""
        # Try to extract timestamp from line
        timestamp_match = self.patterns['timestamp_iso'].search(line)
        if not timestamp_match:
            timestamp_match = self.patterns['timestamp_common'].search(line)
        
        if timestamp_match:
            try:
                timestamp = self._parse_timestamp(timestamp_match.group())
                return timestamp >= time_threshold
            except:
                pass
        
        return True  # Include line if we can't parse timestamp
    
    def _parse_timestamp(self, timestamp_str: str) -> Optional[datetime]:
        """Parse various timestamp formats"""
        # Common timestamp formats
        formats = [
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%dT%H:%M:%S',
            '%d/%b/%Y:%H:%M:%S',
            '%b %d %H:%M:%S',
            '%Y-%m-%d %H:%M:%S.%f',
            '%Y-%m-%dT%H:%M:%S.%f'
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(timestamp_str.strip(), fmt)
            except ValueError:
                continue
        
        return None
    
    def _generate_stats(self, entries: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate statistics from parsed log entries"""
        stats = {
            "total_entries": len(entries),
            "log_levels": {},
            "time_range": {},
            "top_ips": {},
            "status_codes": {},
            "error_patterns": [],
            "summary": {}
        }
        
        timestamps = []
        
        for entry in entries:
            # Log level distribution
            level = entry.get("level", "UNKNOWN")
            stats["log_levels"][level] = stats["log_levels"].get(level, 0) + 1
            
            # Collect timestamps
            if entry.get("timestamp"):
                timestamps.append(entry["timestamp"])
            
            # IP address frequency
            for ip in entry.get("ip_addresses", []):
                stats["top_ips"][ip] = stats["top_ips"].get(ip, 0) + 1
            
            # HTTP status codes (if parsed)
            if "status" in entry.get("parsed", {}):
                status = entry["parsed"]["status"]
                stats["status_codes"][status] = stats["status_codes"].get(status, 0) + 1
            
            # Error pattern detection
            if level == "ERROR":
                stats["error_patterns"].append({
                    "line": entry["line_number"],
                    "message": entry["raw_line"][:200]  # Truncate long lines
                })
        
        # Time range analysis
        if timestamps:
            timestamps.sort()
            stats["time_range"] = {
                "earliest": timestamps[0].isoformat(),
                "latest": timestamps[-1].isoformat(),
                "span_hours": (timestamps[-1] - timestamps[0]).total_seconds() / 3600
            }
        
        # Sort and limit top items
        stats["top_ips"] = dict(sorted(stats["top_ips"].items(), key=lambda x: x[1], reverse=True)[:10])
        stats["error_patterns"] = stats["error_patterns"][:20]  # Limit error patterns
        
        # Generate summary
        stats["summary"] = {
            "most_common_level": max(stats["log_levels"].items(), key=lambda x: x[1])[0] if stats["log_levels"] else "UNKNOWN",
            "error_rate": stats["log_levels"].get("ERROR", 0) / len(entries) * 100 if entries else 0,
            "unique_ips": len(stats["top_ips"]),
            "has_errors": stats["log_levels"].get("ERROR", 0) > 0
        }
        
        return stats

    async def tail_log(self, log_path: str, lines: int = 50) -> Dict[str, Any]:
        """Get last N lines from log file (like tail command)"""
        
        if not os.path.exists(log_path):
            raise FileNotFoundError(f"Log file not found: {log_path}")
        
        try:
            with open(log_path, 'r', encoding='utf-8', errors='replace') as f:
                tail_lines = self._tail_file(f, lines)
            
            return {
                "log_path": log_path,
                "lines_returned": len(tail_lines),
                "lines": tail_lines,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to tail log {log_path}: {e}")
            raise
    
    async def search_logs(self, log_path: str, search_term: str, **kwargs) -> Dict[str, Any]:
        """Search for specific terms in log files"""
        
        context_lines = kwargs.get('context_lines', 2)
        max_results = kwargs.get('max_results', 100)
        case_sensitive = kwargs.get('case_sensitive', False)
        
        if not os.path.exists(log_path):
            raise FileNotFoundError(f"Log file not found: {log_path}")
        
        matches = []
        
        try:
            with open(log_path, 'r', encoding='utf-8', errors='replace') as f:
                lines = f.readlines()
            
            search_pattern = search_term if case_sensitive else search_term.lower()
            
            for i, line in enumerate(lines):
                search_line = line if case_sensitive else line.lower()
                
                if search_pattern in search_line:
                    # Get context lines
                    start_idx = max(0, i - context_lines)
                    end_idx = min(len(lines), i + context_lines + 1)
                    
                    context = {
                        "line_number": i + 1,
                        "matching_line": line.strip(),
                        "context_before": [lines[j].strip() for j in range(start_idx, i)],
                        "context_after": [lines[j].strip() for j in range(i + 1, end_idx)]
                    }
                    
                    matches.append(context)
                    
                    if len(matches) >= max_results:
                        break
            
            return {
                "log_path": log_path,
                "search_term": search_term,
                "total_matches": len(matches),
                "matches": matches,
                "search_options": {
                    "case_sensitive": case_sensitive,
                    "context_lines": context_lines,
                    "max_results": max_results
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to search log {log_path}: {e}")
            raise