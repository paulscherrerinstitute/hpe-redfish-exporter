#!/usr/bin/env python3

import redfish
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
    client = redfish.redfish_client(
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
    #for node in members:
    #    node_url = node.get("@odata.id")
    #    node_info = safe_get(client, node_url)
    #    if node_info is None or node_info.status != 200:
    #        continue

    #    node_id = node_info.dict.get("Id", "unknown")
    #    node_name = node_info.dict.get("Name", node_id)

    #    # Health
    #    health = node_info.dict.get("Status", {}).get("Health", "Unknown")
    #    health_value = 1 if health.lower() == "ok" else 0
    #    metrics.append(
    #        f'clustorstor_node_health{prom_kv({"node": node_id, "health": health})} {health_value}'
    #    )

    #    # Power state if present
    #    power_state = node_info.dict.get("PowerState", "Unknown")
    #    metrics.append(
    #        f'clustorstor_node_power_state{prom_kv({"node": node_id, "state": power_state})} 1'
    #    )

    #    # Network interfaces (if present)
    #    nics_url = node_info.dict.get("NetworkInterfaces", {}).get("@odata.id")
    #    if nics_url:
    #        nics = safe_get(client, nics_url)
    #        if nics and nics.status == 200:
    #            for nic_member in nics.dict.get("Members", []):
    #                nic_url = nic_member.get("@odata.id")
    #                nic_info = safe_get(client, nic_url)
    #                if nic_info:
    #                    nic_id = nic_info.dict.get("Id", "nic")
    #                    link_status = nic_info.dict.get("Status", {}).get("Health", "Unknown")
    #                    link_val = 1 if link_status.lower() == "ok" else 0
    #                    metrics.append(
    #                        f'clustorstor_node_nic_health{prom_kv({"node": node_id, "nic": nic_id, "health": link_status})} {link_val}'
    #                    )

    # --------------------------------------------------------------------------
    # STORAGE CAPACITY VIA Swordfish Storage endpoint
    # /redfish/v1/StorageServices/...  (Swordfish schemas)  [1](https://github.com/grafana/alloy)
    # --------------------------------------------------------------------------

    storage_root = safe_get(client, "/redfish/v1/StorageServices")
    if storage_root and storage_root.status == 200:
        for store in storage_root.dict.get("Members", []):
            store_url = store.get("@odata.id")
            store_info = safe_get(client, store_url)
            if store_info is None:
                continue

            store_id = store_info.dict.get("Id")
            # should be an array but returns a dict
            fs_url = store_info.dict.get("FileSystems").get("@odata.id")
            fs_info = safe_get(client, fs_url)
            if fs_info is None:
                continue

            for fs_member in fs_info.dict.get("Members", []):
                fs_member_url = fs_member.get("@odata.id")
                fs_member_info = safe_get(client, fs_member_url)
                if fs_member_info is None:
                    continue

                fs_member_id = fs_member_info.dict.get("Id")
                if "FSYS" in fs_member_id:
                    # shared storage for management nodes
                    continue

                # get lustre MDT/OST metrics
                lustre_fs_info = fs_member_info.dict.get("Oem").get("Lustre")
                lustre_fs_name = lustre_fs_info.get("FsName", "unknown")
                lustre_target = lustre_fs_info.get("TargetName", "unknown")
                lustre_target_type = lustre_fs_info.get("TargetType", "unknown")
                lustre_stats = lustre_fs_info.get("Statistics")

                metrics.append(
                        f'clustorstor_lustre_filesystem_metric{prom_kv({"filesystem": lustre_fs_name, "target": lustre_target, "type": lustre_target_type})} 0'
                )

    # --------------------------------------------------------------------------
    # EVENT SERVICE HISTORY (runtime-only event list) [2](https://deepwiki.com/grafana/Building-OpenTelemetry-and-Prometheus-native-telemetry-pipelines-with-Grafana-Alloy/5.1-the-config.alloy-file)
    # --------------------------------------------------------------------------

    #events = safe_get(client, "/redfish/v1/Events")
    #if events and events.status == 200:
    #    event_members = events.dict.get("Members", [])
    #    metrics.append(f"clustorstor_events_total {len(event_members)}")

    #    # Count by severity
    #    sev_count = {}
    #    for event in event_members:
    #        eid = event.get("@odata.id")
    #        e_info = safe_get(client, eid)
    #        if e_info and e_info.status == 200:
    #            sev = e_info.dict.get("Severity", "Unknown")
    #            sev_count[sev] = sev_count.get(sev, 0) + 1

    #    for severity, val in sev_count.items():
    #        metrics.append(
    #            f'clustorstor_events_severity{prom_kv({"severity": severity})} {val}'
    #        )

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
    print(text)
    #return Response(text, mimetype="text/plain")

if __name__ == "__main__":
    #print(f"Starting ClusterStor Redfish Exporter on {EXPORTER_LISTEN_ADDR}:{EXPORTER_LISTEN_PORT}")
    #app.run(host=EXPORTER_LISTEN_ADDR, port=EXPORTER_LISTEN_PORT)
    metrics()
