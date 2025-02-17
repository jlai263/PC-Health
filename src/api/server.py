#!/usr/bin/env python3

import asyncio
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any, List
import logging
import threading

app = FastAPI(title="PC Health Monitor API")
logger = logging.getLogger("API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000", "http://127.0.0.1:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variable to store the monitor instance
monitor = None

def start_api_server(monitor_instance):
    """Start the API server in a separate thread."""
    global monitor
    monitor = monitor_instance
    
    def run_server():
        import uvicorn
        host = monitor.config.get("api", {}).get("host", "127.0.0.1")
        port = monitor.config.get("api", {}).get("port", 8001)
        uvicorn.run(app, host=host, port=port)
    
    thread = threading.Thread(target=run_server, daemon=True)
    thread.start()

@app.get("/health")
async def health_check():
    """Simple health check endpoint."""
    return {"status": "healthy"}

@app.get("/metrics")
async def get_metrics():
    """Get current system metrics."""
    if not monitor:
        raise HTTPException(status_code=500, detail="Monitor not initialized")
    
    try:
        return {
            "cpu": monitor.metrics_collector.check_cpu(),
            "memory": monitor.metrics_collector.check_memory(),
            "disk": monitor.metrics_collector.check_disk()
        }
    except Exception as e:
        logger.error(f"Error getting metrics: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/processes")
async def get_processes():
    """Get list of running processes."""
    if not monitor:
        raise HTTPException(status_code=500, detail="Monitor not initialized")
    
    try:
        return monitor.process_monitor.get_all_processes()
    except Exception as e:
        logger.error(f"Error getting processes: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/process/{pid}")
async def get_process_details(pid: int):
    """Get detailed information about a specific process."""
    if not monitor:
        raise HTTPException(status_code=500, detail="Monitor not initialized")
    
    try:
        details = monitor.process_monitor.get_process_details(pid)
        if "error" in details:
            raise HTTPException(status_code=404, detail=details["error"])
        return details
    except Exception as e:
        logger.error(f"Error getting process details: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/alerts")
async def get_alerts():
    """Get current alerts."""
    if not monitor:
        raise HTTPException(status_code=500, detail="Monitor not initialized")
    
    try:
        if monitor.alerting:
            return monitor.alerting.get_open_incidents()
        return []
    except Exception as e:
        logger.error(f"Error getting alerts: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/process/{pid}/kill")
async def kill_process(pid: int):
    """Kill a specific process."""
    if not monitor:
        raise HTTPException(status_code=500, detail="Monitor not initialized")
    
    try:
        success = monitor.process_monitor.kill_process(pid)
        if success:
            return {"status": "success", "message": f"Process {pid} killed"}
        else:
            raise HTTPException(status_code=400, detail=f"Failed to kill process {pid}")
    except Exception as e:
        logger.error(f"Error killing process: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/system")
async def get_system_info():
    """Get system information."""
    if not monitor:
        raise HTTPException(status_code=500, detail="Monitor not initialized")
    
    try:
        return monitor.metrics_collector.get_system_info()
    except Exception as e:
        logger.error(f"Error getting system info: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/alerts/{incident_id}/acknowledge")
async def acknowledge_alert(incident_id: str):
    """Acknowledge a specific alert."""
    if not monitor or not monitor.alerting:
        raise HTTPException(status_code=500, detail="Alerting not configured")
    
    try:
        success = monitor.alerting.acknowledge_incident(incident_id)
        if success:
            return {"status": "success", "message": f"Alert {incident_id} acknowledged"}
        else:
            raise HTTPException(status_code=400, detail=f"Failed to acknowledge alert {incident_id}")
    except Exception as e:
        logger.error(f"Error acknowledging alert: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/alerts/{incident_id}/resolve")
async def resolve_alert(incident_id: str):
    """Resolve a specific alert."""
    if not monitor or not monitor.alerting:
        raise HTTPException(status_code=500, detail="Alerting not configured")
    
    try:
        success = monitor.alerting.resolve_incident(incident_id)
        if success:
            return {"status": "success", "message": f"Alert {incident_id} resolved"}
        else:
            raise HTTPException(status_code=400, detail=f"Failed to resolve alert {incident_id}")
    except Exception as e:
        logger.error(f"Error resolving alert: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) 