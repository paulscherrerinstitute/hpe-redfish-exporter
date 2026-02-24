#!/usr/bin/env python3

from redfish import redfish_client
import requests
from flask import Flask, Response
import urllib3
import time

# Disable warnings for self-signed certificate Redfish endpoints
#urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ------------------------------------------------------------------------------
# CONFIGURATION
# ------------------------------------------------------------------------------

REDFISH_HOST = "https://localhost:8081"
USERNAME     = "your-username"
PASSWORD     = "your-password"

# Prometheus exporter HTTP server
EXPORTER_LISTEN_ADDR = "127.0.0.1"
EXPORTER_LISTEN_PORT = 9223


# ------------------------------------------------------------------------------
# REDFISH CLIENT SETUP
# ------------------------------------------------------------------------------

def get_client():
    client = redfish_client(
        base_url=REDFISH_HOST,
        username=USERNAME,
        password=PASSWORD,
        default_prefix="/redfish/v1",
        timeout=10
    )
    client.login(auth="session")
    return client


# ------------------------------------------------------------------------------
# HELPERS
# ------------------------------------------------------------------------------

def prom_kv(label_dict):
    parts = [f'{k}="{v}"' for k, v in label_dict.items()]
    return "{" + ",".join(parts) + "}" if parts else ""


def safe_get(client, path):
    try:
        return client.get(path)
    except Exception:
        return None


# ------------------------------------------------------------------------------
# METRIC COLLECTION
# ------------------------------------------------------------------------------

