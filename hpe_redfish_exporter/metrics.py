"""
Metrics collection for HPE Redfish Exporter
"""

from typing import List, Dict, Any, Optional, Callable, Tuple, Final
from .redfish_client import RedfishClientWrapper
from .utils import prom_kv, clean_metric_name
from .config import Config
from concurrent.futures import ThreadPoolExecutor, as_completed
import itertools
import threading
import time

LUSTRE_STAT_NAME_MAP: Final[Dict[str, str]] = {
    "Max (24 hour) aggregated all OST(s) read_bytes": "24_hrs_read_bytes",
    "Max (24 hour) aggregated all OST(s) write_bytes": "24_hrs_write_bytes",
    "Total FS Space Available": "fs_avail_space",
    "Total Available FS Space Percentage": "fs_avail_space_percent",
    "Total FS Space": "fs_space",
    "Total FS Space Used": "fs_used_space",
    "Total FS MD ops": "fs_metadata_ops",
    "Total FS Read": "fs_read_ops",
    "Total FS Write": "fd_write_ops"
}

class ResponseCache:
    """Cache for top-level Redfish API responses"""

    def __init__(self, ttl: int = 30):
        self.ttl = ttl
        self._cache: Dict[str, Tuple[Any, float]] = {}
        self._lock = threading.Lock()

    def get(self, url: str) -> Optional[Any]:
        """Get cached response if not expired"""
        with self._lock:
            if url in self._cache:
                response, timestamp = self._cache[url]
                if time.time() - timestamp < self.ttl:
                    return response
                else:
                    del self._cache[url]
        return None

    def set(self, url: str, response: Any):
        """Cache a response"""
        with self._lock:
            self._cache[url] = (response, time.time())

    def invalidate(self, url: str):
        """Invalidate a cached entry"""
        with self._lock:
            if url in self._cache:
                del self._cache[url]


class ParallelFetcher:
    """Helper for parallel API fetching with rate limiting"""

    def __init__(
        self,
        client: RedfishClientWrapper,
        max_workers: int = 20,
        debug_timing: bool = False,
    ):
        self.client = client
        self.max_workers = max_workers
        self.debug_timing = debug_timing
        self._fetch_errors = 0
        self._lock = threading.Lock()

    def fetch(
        self,
        urls: List[str],
        callback: Callable[[str, Any], Optional[Any]],
        progress_label: str = "items",
    ) -> List[Any]:
        """Fetch URLs in parallel, calling callback on each result"""
        results: List[Any] = []
        self._fetch_errors = 0

        if not urls:
            return results

        semaphore = threading.Semaphore(self.max_workers)

        def fetch_with_semaphore(url: str) -> Tuple[str, Any, float]:
            with semaphore:
                start = time.time()
                try:
                    result = self.client.safe_get(url)
                    elapsed = time.time() - start
                    if result is None or result.status != 200:
                        with self._lock:
                            self._fetch_errors += 1
                        if self.debug_timing:
                            print(f"[WARNING] Failed to fetch {url}")
                    return (url, result, elapsed)
                except Exception as e:
                    with self._lock:
                        self._fetch_errors += 1
                    if self.debug_timing:
                        print(f"[WARNING] Exception fetching {url}: {e}")
                    return (url, None, time.time() - start)

        total_start = time.time()

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {executor.submit(fetch_with_semaphore, url): url for url in urls}

            completed = 0
            for future in as_completed(futures):
                url, result, elapsed = future.result()
                processed = callback(url, result)
                if processed:
                    results.append(processed)
                completed += 1
                if self.debug_timing and completed % 50 == 0:
                    print(f"[TIMING]   {progress_label}: {completed}/{len(urls)}")

            total_elapsed = time.time() - total_start
            if self.debug_timing:
                print(
                    f"[TIMING]   {progress_label}: {total_elapsed:.2f}s ({len(urls)} items, {self._fetch_errors} errors)"
                )

        return results

    def get_error_count(self) -> int:
        """Get number of fetch errors from last fetch operation"""
        return self._fetch_errors


