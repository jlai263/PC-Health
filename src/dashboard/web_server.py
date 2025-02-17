#!/usr/bin/env python3

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pathlib import Path
import logging
from typing import Dict, Any
import json
import asyncio
from datetime import datetime

app = FastAPI(title="PC Health Monitor Dashboard")
logger = logging.getLogger("Dashboard")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8001", "http://127.0.0.1:8001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variable to store the monitor instance
monitor = None

def start_dashboard(monitor_instance):
    """Start the dashboard web server."""
    global monitor
    monitor = monitor_instance
    
    host = monitor.config["dashboard"]["host"]
    port = monitor.config["dashboard"]["port"]
    api_host = monitor.config.get("api", {}).get("host", "127.0.0.1")
    api_port = monitor.config.get("api", {}).get("port", 8001)
    
    # Mount static files
    static_dir = Path(__file__).parent / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    
    # Start the server
    try:
        uvicorn.run(app, host=host, port=port)
    except Exception as e:
        logger.error(f"Failed to start dashboard server: {str(e)}")

@app.get("/", response_class=HTMLResponse)
async def get_dashboard():
    """Render the main dashboard page."""
    api_host = monitor.config.get("api", {}).get("host", "127.0.0.1")
    api_port = monitor.config.get("api", {}).get("port", 8001)
    api_base_url = f"http://{api_host}:{api_port}"
    
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>PC Health Monitor</title>
        <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    </head>
    <body class="bg-gray-100">
        <div class="container mx-auto px-4 py-8">
            <h1 class="text-3xl font-bold mb-8">PC Health Monitor</h1>
            
            <!-- System Info -->
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
                <div class="bg-white rounded-lg shadow p-4">
                    <h2 class="text-lg font-semibold mb-2">CPU Usage</h2>
                    <div class="text-2xl font-bold" id="cpu-usage">Loading...</div>
                    <canvas id="cpu-chart" class="mt-4"></canvas>
                </div>
                
                <div class="bg-white rounded-lg shadow p-4">
                    <h2 class="text-lg font-semibold mb-2">Memory Usage</h2>
                    <div class="text-2xl font-bold" id="memory-usage">Loading...</div>
                    <canvas id="memory-chart" class="mt-4"></canvas>
                </div>
                
                <div class="bg-white rounded-lg shadow p-4">
                    <h2 class="text-lg font-semibold mb-2">Disk Usage</h2>
                    <div class="text-2xl font-bold" id="disk-usage">Loading...</div>
                    <canvas id="disk-chart" class="mt-4"></canvas>
                </div>
                
                <div class="bg-white rounded-lg shadow p-4">
                    <h2 class="text-lg font-semibold mb-2">System Info</h2>
                    <div id="system-info" class="text-sm">Loading...</div>
                </div>
            </div>
            
            <!-- Error Alert -->
            <div id="error-alert" class="hidden bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative mb-4" role="alert">
                <strong class="font-bold">Error!</strong>
                <span id="error-message" class="block sm:inline"></span>
            </div>
            
            <!-- Processes -->
            <div class="bg-white rounded-lg shadow p-4 mb-8">
                <h2 class="text-lg font-semibold mb-4">Top Processes</h2>
                <div class="overflow-x-auto">
                    <table class="min-w-full table-auto">
                        <thead>
                            <tr class="bg-gray-100">
                                <th class="px-4 py-2">PID</th>
                                <th class="px-4 py-2">Name</th>
                                <th class="px-4 py-2">CPU %</th>
                                <th class="px-4 py-2">Memory %</th>
                                <th class="px-4 py-2">Status</th>
                            </tr>
                        </thead>
                        <tbody id="process-list">
                            <tr><td colspan="5" class="text-center py-4">Loading...</td></tr>
                        </tbody>
                    </table>
                </div>
            </div>
            
            <!-- Alerts -->
            <div class="bg-white rounded-lg shadow p-4">
                <h2 class="text-lg font-semibold mb-4">Recent Alerts</h2>
                <div id="alerts-list" class="space-y-4">
                    <div class="text-center py-4">Loading...</div>
                </div>
            </div>
        </div>
        
        <script>
            const API_BASE_URL = '""" + api_base_url + """';
            
            // Show error message
            function showError(message) {
                const errorAlert = document.getElementById('error-alert');
                const errorMessage = document.getElementById('error-message');
                errorMessage.textContent = message;
                errorAlert.classList.remove('hidden');
            }
            
            // Hide error message
            function hideError() {
                const errorAlert = document.getElementById('error-alert');
                errorAlert.classList.add('hidden');
            }
            
            // Initialize charts
            const createChart = (ctx, label) => {
                return new Chart(ctx, {
                    type: 'line',
                    data: {
                        labels: [],
                        datasets: [{
                            label: label,
                            data: [],
                            borderColor: 'rgb(75, 192, 192)',
                            tension: 0.1
                        }]
                    },
                    options: {
                        responsive: true,
                        scales: {
                            y: {
                                beginAtZero: true,
                                max: 100
                            }
                        }
                    }
                });
            };
            
            const cpuChart = createChart(document.getElementById('cpu-chart').getContext('2d'), 'CPU %');
            const memoryChart = createChart(document.getElementById('memory-chart').getContext('2d'), 'Memory %');
            const diskChart = createChart(document.getElementById('disk-chart').getContext('2d'), 'Disk %');
            
            // Update data
            const updateData = async () => {
                try {
                    hideError();
                    
                    const metrics = await fetch(`${API_BASE_URL}/metrics`).then(r => {
                        if (!r.ok) throw new Error(`Failed to fetch metrics: ${r.status}`);
                        return r.json();
                    });
                    
                    const processes = await fetch(`${API_BASE_URL}/processes`).then(r => {
                        if (!r.ok) throw new Error(`Failed to fetch processes: ${r.status}`);
                        return r.json();
                    });
                    
                    const alerts = await fetch(`${API_BASE_URL}/alerts`).then(r => {
                        if (!r.ok) throw new Error(`Failed to fetch alerts: ${r.status}`);
                        return r.json();
                    });
                    
                    // Update metrics
                    document.getElementById('cpu-usage').innerHTML = `
                        <div class="text-2xl font-bold">${metrics.cpu.usage.value.toFixed(1)}%</div>
                    `;
                    document.getElementById('memory-usage').textContent = `${metrics.memory.ram.value.toFixed(1)}%`;
                    document.getElementById('disk-usage').textContent = 
                        `${(Object.values(metrics.disk).find(d => d.value)?.value || 0).toFixed(1)}%`;

                    // Update system info
                    const sysInfo = await fetch(`${API_BASE_URL}/system`).then(r => {
                        if (!r.ok) throw new Error(`Failed to fetch system info: ${r.status}`);
                        return r.json();
                    });

                    // Format memory in GB
                    const memoryGB = (sysInfo.memory_total / (1024 * 1024 * 1024)).toFixed(2);
                    const bootTime = new Date(sysInfo.boot_time * 1000).toLocaleString('en-US', { 
                        timeZone: Intl.DateTimeFormat().resolvedOptions().timeZone 
                    });

                    document.getElementById('system-info').innerHTML = `
                        <div class="space-y-2">
                            <div><strong>OS:</strong> ${sysInfo.platform} ${sysInfo.platform_release}</div>
                            <div><strong>CPU:</strong> ${sysInfo.processor}</div>
                            <div><strong>Cores:</strong> ${sysInfo.physical_cores} Physical / ${sysInfo.total_cores} Logical</div>
                            <div><strong>Memory:</strong> ${memoryGB} GB</div>
                            <div><strong>Boot Time:</strong> ${bootTime}</div>
                        </div>
                    `;
                    
                    // Update charts
                    const timestamp = new Date().toLocaleTimeString();
                    
                    [cpuChart, memoryChart, diskChart].forEach(chart => {
                        if (chart.data.labels.length > 20) {
                            chart.data.labels.shift();
                            chart.data.datasets[0].data.shift();
                        }
                    });
                    
                    cpuChart.data.labels.push(timestamp);
                    cpuChart.data.datasets[0].data.push(metrics.cpu.usage.value);
                    cpuChart.update();
                    
                    memoryChart.data.labels.push(timestamp);
                    memoryChart.data.datasets[0].data.push(metrics.memory.ram.value);
                    memoryChart.update();
                    
                    const diskValue = Object.values(metrics.disk).find(d => d.value)?.value || 0;
                    diskChart.data.labels.push(timestamp);
                    diskChart.data.datasets[0].data.push(diskValue);
                    diskChart.update();
                    
                    // Update process list
                    document.getElementById('process-list').innerHTML = processes
                        .slice(0, 10)
                        .map(p => `
                            <tr class="hover:bg-gray-50">
                                <td class="px-4 py-2">${p.pid}</td>
                                <td class="px-4 py-2">${p.name}</td>
                                <td class="px-4 py-2">${p.cpu_percent.toFixed(1)}%</td>
                                <td class="px-4 py-2">${p.memory_percent.toFixed(1)}%</td>
                                <td class="px-4 py-2">${p.status}</td>
                            </tr>
                        `)
                        .join('');
                    
                    // Update alerts
                    document.getElementById('alerts-list').innerHTML = alerts.length > 0 ?
                        alerts
                        .slice(0, 5)
                        .map(a => `
                            <div class="p-4 ${a.severity === 'critical' ? 'bg-red-100' : 'bg-yellow-100'} rounded">
                                <div class="font-semibold">${a.title}</div>
                                <div class="text-sm">${a.description}</div>
                                <div class="text-xs text-gray-600 mt-1">
                                    Severity: ${a.severity}
                                    ${a.created_at ? ` • Created: ${new Date(a.created_at).toLocaleString()}` : ''}
                                </div>
                            </div>
                        `)
                        .join('') : '<div class="text-center py-4">No active alerts</div>';
                        
                } catch (error) {
                    console.error('Error updating dashboard:', error);
                    showError(error.message);
                }
            };
            
            // Update every 5 seconds
            setInterval(updateData, 5000);
            updateData();
        </script>
    </body>
    </html>
    """
    return html_content

@app.get("/api/metrics")
async def get_metrics():
    """Get current system metrics."""
    if not monitor:
        raise HTTPException(status_code=500, detail="Monitor not initialized")
    
    try:
        cpu_metrics = monitor.metrics_collector.check_cpu()
        memory_metrics = monitor.metrics_collector.check_memory()
        disk_metrics = monitor.metrics_collector.check_disk()
        
        return {
            "cpu": cpu_metrics,
            "memory": memory_metrics,
            "disk": disk_metrics
        }
    except Exception as e:
        logger.error(f"Error getting metrics: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/processes")
async def get_processes():
    """Get list of running processes."""
    if not monitor:
        raise HTTPException(status_code=500, detail="Monitor not initialized")
    
    try:
        return monitor.process_monitor.get_all_processes()
    except Exception as e:
        logger.error(f"Error getting processes: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/alerts")
async def get_alerts():
    """Get recent alerts."""
    if not monitor:
        raise HTTPException(status_code=500, detail="Monitor not initialized")
    
    try:
        if monitor.alerting:
            return monitor.alerting.get_open_incidents()
        return []
    except Exception as e:
        logger.error(f"Error getting alerts: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/system")
async def get_system_info():
    """Get system information."""
    if not monitor:
        raise HTTPException(status_code=500, detail="Monitor not initialized")
    
    try:
        return monitor.metrics_collector.get_system_info()
    except Exception as e:
        logger.error(f"Error getting system info: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) 