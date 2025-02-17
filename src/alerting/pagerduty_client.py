#!/usr/bin/env python3

import logging
from typing import Dict, Any, Optional
from pdpyras import APISession, PDClientError

class PagerDutyClient:
    def __init__(self, api_key: str, service_id: str):
        self.session = APISession(api_key)
        self.service_id = service_id
        self.logger = logging.getLogger("PagerDutyClient")

    def send_alert(
        self,
        title: str,
        description: str,
        severity: str,
        custom_details: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Send an alert to PagerDuty.
        
        Args:
            title: Alert title
            description: Detailed description of the alert
            severity: One of 'critical', 'warning', 'error', 'info'
            custom_details: Optional dictionary of additional alert details
            
        Returns:
            bool: True if alert was sent successfully, False otherwise
        """
        try:
            # Normalize severity
            severity = severity.lower()
            if severity not in ['critical', 'warning', 'error', 'info']:
                severity = 'warning'
                
            # Prepare the incident data
            incident_data = {
                "incident": {
                    "type": "incident",
                    "title": title,
                    "service": {
                        "id": self.service_id,
                        "type": "service_reference"
                    },
                    "urgency": "high" if severity == "critical" else "low",
                    "body": {
                        "type": "incident_body",
                        "details": description
                    },
                    "custom_details": custom_details or {}
                }
            }
            
            # Create the incident
            response = self.session.rpost("incidents", json=incident_data)
            
            if response.ok:
                self.logger.info(f"Successfully created PagerDuty incident: {title}")
                return True
            else:
                self.logger.error(
                    f"Failed to create PagerDuty incident. Status: {response.status_code}, "
                    f"Response: {response.text}"
                )
                return False
                
        except PDClientError as e:
            self.logger.error(f"PagerDuty API error: {str(e)}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error sending PagerDuty alert: {str(e)}")
            return False

    def resolve_incident(self, incident_id: str) -> bool:
        """
        Resolve a PagerDuty incident.
        
        Args:
            incident_id: The ID of the incident to resolve
            
        Returns:
            bool: True if incident was resolved successfully, False otherwise
        """
        try:
            update_data = {
                "incident": {
                    "type": "incident_reference",
                    "status": "resolved"
                }
            }
            
            response = self.session.rput(f"incidents/{incident_id}", json=update_data)
            
            if response.ok:
                self.logger.info(f"Successfully resolved PagerDuty incident: {incident_id}")
                return True
            else:
                self.logger.error(
                    f"Failed to resolve PagerDuty incident. Status: {response.status_code}, "
                    f"Response: {response.text}"
                )
                return False
                
        except PDClientError as e:
            self.logger.error(f"PagerDuty API error: {str(e)}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error resolving PagerDuty incident: {str(e)}")
            return False

    def get_open_incidents(self) -> list:
        """
        Get a list of all open incidents for the service.
        
        Returns:
            list: List of open incidents
        """
        try:
            params = {
                "service_ids[]": self.service_id,
                "statuses[]": ["triggered", "acknowledged"],
                "sort_by": "created_at:desc"
            }
            
            response = self.session.rget("incidents", params=params)
            
            # Handle the response properly
            if isinstance(response, dict) and "incidents" in response:
                return response["incidents"]
            elif isinstance(response, list):
                return response
            else:
                self.logger.error(f"Unexpected response format from PagerDuty API: {response}")
                return []
                
        except PDClientError as e:
            self.logger.error(f"PagerDuty API error: {str(e)}")
            return []
        except Exception as e:
            self.logger.error(f"Unexpected error getting open incidents: {str(e)}")
            return []

    def acknowledge_incident(self, incident_id: str) -> bool:
        """
        Acknowledge a PagerDuty incident.
        
        Args:
            incident_id: The ID of the incident to acknowledge
            
        Returns:
            bool: True if incident was acknowledged successfully, False otherwise
        """
        try:
            update_data = {
                "incident": {
                    "type": "incident_reference",
                    "status": "acknowledged"
                }
            }
            
            response = self.session.rput(f"incidents/{incident_id}", json=update_data)
            
            if response.ok:
                self.logger.info(f"Successfully acknowledged PagerDuty incident: {incident_id}")
                return True
            else:
                self.logger.error(
                    f"Failed to acknowledge PagerDuty incident. Status: {response.status_code}, "
                    f"Response: {response.text}"
                )
                return False
                
        except PDClientError as e:
            self.logger.error(f"PagerDuty API error: {str(e)}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error acknowledging PagerDuty incident: {str(e)}")
            return False 