class MetricsCollector:
    """Collect metrics from HPE Redfish API"""

    def __init__(self, config: Config):
        self.config = config
        self.debug_timing = config.debug_timing
        self.client_wrapper = RedfishClientWrapper(
            base_url=config.redfish_host,
            username=config.username,
            password=config.password,
        )
        self.cache = ResponseCache(ttl=config.cache_ttl)
        self._parallel_fetcher = ParallelFetcher(
            self.client_wrapper,
            max_workers=self.config.parallel_workers,
            debug_timing=self.debug_timing,
        )
        self._metrics: List[str] = []
        self._unique_metric: set[str] = set()
        self._unique_metric_help: set[str] = set()

    def _add_metric(
        self,
        metric: str,
        value: float,
        metric_type: Optional[str] = None,
        help_text: Optional[str] = None
    ):
        """Append metrics information for later emitting"""
        if metric in self._unique_metric:
            raise Exception(f"Repeat of metric name: {metric}!")

        # capture the name of the metric
        name = metric.split('{', maxsplit=1)[0]

        if name not in self._unique_metric_help:
            if help_text:
                self._metrics.append(f"# HELP {name} {help_text}")
            if metric_type:
                self._metrics.append(f"# TYPE {name} {metric_type}")
            self._unique_metric_help.add(name)

        self._metrics.append(f"{metric} {value}")
        self._unique_metric.add(metric)

    def collect(self) -> str:
        """Collect all metrics and return as Prometheus format"""
        # reset lists and sets
        del self._metrics[:]
        self._unique_metric.clear()
        self._unique_metric_help.clear()

        now = int(time.time())

        # Connect to Redfish API
        if not self.client_wrapper.connect():
            self._add_metric(
                "hpe_redfish_up", 0, "gauge", "Whether the Redfish API is reachable"
            )
            return "\n".join(self._metrics)

        self._add_metric(
            "hpe_redfish_up", 1, "gauge", "Whether the Redfish API is reachable"
        )

        start_total = time.time()

        # Collect storage system metrics
        start = time.time()
        self._collect_storage_systems()
        if self.debug_timing:
            print(f"[TIMING] Storage systems: {time.time() - start:.2f}s")

        # Collect Lustre filesystem metrics
        start = time.time()
        self._collect_lustre_metrics()
        if self.debug_timing:
            print(f"[TIMING] Lustre metrics: {time.time() - start:.2f}s")

        # Collect event service metrics
        start = time.time()
        self._collect_events()
        if self.debug_timing:
            print(f"[TIMING] Events: {time.time() - start:.2f}s")

        # Add fetch error metric
        total_errors = self._parallel_fetcher.get_error_count()
        if total_errors > 0:
            self._add_metric(
                "hpe_redfish_clusterstor_fetch_errors_total", total_errors, "counter", "Total failed API fetches"
            )

        if self.debug_timing:
            print(f"[TIMING] Total collection: {time.time() - start:.2f}s")

        # Logout
        self.client_wrapper.logout()

        return "\n".join(self._metrics)

    def _get_cached(self, url: str) -> Optional[Any]:
        """Get from cache or fetch from API"""
        cached = self.cache.get(url)
        if cached is not None:
            return cached
        result = self.client_wrapper.safe_get(url)
        if result:
            self.cache.set(url, result)
        return result

    def _collect_storage_systems(self):
        """Collect storage system metrics"""
        ss = self._get_cached("/redfish/v1/StorageSystems")
        if ss is None or ss.status != 200:
            self._add_metric(
                "hpe_redfish_clusterstor_storage_systems_up",
                0,
                "gauge",
                "Storage systems availability",
            )
            return

        self._add_metric(
            "hpe_redfish_clusterstor_storage_systems_up",
            1,
            "gauge",
            "Storage systems availability"
        )

        members = ss.dict.get("Members", [])
        self._add_metric(
            "hpe_redfish_clusterstor_nodes_total",
            len(members),
            "counter",
            "Number of storage nodes"
        )

        # Get all node URLs
        node_urls = [node.get("@odata.id") for node in members if "@odata.id" in node]

        # Parallel fetch nodes
        def process_node(url: str, result: Any) -> Optional[Dict]:
            if result is None or result.status != 200:
                return None
            return {"url": url, "data": result.dict}

        node_results = self._parallel_fetcher.fetch(
            node_urls, process_node, "storage_nodes"
        )

        # Process node results
        for node_data in node_results:
            data = node_data["data"]
            node_id = data.get("Id", "unknown")
            node_name = data.get("Name", node_id)
            node_hostname = data.get("HostName", "unknown")
            node_serial_number = data.get("SerialNumber", "unknown")

            # shared labels
            labels = {
                'node': node_id,
                'hostname': node_hostname,
                'serialnumber': node_serial_number,
            }

            # Health status (already collected, but include for completeness)
            health = data.get("Status", {}).get("Health", "Unknown")
            health_value = 1 if health.lower() == "ok" else 0
            self._add_metric(
                f"hpe_redfish_clusterstor_node_health{prom_kv({**labels, 'health': health})}",
                health_value,
                "gauge",
                "Node health status (1=OK, 0=other)"
            )

            # Power state
            power_state = data.get("PowerState", "Unknown")
            self._add_metric(
                f"hpe_redfish_clusterstor_node_power_state{prom_kv({**labels, 'state': power_state})}",
                1,
                "gauge",
                "Node power state"
            )

            # Try to get Linux statistics from Oem section
            oem_data = data.get("Oem", {})
            linux_stats = oem_data.get("LinuxStats", {})

            def sanitize(value: str) -> float:
                if "(%)" in value:
                    _tmp_value = value.replace(" (%)", "")
                elif "(GB)" in value:
                    value_format = value.replace(" (GB)", "")
                    _tmp_value = str(float(value_format) * (2**10) ** 3)  # into bytes
                elif "(m)" in value:
                    _tmp_value = value.replace(" (m)", "")
                else:
                    _tmp_value = value

                return float(_tmp_value)

            if linux_stats:
                # CPU metrics
                cpu_util = linux_stats.get("CPUUtilization")
                if cpu_util is not None:
                    self._add_metric(
                        f"hpe_redfish_clusterstor_node_cpu_utilization_percent{prom_kv(labels)}",
                        sanitize(cpu_util),
                        "gauge",
                        "CPU utilization percentage"
                    )

                # Memory metrics
                if "MemoryUtilization" in linux_stats:
                    self._add_metric(
                        f"hpe_redfish_clusterstor_node_memoryutilization_percent{prom_kv(labels)}",
                        sanitize(linux_stats['MemoryUtilization']),
                        "gauge",
                        "Memory utilization percentage"
                    )

                for mem_metric in [
                    ("AvailableMemory", "gauge", "Available memory in bytes"),
                    ("TotalMemory", "gauge", "Total memory in bytes")
                ]:
                    if mem_metric[0] in linux_stats:
                        self._add_metric(
                            f"hpe_redfish_clusterstor_node_{mem_metric[0].lower()}_bytes{prom_kv(labels)}",
                            sanitize(linux_stats[mem_metric[0]]),
                            mem_metric[1],
                            mem_metric[2]
                        )

                # Load averages
                for load_metric in [
                    "LoadAverage1m",
                    "LoadAverage5m",
                    "LoadAverage15m",
                ]:
                    if load_metric in linux_stats:
                        self._add_metric(
                            f"hpe_redfish_clusterstor_node_{load_metric.lower()}{prom_kv(labels)}",
                            sanitize(linux_stats[load_metric]),
                            "gauge",
                            "System load averages"
                        )

    def _collect_lustre_metrics(self):
        """Collect Lustre filesystem metrics"""
        storage_root = self._get_cached("/redfish/v1/StorageServices")
        if storage_root is None or storage_root.status != 200:
            return

        # Get all storage services and their filesystems
        fs_member_urls: List[str] = []
        fs_storage_ids: set[str] = set()
        fs_lustre_ids: set[str] = set()

        for store in storage_root.dict.get("Members", []):
            store_url = store.get("@odata.id")
            if store_url:
                store_info = self.client_wrapper.safe_get(store_url)
                if store_info is None or store_info.status != 200:
                    continue
            else:
                # capture Redfish storage ID for LustreFS
                fs_lustre_url = store.get("Lustre Filesystem")
                if fs_lustre_url:
                    fs_storage_ids.add(fs_lustre_url.rsplit('/', 1)[-1])
                continue

            store_id = store_info.dict.get("Id")
            fs_url = store_info.dict.get("FileSystems", {}).get("@odata.id")
            if not fs_url:
                continue

            fs_info = self.client_wrapper.safe_get(fs_url)
            if fs_info is None or fs_info.status != 200:
                continue

            for fs_member in fs_info.dict.get("Members", []):
                fs_member_url = fs_member.get("@odata.id")
                if fs_member_url:
                    fs_member_urls.append(fs_member_url)


        # Parallel fetch all filesystems
        def process_fs(url: str, result: Any) -> Optional[Dict]:
            if result is None or result.status != 200:
                return None
            return {"url": url, "data": result.dict}

        fs_member_results = self._parallel_fetcher.fetch(
            fs_member_urls, process_fs, "filesystems"
        )

        # Process filesystem results
        unique_fs_members: set[str] = set()
        for fs_member_data in fs_member_results:
            data = fs_member_data["data"]
            fs_member_id = data.get("Id")

            if "FSYS" in fs_member_id:
                # shared storage for management nodes
                continue
            elif fs_member_id in unique_fs_members:
                # skip as we have already seen this OST/MDT
                continue

            # Get lustre MDT/OST metrics
            lustre_fs_oem_info = data.get("Oem", {})
            lustre_fs_info = lustre_fs_oem_info.get("Lustre", {})
            lustre_fs_name = lustre_fs_info.get("FsName")
            if lustre_fs_name:
                fs_lustre_ids.add(lustre_fs_name)
            else:
                # XXX maybe we should issue a warning?
                lustre_fs_name = "unknown"
            lustre_target = lustre_fs_info.get("TargetName", "unknown")
            lustre_target_type = lustre_fs_info.get("TargetType", "unknown")
            lustre_target_hostname = lustre_fs_oem_info.get("Hostname", "unknown")
            lustre_stats = lustre_fs_info.get("Statistics", {})

            # Collect individual target metrics (IOPS, bandwidth, etc.)
            if lustre_stats:
                for stat_key, stat_value in lustre_stats.items():
                    # Parse statistics in format like "OST0000 read" or "MDT0000 free_space"
                    try:
                        # Extract metric name (all parts after the target identifier)
                        parts = stat_key.split()
                        if len(parts) >= 2:
                            # Join all parts after the first one (target identifier) to get full metric name
                            metric_name = "_".join(parts[1:])

                            # Clean up metric name for Prometheus
                            clean_metric_name_result = clean_metric_name(metric_name)

                            # Convert string value to numeric
                            numeric_value = float(stat_value)

                            # Shared labels for metrics
                            labels = {
                                "filesystem": lustre_fs_name,
                                "target": lustre_target,
                                "hostname": lustre_target_hostname,
                                "type": lustre_target_type,
                            }

                            # Create generic metric with unique labels
                            self._add_metric(
                                f"hpe_redfish_clusterstor_lustre_metric{prom_kv({**labels, "metric": clean_metric_name_result})}",
                                numeric_value,
                                "gauge",
                                "Generic Lustre metric with all labels"
                            )

                            # Also create specific metrics for common operations
                            if clean_metric_name_result in ["read", "write"]:
                                self._add_metric(
                                    f"hpe_redfish_clusterstor_lustre_{clean_metric_name_result}_ops_total{prom_kv(labels)}",
                                    numeric_value,
                                    "counter",
                                    f"Cumulative {clean_metric_name_result} operations"
                                )
                            elif clean_metric_name_result in [
                                "free_space",
                                "total_space",
                                "used_space",
                                "available_space",
                            ]:
                                self._add_metric(
                                    f"hpe_redfish_clusterstor_lustre_{clean_metric_name_result}_bytes{prom_kv(labels)}",
                                    numeric_value,
                                    "gauge",
                                    f"{clean_metric_name_result.capitalize().replace('_', ' ')} in bytes"
                                )
                            elif clean_metric_name_result in [
                                "free_inodes",
                                "total_inodes",
                                "used_inodes",
                            ]:
                                self._add_metric(
                                    f"hpe_redfish_clusterstor_lustre_{clean_metric_name_result}{prom_kv(labels)}",
                                    numeric_value,
                                    "gauge",
                                    f"{clean_metric_name_result.capitalize().replace('_', ' ')} count"
                                )
                            elif clean_metric_name_result == "num_exports":
                                self._add_metric(
                                    f"hpe_redfish_clusterstor_lustre_exports{prom_kv(labels)}",
                                    numeric_value,
                                    "gauge",
                                    "Number of exports"
                                )
                            elif clean_metric_name_result == "percent_free_space":
                                self._add_metric(
                                    f"hpe_redfish_clusterstor_lustre_free_space_percent{prom_kv(labels)}",
                                    numeric_value,
                                    "gauge",
                                    "Free space percentage"
                                )

                    except (ValueError, IndexError):
                        # Skip malformed or non-numeric statistics
                        # TODO we should log this
                        continue

            unique_fs_members.add(fs_member_id)

        # capture Lustre filesystem-level stats
        for storage_id, fs_name in itertools.product(fs_storage_ids, fs_lustre_ids):
            fs_lustre_url = f'/redfish/v1/StorageServices/{storage_id}/FileSystems/{fs_name}'
            fs_lustre_info = self.client_wrapper.safe_get(fs_lustre_url)
            if fs_lustre_info is None or fs_lustre_info.status != 200:
                continue

            fs_lustre_oem = fs_lustre_info.dict.get("Oem", {})
            fs_lustre_info = fs_lustre_oem.get("Lustre", {})
            fs_lustre_stats = fs_lustre_info.get("Statistics", {})

            if fs_lustre_stats:
                for stat_key, stat_value in fs_lustre_stats.items():
                    try:
                        # re-format metrics label
                        metric_name = LUSTRE_STAT_NAME_MAP[stat_key]

                        # Clean up metric name for Prometheus
                        clean_metric_name_result = clean_metric_name(metric_name)

                        # Convert string value to numeric
                        numeric_value = float(stat_value)

                        # Create appropriate Prometheus metric based on metric type
                        labels = {
                            "filesystem": fs_name,
                            "storage_id": storage_id,
                        }

                        # Create generic metric with unique labels
                        self._add_metric(
                            f"hpe_redfish_clusterstor_lustre_metric{prom_kv({**labels, "metric": clean_metric_name_result})}",
                            numeric_value,
                            "guage",
                            "Generic Lustre metric with all labels"
                        )

                        # Also create specific metrics for common operations
                        if "_percent" in clean_metric_name_result:
                            self._add_metric(
                                f"hpe_redfish_clusterstor_lustre_{clean_metric_name_result}{prom_kv(labels)}",
                                numeric_value,
                                "gauge",
                                f"gauge of {clean_metric_name_result} percentage"
                            )
                        else:
                            self._add_metric(
                                f"hpe_redfish_clusterstor_lustre_{clean_metric_name_result}{prom_kv(labels)}",
                                numeric_value,
                                "gauge",
                                f"gauge of {clean_metric_name_result}"
                            )
                    except (ValueError, IndexError):
                        # Skip malformed or non-numeric statistics
                        # TODO we should log this
                        continue

    def _collect_events(self):
        """Collect event service history metrics"""
        events = self._get_cached("/redfish/v1/Events")
        if events is None or events.status != 200:
            return

        event_members = events.dict.get("Members", [])

        # Apply limit if configured
        if self.config.events_limit and len(event_members) > self.config.events_limit:
            event_members = event_members[-self.config.events_limit :]

        self._add_metric(
            "hpe_redfish_clusterstor_events_total",
            len(event_members),
            "counter",
            "Total number of events"
        )

        # Get all event URLs
        event_urls = [e.get("@odata.id") for e in event_members if "@odata.id" in e]

        # Parallel fetch events
        def process_event(url: str, result: Any) -> Optional[str]:
            if result and result.status == 200:
                # Get the event object
                event_data = result.dict

                # Note that not every API call include this field
                event_msgs_count = event_data.get("Events@odata.count", 1)

                # Get array of message(s)
                event_msgs = event_data.get("Events", [])

                # The API docs indicate that there should only ever be one message
                if event_msgs_count != 1 and len(event_msgs) != event_msgs_count:
                    return None

                # Get severity from the event data
                return event_msgs[0].get("Severity", "Unknown")
            return None

        severities = self._parallel_fetcher.fetch(event_urls, process_event, "events")

        # Count by severity
        sev_count: Dict[str, int] = {}
        for severity in severities:
            if severity:
                sev_count[severity] = sev_count.get(severity, 0) + 1

        for severity, val in sev_count.items():
            self._add_metric(
                f"hpe_redfish_clusterstor_events_severity{prom_kv({'severity': severity})}",
                val,
                "gauge",
                "Events count by severity"
            )
