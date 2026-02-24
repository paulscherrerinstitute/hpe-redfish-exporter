"""
Metrics collection for HPE Redfish Exporter
"""

from typing import List, Dict, Any, Optional
from .redfish_client import RedfishClientWrapper
from .utils import prom_kv, clean_metric_name
import time


class MetricsCollector:
    """Collect metrics from HPE Redfish API"""
    
    def __init__(self, config: 'Config'):
        from .config import Config
        self.config = config
        self.client_wrapper = RedfishClientWrapper(
            base_url=config.redfish_host,
            username=config.username or "",
            password=config.password or ""
        )
        
    def collect(self) -> str:
        """Collect all metrics and return as Prometheus format"""
        metrics = []
        now = int(time.time())
        
        # Connect to Redfish API
        if not self.client_wrapper.connect():
            return "redfish_up 0\n"
            
        metrics.append("redfish_up 1")
        
        # Collect storage system metrics
        self._collect_storage_systems(metrics)
        
        # Collect Lustre filesystem metrics
        self._collect_lustre_metrics(metrics)
        
        # Collect node status metrics
        self._collect_node_status(metrics)
        
        # Collect event service metrics
        self._collect_events(metrics)
        
        # Logout
        self.client_wrapper.logout()
        
        return "\n".join(metrics)
        
    def _collect_storage_systems(self, metrics: List[str]):
        """Collect storage system metrics"""
        ss = self.client_wrapper.safe_get("/redfish/v1/StorageSystems")
        if ss is None or ss.status != 200:
            metrics.append("clustorstor_storage_systems_up 0")
            return
            
        metrics.append("clustorstor_storage_systems_up 1")
        
        members = ss.dict.get("Members", [])
        metrics.append(f"clustorstor_nodes_count {len(members)}")
        
        # Loop each storage system node
        for node in members:
            node_url = node.get("@odata.id")
            node_info = self.client_wrapper.safe_get(node_url)
            if node_info is None or node_info.status != 200:
                continue
                
            node_id = node_info.dict.get("Id", "unknown")
            node_name = node_info.dict.get("Name", node_id)
            
            # Health
            health = node_info.dict.get("Status", {}).get("Health", "Unknown")
            health_value = 1 if health.lower() == "ok" else 0
            metrics.append(
                f'clustorstor_node_health{prom_kv({"node": node_id, "health": health})} {health_value}'
            )
            
            # Power state if present
            power_state = node_info.dict.get("PowerState", "Unknown")
            metrics.append(
                f'clustorstor_node_power_state{prom_kv({"node": node_id, "state": power_state})} 1'
            )
            
            # Network interfaces (if present)
            nics_url = node_info.dict.get("NetworkInterfaces", {}).get("@odata.id")
            if nics_url:
                nics = self.client_wrapper.safe_get(nics_url)
                if nics and nics.status == 200:
                    for nic_member in nics.dict.get("Members", []):
                        nic_url = nic_member.get("@odata.id")
                        nic_info = self.client_wrapper.safe_get(nic_url)
                        if nic_info:
                            nic_id = nic_info.dict.get("Id", "nic")
                            link_status = nic_info.dict.get("Status", {}).get("Health", "Unknown")
                            link_val = 1 if link_status.lower() == "ok" else 0
                            metrics.append(
                                f'clustorstor_node_nic_health{prom_kv({"node": node_id, "nic": nic_id, "health": link_status})} {link_val}'
                            )
    
    def _collect_lustre_metrics(self, metrics: List[str]):
        """Collect Lustre filesystem metrics"""
        storage_root = self.client_wrapper.safe_get("/redfish/v1/StorageServices")
        if storage_root and storage_root.status == 200:
            for store in storage_root.dict.get("Members", []):
                store_url = store.get("@odata.id")
                store_info = self.client_wrapper.safe_get(store_url)
                if store_info is None or store_info.status != 200:
                    continue
                    
                store_id = store_info.dict.get("Id")
                # Get filesystem collection
                fs_url = store_info.dict.get("FileSystems", {}).get("@odata.id")
                if not fs_url:
                    continue
                    
                fs_info = self.client_wrapper.safe_get(fs_url)
                if fs_info is None or fs_info.status != 200:
                    continue
                    
                for fs_member in fs_info.dict.get("Members", []):
                    fs_member_url = fs_member.get("@odata.id")
                    fs_member_info = self.client_wrapper.safe_get(fs_member_url)
                    if fs_member_info is None or fs_member_info.status != 200:
                        continue
                        
                    fs_member_id = fs_member_info.dict.get("Id")
                    if "FSYS" in fs_member_id:
                        # shared storage for management nodes
                        continue
                        
                    # Get lustre MDT/OST metrics
                    lustre_fs_info = fs_member_info.dict.get("Oem", {}).get("Lustre", {})
                    lustre_fs_name = lustre_fs_info.get("FsName", "unknown")
                    lustre_target = lustre_fs_info.get("TargetName", "unknown")
                    lustre_target_type = lustre_fs_info.get("TargetType", "unknown")
                    lustre_stats = lustre_fs_info.get("Statistics", {})
                    
                    # Collect individual target metrics (IOPS, bandwidth, etc.)
                    if lustre_stats and isinstance(lustre_stats, dict):
                        for stat_key, stat_value in lustre_stats.items():
                            # Parse statistics in format like "OST0000 read" or "MDT0000 free_space"
                            try:
                                # Extract metric name (all parts after the target identifier)
                                parts = stat_key.split()
                                if len(parts) >= 2:
                                    # Join all parts after the first one (target identifier) to get full metric name
                                    metric_name = "_".join(parts[1:])  # e.g., "free_inodes", "total_space"
                                    
                                    # Clean up metric name for Prometheus
                                    clean_metric_name_result = clean_metric_name(metric_name)
                                    
                                    # Convert string value to numeric
                                    numeric_value = float(stat_value)
                                    
                                    # Create appropriate Prometheus metric based on metric type
                                    labels = {
                                        "filesystem": lustre_fs_name,
                                        "target": lustre_target,
                                        "type": lustre_target_type,
                                        "metric": clean_metric_name_result
                                    }
                                    
                                    metrics.append(
                                        f'clustorstor_lustre_metric{prom_kv(labels)} {numeric_value}'
                                    )
                                    
                                    # Also create specific metrics for common operations
                                    if clean_metric_name_result in ['read', 'write']:
                                        metrics.append(
                                            f'clustorstor_lustre_{clean_metric_name_result}_ops{prom_kv({"filesystem": lustre_fs_name, "target": lustre_target, "type": lustre_target_type})} {numeric_value}'
                                        )
                                    elif clean_metric_name_result in ['free_space', 'total_space', 'used_space', 'available_space']:
                                        metrics.append(
                                            f'clustorstor_lustre_{clean_metric_name_result}_bytes{prom_kv({"filesystem": lustre_fs_name, "target": lustre_target, "type": lustre_target_type})} {numeric_value}'
                                        )
                                    elif clean_metric_name_result in ['free_inodes', 'total_inodes', 'used_inodes']:
                                        metrics.append(
                                            f'clustorstor_lustre_{clean_metric_name_result}{prom_kv({"filesystem": lustre_fs_name, "target": lustre_target, "type": lustre_target_type})} {numeric_value}'
                                        )
                                    elif clean_metric_name_result == 'num_exports':
                                        metrics.append(
                                            f'clustorstor_lustre_exports{prom_kv({"filesystem": lustre_fs_name, "target": lustre_target, "type": lustre_target_type})} {numeric_value}'
                                        )
                                    elif clean_metric_name_result == 'percent_free_space':
                                        metrics.append(
                                            f'clustorstor_lustre_free_space_percent{prom_kv({"filesystem": lustre_fs_name, "target": lustre_target, "type": lustre_target_type})} {numeric_value}'
                                        )
                                        
                            except (ValueError, IndexError):
                                # Skip malformed or non-numeric statistics
                                continue
    
    def _collect_node_status(self, metrics: List[str]):
        """Collect node status and system load metrics"""
        ss = self.client_wrapper.safe_get("/redfish/v1/StorageSystems")
        if ss is not None and ss.status == 200:
            members = ss.dict.get("Members", [])
            
            for node in members:
                node_url = node.get("@odata.id")
                node_info = self.client_wrapper.safe_get(node_url)
                if node_info is None or node_info.status != 200:
                    continue
                    
                node_id = node_info.dict.get("Id", "unknown")
                node_name = node_info.dict.get("Name", node_id)
                
                # Health status
                health = node_info.dict.get("Status", {}).get("Health", "Unknown")
                health_value = 1 if health.lower() == "ok" else 0
                metrics.append(
                    f'clustorstor_node_health{prom_kv({"node": node_id, "health": health})} {health_value}'
                )
                
                # Power state
                power_state = node_info.dict.get("PowerState", "Unknown")
                metrics.append(
                    f'clustorstor_node_power_state{prom_kv({"node": node_id, "state": power_state})} 1'
                )
                
                # Try to get Linux statistics from Oem section
                oem_data = node_info.dict.get("Oem", {}).get("Hpe", {})
                linux_stats = oem_data.get("LinuxStats", {})
                
                if linux_stats:
                    # CPU metrics
                    cpu_util = linux_stats.get("CPUUtilization")
                    if cpu_util is not None:
                        metrics.append(
                            f'clustorstor_node_cpu_utilization{prom_kv({"node": node_id})} {cpu_util}'
                        )
                    
                    # Memory metrics
                    for mem_metric in ["MemoryUtilization", "AvailableMemory", "TotalMemory"]:
                        if mem_metric in linux_stats:
                            metrics.append(
                                f'clustorstor_node_{mem_metric.lower()}{prom_kv({"node": node_id})} {linux_stats[mem_metric]}'
                            )
                    
                    # Load averages
                    for load_metric in ["LoadAverage1m", "LoadAverage5m", "LoadAverage15m"]:
                        if load_metric in linux_stats:
                            metrics.append(
                                f'clustorstor_node_{load_metric.lower()}{prom_kv({"node": node_id})} {linux_stats[load_metric]}'
                            )
    
    def _collect_events(self, metrics: List[str]):
        """Collect event service history metrics"""
        events = self.client_wrapper.safe_get("/redfish/v1/Events")
        if events and events.status == 200:
            event_members = events.dict.get("Members", [])
            metrics.append(f"clustorstor_events_total {len(event_members)}")
            
            # Count by severity
            sev_count = {}
            for event in event_members:
                eid = event.get("@odata.id")
                e_info = self.client_wrapper.safe_get(eid)
                if e_info and e_info.status == 200:
                    sev = e_info.dict.get("Severity", "Unknown")
                    sev_count[sev] = sev_count.get(sev, 0) + 1
            
            for severity, val in sev_count.items():
                metrics.append(
                    f'clustorstor_events_severity{prom_kv({"severity": severity})} {val}'
                )