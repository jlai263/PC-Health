#!/usr/bin/env python3

import os
import sys
import time
import logging
import yaml
import psutil
from pathlib import Path
from typing import Dict, Any
from datetime import datetime
import threading

# Local imports
from collectors.system_metrics import SystemMetricsCollector
from collectors.process_monitor import ProcessMonitor
from alerting.pagerduty_client import PagerDutyClient
from api.server import start_api_server
from dashboard.web_server import start_dashboard

class PCHealthMonitor:
    def __init__(self, config_path: str = "config/config.yaml"):
        self.config = self._load_config(config_path)
        self.setup_logging()
        self.metrics_collector = SystemMetricsCollector(self.config["metrics"])
        self.process_monitor = ProcessMonitor(self.config["processes"])
        self.alerting = self._setup_alerting()
        self.last_check = {}
        
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        try:
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            print(f"Error: Configuration file not found at {config_path}")
            print("Please copy config.example.yaml to config.yaml and configure it.")
            sys.exit(1)
            
    def setup_logging(self):
        """Configure logging based on settings."""
        log_config = self.config["logging"]
        log_dir = Path(os.path.dirname(log_config["file"]))
        log_dir.mkdir(parents=True, exist_ok=True)
        
        logging.basicConfig(
            level=getattr(logging, log_config["level"]),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_config["file"]),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger("PCHealthMonitor")
        
    def _setup_alerting(self) -> PagerDutyClient:
        """Initialize alerting system."""
        if self.config["alerting"]["pagerduty"]["enabled"]:
            return PagerDutyClient(
                api_key=self.config["alerting"]["pagerduty"]["api_key"],
                service_id=self.config["alerting"]["pagerduty"]["service_id"]
            )
        return None
        
    def should_check(self, metric: str, interval: int) -> bool:
        """Determine if it's time to check a specific metric."""
        now = time.time()
        if metric not in self.last_check:
            self.last_check[metric] = 0
        if now - self.last_check[metric] >= interval:
            self.last_check[metric] = now
            return True
        return False
        
    def run_checks(self):
        """Run all configured health checks."""
        try:
            # CPU checks
            if self.config["metrics"]["cpu"]["enabled"]:
                if self.should_check("cpu", self.config["metrics"]["cpu"]["check_interval"]):
                    metrics = self.metrics_collector.check_cpu()
                    self.handle_metrics("CPU", metrics)
            
            # Memory checks
            if self.config["metrics"]["memory"]["enabled"]:
                if self.should_check("memory", self.config["metrics"]["memory"]["check_interval"]):
                    metrics = self.metrics_collector.check_memory()
                    self.handle_metrics("Memory", metrics)
            
            # Disk checks
            if self.config["metrics"]["disk"]["enabled"]:
                if self.should_check("disk", self.config["metrics"]["disk"]["check_interval"]):
                    metrics = self.metrics_collector.check_disk()
                    self.handle_metrics("Disk", metrics)
            
            # Process checks
            if self.config["processes"]["enabled"]:
                if self.should_check("processes", self.config["processes"]["check_interval"]):
                    issues = self.process_monitor.check_processes()
                    for issue in issues:
                        self.handle_alert(issue)
                        
        except Exception as e:
            self.logger.error(f"Error during health checks: {str(e)}")
            
    def handle_metrics(self, category: str, metrics: Dict[str, Any]):
        """Process collected metrics and trigger alerts if necessary."""
        for metric_name, data in metrics.items():
            if data.get("status") in ["warning", "critical"]:
                # Create a more detailed alert message
                value = data.get("value", "unknown")
                threshold = (
                    self.config["metrics"][category.lower()]["critical_threshold"]
                    if data["status"] == "critical"
                    else self.config["metrics"][category.lower()]["warning_threshold"]
                )
                
                alert = {
                    "title": f"{category} Alert: {metric_name}",
                    "description": (
                        f"Current {metric_name} is {value}%, "
                        f"exceeding {data['status']} threshold of {threshold}%. "
                        f"{data.get('message', '')}"
                    ),
                    "severity": data["status"],
                    "created_at": datetime.now().isoformat()
                }
                self.handle_alert(alert)
                
    def handle_alert(self, alert: Dict[str, Any]):
        """Send alerts through configured channels."""
        self.logger.warning(f"Alert: {alert['title']} - {alert['description']}")
        
        if self.alerting and alert["severity"] == "critical":
            self.alerting.send_alert(
                title=alert["title"],
                description=alert["description"],
                severity=alert["severity"]
            )
            
    def run(self):
        """Main monitoring loop."""
        self.logger.info("Starting PC Health Monitor...")
        
        # Start API server if enabled
        if self.config["features"]["api_server"]:
            self.logger.info("Starting API server...")
            start_api_server(self)
            
        # Start dashboard if enabled
        if self.config["dashboard"]["enabled"]:
            self.logger.info("Starting dashboard...")
            # Start dashboard in a separate thread
            dashboard_thread = threading.Thread(
                target=start_dashboard,
                args=(self,),
                daemon=True
            )
            dashboard_thread.start()
            
        # Initialize CPU metrics
        psutil.cpu_percent(interval=1)  # First call to initialize CPU metrics
        
        try:
            while True:
                self.run_checks()
                time.sleep(0.5)  # Update every 500ms like Task Manager
        except KeyboardInterrupt:
            self.logger.info("Shutting down PC Health Monitor...")
            sys.exit(0)

def main():
    monitor = PCHealthMonitor()
    monitor.run()

if __name__ == "__main__":
    main() 