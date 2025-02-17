#!/usr/bin/env python3

import psutil
import logging
from typing import Dict, Any, List

class ProcessMonitor:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger("ProcessMonitor")
        self.watch_list = config.get("watch_list", [])

    def check_processes(self) -> List[Dict[str, Any]]:
        """Check resource usage of watched processes."""
        issues = []
        
        try:
            # Get all running processes
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                try:
                    proc_info = proc.info
                    proc_name = proc_info['name'].lower()
                    
                    # Check if this process is in our watch list
                    for watched_proc in self.watch_list:
                        if watched_proc["name"].lower() in proc_name:
                            # Check CPU usage
                            if proc_info['cpu_percent'] > watched_proc["max_cpu_percent"]:
                                issues.append({
                                    "title": f"High CPU Usage: {proc_name}",
                                    "description": (
                                        f"Process {proc_name} (PID: {proc_info['pid']}) "
                                        f"is using {proc_info['cpu_percent']}% CPU, "
                                        f"exceeding threshold of {watched_proc['max_cpu_percent']}%"
                                    ),
                                    "severity": "warning"
                                })
                                
                            # Check memory usage
                            if proc_info['memory_percent'] > watched_proc["max_memory_percent"]:
                                issues.append({
                                    "title": f"High Memory Usage: {proc_name}",
                                    "description": (
                                        f"Process {proc_name} (PID: {proc_info['pid']}) "
                                        f"is using {proc_info['memory_percent']:.1f}% memory, "
                                        f"exceeding threshold of {watched_proc['max_memory_percent']}%"
                                    ),
                                    "severity": "warning"
                                })
                                
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
                    
        except Exception as e:
            self.logger.error(f"Error monitoring processes: {str(e)}")
            issues.append({
                "title": "Process Monitoring Error",
                "description": f"Failed to monitor processes: {str(e)}",
                "severity": "error"
            })
            
        return issues

    def get_process_details(self, pid: int) -> Dict[str, Any]:
        """Get detailed information about a specific process."""
        try:
            proc = psutil.Process(pid)
            cpu_count = psutil.cpu_count() or 1
            
            with proc.oneshot():
                cpu_percent = proc.cpu_percent() / cpu_count if proc.cpu_percent() is not None else 0
                return {
                    "pid": pid,
                    "name": proc.name(),
                    "status": proc.status(),
                    "cpu_percent": cpu_percent,
                    "memory_percent": proc.memory_percent(),
                    "memory_info": dict(proc.memory_info()._asdict()),
                    "num_threads": proc.num_threads(),
                    "username": proc.username(),
                    "create_time": proc.create_time(),
                    "cmdline": proc.cmdline(),
                    "connections": len(proc.connections()),
                    "open_files": len(proc.open_files()),
                    "nice": proc.nice(),
                    "io_counters": dict(proc.io_counters()._asdict()) if hasattr(proc, "io_counters") else None
                }
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess) as e:
            self.logger.error(f"Error getting process details for PID {pid}: {str(e)}")
            return {
                "error": f"Failed to get process details: {str(e)}"
            }

    def get_all_processes(self) -> List[Dict[str, Any]]:
        """Get a list of all running processes with basic information."""
        processes = []
        try:
            # Get the number of CPU cores for normalization
            cpu_count = psutil.cpu_count() or 1
            
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'status']):
                try:
                    proc_info = proc.info
                    
                    # Skip the System Idle Process
                    if proc_info["pid"] == 0:
                        continue
                        
                    # Normalize CPU percentage to total CPU capacity
                    # If a process uses 2 cores fully (200%), it should show as 25% on an 8-core system
                    cpu_percent = proc_info["cpu_percent"] / cpu_count if proc_info["cpu_percent"] is not None else 0
                    
                    processes.append({
                        "pid": proc_info["pid"],
                        "name": proc_info["name"],
                        "cpu_percent": cpu_percent,
                        "memory_percent": proc_info["memory_percent"] or 0,
                        "status": proc_info["status"]
                    })
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
        except Exception as e:
            self.logger.error(f"Error listing all processes: {str(e)}")
            return []
            
        return sorted(processes, key=lambda x: x["cpu_percent"], reverse=True)

    def kill_process(self, pid: int) -> bool:
        """Attempt to kill a process by PID."""
        try:
            proc = psutil.Process(pid)
            proc.kill()
            return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess) as e:
            self.logger.error(f"Error killing process {pid}: {str(e)}")
            return False 