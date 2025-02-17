#!/usr/bin/env python3

import psutil
import platform
import logging
from typing import Dict, Any
from pathlib import Path

class SystemMetricsCollector:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger("SystemMetricsCollector")

    def check_cpu(self) -> Dict[str, Any]:
        """Check CPU usage and temperature."""
        metrics = {}
        
        try:
            # CPU Usage (using interval=None to get instant reading like Task Manager)
            total_cpu = psutil.cpu_percent(interval=None)
            cpu_config = self.config["cpu"]
            
            status = "normal"
            if total_cpu >= cpu_config["critical_threshold"]:
                status = "critical"
            elif total_cpu >= cpu_config["warning_threshold"]:
                status = "warning"
                
            metrics["usage"] = {
                "value": total_cpu,
                "status": status,
                "message": f"CPU usage is at {total_cpu}%"
            }
            
            # CPU Temperature (if available)
            if hasattr(psutil, "sensors_temperatures"):
                temps = psutil.sensors_temperatures()
                if temps:
                    # Get the highest temperature from any CPU core
                    max_temp = max(
                        temp.current
                        for sensor_name, entries in temps.items()
                        for temp in entries
                        if "cpu" in sensor_name.lower()
                    )
                    
                    temp_status = "normal"
                    if max_temp >= cpu_config["temperature_critical"]:
                        temp_status = "critical"
                    elif max_temp >= cpu_config["temperature_warning"]:
                        temp_status = "warning"
                        
                    metrics["temperature"] = {
                        "value": max_temp,
                        "status": temp_status,
                        "message": f"CPU temperature is at {max_temp}°C"
                    }
                    
        except Exception as e:
            self.logger.error(f"Error checking CPU metrics: {str(e)}")
            metrics["error"] = {
                "status": "error",
                "message": f"Failed to check CPU metrics: {str(e)}"
            }
            
        return metrics

    def check_memory(self) -> Dict[str, Any]:
        """Check memory usage including RAM and swap."""
        metrics = {}
        
        try:
            # RAM Usage
            memory = psutil.virtual_memory()
            memory_config = self.config["memory"]
            
            status = "normal"
            if memory.percent >= memory_config["critical_threshold"]:
                status = "critical"
            elif memory.percent >= memory_config["warning_threshold"]:
                status = "warning"
                
            metrics["ram"] = {
                "value": memory.percent,
                "total": memory.total,
                "available": memory.available,
                "status": status,
                "message": f"Memory usage is at {memory.percent}%"
            }
            
            # Swap Usage
            swap = psutil.swap_memory()
            if swap.total > 0:  # Only check if swap is enabled
                swap_percent = swap.percent
                swap_status = "normal"
                
                if swap_percent >= memory_config["swap_critical_threshold"]:
                    swap_status = "critical"
                elif swap_percent >= memory_config["swap_warning_threshold"]:
                    swap_status = "warning"
                    
                metrics["swap"] = {
                    "value": swap_percent,
                    "total": swap.total,
                    "used": swap.used,
                    "status": swap_status,
                    "message": f"Swap usage is at {swap_percent}%"
                }
                
        except Exception as e:
            self.logger.error(f"Error checking memory metrics: {str(e)}")
            metrics["error"] = {
                "status": "error",
                "message": f"Failed to check memory metrics: {str(e)}"
            }
            
        return metrics

    def check_disk(self) -> Dict[str, Any]:
        """Check disk usage for configured paths."""
        metrics = {}
        disk_config = self.config["disk"]
        
        try:
            for path in disk_config["monitored_paths"]:
                if not Path(path).exists():
                    continue
                    
                usage = psutil.disk_usage(path)
                status = "normal"
                
                if usage.percent >= disk_config["critical_threshold"]:
                    status = "critical"
                elif usage.percent >= disk_config["warning_threshold"]:
                    status = "warning"
                    
                metrics[path] = {
                    "value": usage.percent,
                    "total": usage.total,
                    "used": usage.used,
                    "free": usage.free,
                    "status": status,
                    "message": f"Disk usage for {path} is at {usage.percent}%"
                }
                
            # Check disk I/O
            disk_io = psutil.disk_io_counters()
            if disk_io:
                metrics["io"] = {
                    "read_bytes": disk_io.read_bytes,
                    "write_bytes": disk_io.write_bytes,
                    "read_count": disk_io.read_count,
                    "write_count": disk_io.write_count,
                    "status": "normal",  # IO stats are for information only
                    "message": "Disk I/O statistics collected"
                }
                
        except Exception as e:
            self.logger.error(f"Error checking disk metrics: {str(e)}")
            metrics["error"] = {
                "status": "error",
                "message": f"Failed to check disk metrics: {str(e)}"
            }
            
        return metrics

    def get_system_info(self) -> Dict[str, Any]:
        """Get general system information."""
        try:
            # Get CPU information
            cpu_info = ""
            try:
                import cpuinfo
                cpu_info = cpuinfo.get_cpu_info()['brand_raw']
            except:
                cpu_info = platform.processor()

            # Get memory information
            memory = psutil.virtual_memory()
            
            # Get disk information
            disk = psutil.disk_usage('/')
            
            return {
                "platform": platform.system(),
                "platform_release": platform.release(),
                "platform_version": platform.version(),
                "architecture": platform.machine(),
                "processor": cpu_info,
                "physical_cores": psutil.cpu_count(logical=False),
                "total_cores": psutil.cpu_count(logical=True),
                "memory_total": memory.total,
                "memory_available": memory.available,
                "disk_total": disk.total,
                "disk_used": disk.used,
                "disk_free": disk.free,
                "boot_time": psutil.boot_time(),
                "python_version": platform.python_version(),
                "hostname": platform.node()
            }
        except Exception as e:
            self.logger.error(f"Error getting system information: {str(e)}")
            return {
                "error": f"Failed to get system information: {str(e)}"
            } 