"""
Utility functions for HPE Redfish Exporter
"""

from typing import Dict, Any


def prom_kv(label_dict: Dict[str, Any]) -> str:
    """Convert dictionary to Prometheus label format"""
    parts = [f'{k}="{v}"' for k, v in label_dict.items()]
    return "{" + ",".join(parts) + "}" if parts else ""


def clean_metric_name(name: str) -> str:
    """Clean metric name for Prometheus compatibility"""
    return (
        name.lower()
        .replace("(", "")
        .replace(")", "")
        .replace("-", "_")
        .replace(" ", "_")
    )