def collect_metrics():

    metrics = []
    now = int(time.time())

    try:
        client = get_client()
    except Exception:
        return "redfish_up 0\n"

    metrics.append("redfish_up 1")

    # --------------------------------------------------------------------------
    # STORAGE SYSTEM COLLECTION
    # /redfish/v1/StorageSystems            (Cluster root) [1](https://github.com/grafana/alloy)
    # --------------------------------------------------------------------------

    ss = safe_get(client, "/redfish/v1/StorageSystems")
    if ss is None or ss.status != 200:
        metrics.append("clustorstor_storage_systems_up 0")
        return "\n".join(metrics)

    metrics.append("clustorstor_storage_systems_up 1")

    members = ss.dict.get("Members", [])
    metrics.append(f"clustorstor_nodes_count {len(members)}")

    # Loop each storage system node
    for node in members:
        node_url = node.get("@odata.id")
        node_info = safe_get(client, node_url)
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
            nics = safe_get(client, nics_url)
            if nics and nics.status == 200:
                for nic_member in nics.dict.get("Members", []):
                    nic_url = nic_member.get("@odata.id")
                    nic_info = safe_get(client, nic_url)
                    if nic_info:
                        nic_id = nic_info.dict.get("Id", "nic")
                        link_status = nic_info.dict.get("Status", {}).get("Health", "Unknown")
                        link_val = 1 if link_status.lower() == "ok" else 0
                        metrics.append(
                            f'clustorstor_node_nic_health{prom_kv({"node": node_id, "nic": nic_id, "health": link_status})} {link_val}'
                        )

    # --------------------------------------------------------------------------
    # LUSTRE FILESYSTEM METRICS
    # /redfish/v1/StorageServices/.../FileSystems  (Lustre specific metrics)
    # --------------------------------------------------------------------------

    storage_root = safe_get(client, "/redfish/v1/StorageServices")
    if storage_root and storage_root.status == 200:
        for store in storage_root.dict.get("Members", []):
            store_url = store.get("@odata.id")
            store_info = safe_get(client, store_url)
            if store_info is None or store_info.status != 200:
                continue

            store_id = store_info.dict.get("Id")
            # Get filesystem collection
            fs_url = store_info.dict.get("FileSystems", {}).get("@odata.id")
            if not fs_url:
                continue
                
            fs_info = safe_get(client, fs_url)
            if fs_info is None or fs_info.status != 200:
                continue

            for fs_member in fs_info.dict.get("Members", []):
                fs_member_url = fs_member.get("@odata.id")
                fs_member_info = safe_get(client, fs_member_url)
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
                                clean_metric_name = metric_name.lower().replace("(", "").replace(")", "").replace("-", "_").replace(" ", "_")
                                
                                # Convert string value to numeric
                                numeric_value = float(stat_value)
                                
                                # Create appropriate Prometheus metric based on metric type
                                labels = {
                                    "filesystem": lustre_fs_name,
                                    "target": lustre_target,
                                    "type": lustre_target_type,
                                    "metric": clean_metric_name
                                }
                                
                                metrics.append(
                                    f'clustorstor_lustre_metric{prom_kv(labels)} {numeric_value}'
                                )
                                
                                # Also create specific metrics for common operations
                                if clean_metric_name in ['read', 'write']:
                                    metrics.append(
                                        f'clustorstor_lustre_{clean_metric_name}_ops{prom_kv({"filesystem": lustre_fs_name, "target": lustre_target, "type": lustre_target_type})} {numeric_value}'
                                    )
                                elif clean_metric_name in ['free_space', 'total_space', 'used_space', 'available_space']:
                                    metrics.append(
                                        f'clustorstor_lustre_{clean_metric_name}_bytes{prom_kv({"filesystem": lustre_fs_name, "target": lustre_target, "type": lustre_target_type})} {numeric_value}'
                                    )
                                elif clean_metric_name in ['free_inodes', 'total_inodes', 'used_inodes']:
                                    metrics.append(
                                        f'clustorstor_lustre_{clean_metric_name}{prom_kv({"filesystem": lustre_fs_name, "target": lustre_target, "type": lustre_target_type})} {numeric_value}'
                                    )
                                elif clean_metric_name == 'num_exports':
                                    metrics.append(
                                        f'clustorstor_lustre_exports{prom_kv({"filesystem": lustre_fs_name, "target": lustre_target, "type": lustre_target_type})} {numeric_value}'
                                    )
                                elif clean_metric_name == 'percent_free_space':
                                    metrics.append(
                                        f'clustorstor_lustre_free_space_percent{prom_kv({"filesystem": lustre_fs_name, "target": lustre_target, "type": lustre_target_type})} {numeric_value}'
                                    )
                                
                        except (ValueError, IndexError):
                            # Skip malformed or non-numeric statistics
                            continue

    # --------------------------------------------------------------------------
    # TELEMETRY SERVICE - LUSTRE AND LINUX STATISTICS
    # /redfish/v1/TelemetryService/MetricReportDefinitions
    # --------------------------------------------------------------------------

    # Get LustreStats metric report
    lustre_metrics_report = safe_get(client, "/redfish/v1/TelemetryService/MetricReportDefinitions/LustreStats")
    if lustre_metrics_report and lustre_metrics_report.status == 200:
        # This would require subscription to get actual metric values
        # For now, we'll use the individual filesystem approach above
        pass

    # Get LinuxStats metric report for node status
    linux_metrics_report = safe_get(client, "/redfish/v1/TelemetryService/MetricReportDefinitions/LinuxStats")
    if linux_metrics_report and linux_metrics_report.status == 200:
        # This would require subscription to get actual metric values
        # We'll try to get node metrics from StorageSystems instead
        pass

    # --------------------------------------------------------------------------
    # NODE STATUS AND SYSTEM LOAD
    # /redfish/v1/StorageSystems  (Node-level metrics)
    # --------------------------------------------------------------------------

    ss = safe_get(client, "/redfish/v1/StorageSystems")
    if ss is not None and ss.status == 200:
        members = ss.dict.get("Members", [])
        
        for node in members:
            node_url = node.get("@odata.id")
            node_info = safe_get(client, node_url)
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

    # --------------------------------------------------------------------------
    # EVENT SERVICE HISTORY (runtime-only event list)
    # --------------------------------------------------------------------------

    events = safe_get(client, "/redfish/v1/Events")
    if events and events.status == 200:
        event_members = events.dict.get("Members", [])
        metrics.append(f"clustorstor_events_total {len(event_members)}")

        # Count by severity
        sev_count = {}
        for event in event_members:
            eid = event.get("@odata.id")
            e_info = safe_get(client, eid)
            if e_info and e_info.status == 200:
                sev = e_info.dict.get("Severity", "Unknown")
                sev_count[sev] = sev_count.get(sev, 0) + 1

        for severity, val in sev_count.items():
            metrics.append(
                f'clustorstor_events_severity{prom_kv({"severity": severity})} {val}'
            )

    # Clean logout
    try:
        client.logout()
    except Exception:
        pass

    return "\n".join(metrics)


# ------------------------------------------------------------------------------
# PROMETHEUS EXPORTER WEB SERVER
# ------------------------------------------------------------------------------

app = Flask(__name__)

@app.route("/metrics")
def metrics():
    text = collect_metrics()
    return Response(text, mimetype="text/plain")

if __name__ == "__main__":
    print(f"Starting ClusterStor Redfish Exporter on {EXPORTER_LISTEN_ADDR}:{EXPORTER_LISTEN_PORT}")
    app.run(host=EXPORTER_LISTEN_ADDR, port=EXPORTER_LISTEN_PORT)
