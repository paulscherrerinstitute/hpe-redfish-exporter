"""
Configuration handling for HPE Redfish Exporter
"""

import json
import os
from typing import Optional, Dict, Any


class Config:
    """Configuration management for HPE Redfish Exporter"""
    
    def __init__(
        self,
        redfish_host: str = "https://localhost:8081",
        exporter_addr: str = "127.0.0.1",
        exporter_port: int = 9223,
        auth_file: str = ".hpe_redfish_auth"
    ):
        self.redfish_host = redfish_host
        self.exporter_addr = exporter_addr
        self.exporter_port = exporter_port
        self.auth_file = auth_file
        self.username: Optional[str] = None
        self.password: Optional[str] = None
        
    def load_credentials(self) -> bool:
        """Load credentials from auth file"""
        try:
            if not os.path.exists(self.auth_file):
                print(f"ERROR: Auth file {self.auth_file} not found")
                return False
                
            with open(self.auth_file, 'r') as f:
                auth_data = json.load(f)
                self.username = auth_data.get('username', '')
                self.password = auth_data.get('password', '')
                
            if not self.username or not self.password:
                raise ValueError("Missing username or password in auth file")
                
            return True
            
        except json.JSONDecodeError:
            print(f"ERROR: Invalid JSON format in {self.auth_file}")
            return False
        except Exception as e:
            print(f"ERROR: Failed to load credentials: {e}")
            return False

    def validate(self) -> bool:
        """Validate configuration"""
        if not self.username or not self.password:
            return False
        return True

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary"""
        return {
            'redfish_host': self.redfish_host,
            'exporter_addr': self.exporter_addr,
            'exporter_port': self.exporter_port,
            'auth_file': self.auth_file
        }