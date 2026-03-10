"""
HPE Redfish Exporter - Prometheus exporter for HPE ClusterStor systems

This package provides a Prometheus exporter that collects metrics from HPE
ClusterStor systems using the Redfish API.
"""

from .core import HPERedfishExporter
from .cli import main
from .config import Config

__version__ = "2.4.0"
__author__ = "HPE ClusterStor Exporter Team"
__license__ = "MIT"

# Export main components
__all__ = ["HPERedfishExporter", "main", "Config"]
