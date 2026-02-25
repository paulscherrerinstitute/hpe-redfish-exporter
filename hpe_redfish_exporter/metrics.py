"""
Metrics collection for HPE Redfish Exporter
"""

from typing import List, Dict, Any, Optional, Callable, Tuple
from .redfish_client import RedfishClientWrapper
from .utils import prom_kv, clean_metric_name
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import time


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
        results = []
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

    def __init__(self, config: "Config"):
        from .config import Config

        self.config = config
        self.debug_timing = config.debug_timing
        self.client_wrapper = RedfishClientWrapper(
            base_url=config.redfish_host,
            username=config.username,
            password=config.password,
        )
        self.cache = ResponseCache(ttl=config.cache_ttl)
        self._parallel_fetcher: Optional[ParallelFetcher] = None
        self._storage_systems_data: List[Dict] = []

    def collect(self) -> str:
        """Collect all metrics and return as Prometheus format"""
        metrics = []
        now = int(time.time())

        # Connect to Redfish API
        if not self.client_wrapper.connect():
            return "redfish_up 0\n"

        metrics.append("redfish_up 1")

        start_total = time.time()

        # Create parallel fetcher
        self._parallel_fetcher = ParallelFetcher(
            self.client_wrapper,
            max_workers=self.config.parallel_workers,
            debug_timing=self.debug_timing,
        )

        # Collect storage system metrics
        start = time.time()
        self._collect_storage_systems(metrics)
        if self.debug_timing:
            print(f"[TIMING] Storage systems: {time.time() - start:.2f}s")

        # Collect Lustre filesystem metrics
        start = time.time()
        self._collect_lustre_metrics(metrics)
        if self.debug_timing:
            print(f"[TIMING] Lustre metrics: {time.time() - start:.2f}s")

        # Collect node status metrics (reuse cached data from storage systems)
        start = time.time()
        self._collect_node_status(metrics)
        if self.debug_timing:
            print(f"[TIMING] Node status: {time.time() - start:.2f}s")

        # Collect event service metrics
        start = time.time()
        self._collect_events(metrics)
        if self.debug_timing:
            print(f"[TIMING] Events: {time.time() - start:.2f}s")

        # Add fetch error metric
        total_errors = self._parallel_fetcher.get_error_count()
        if total_errors > 0:
            metrics.append(f"clustorstor_fetch_errors_total {total_errors}")

        if self.debug_timing:
            print(f"[TIMING] Total collection: {time.time() - start:.2f}s")

        # Logout
        self.client_wrapper.logout()

        return "\n".join(metrics)

    def _get_cached(self, url: str) -> Optional[Any]:
        """Get from cache or fetch from API"""
        cached = self.cache.get(url)
        if cached is not None:
            return cached
        result = self.client_wrapper.safe_get(url)
        if result:
            self.cache.set(url, result)
        return result

    def _collect_storage_systems(self, metrics: List[str]):
        """Collect storage system metrics"""
        ss = self._get_cached("/redfish/v1/StorageSystems")
        if ss is None or ss.status != 200:
            metrics.append("clustorstor_storage_systems_up 0")
            return

        metrics.append("clustorstor_storage_systems_up 1")

        members = ss.dict.get("Members", [])
        metrics.append(f"clustorstor_nodes_count {len(members)}")

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

            # Health
            health = data.get("Status", {}).get("Health", "Unknown")
            health_value = 1 if health.lower() == "ok" else 0
            metrics.append(
                f"clustorstor_node_health{prom_kv({'node': node_id, 'health': health})} {health_value}"
            )

            # Power state if present
            power_state = data.get("PowerState", "Unknown")
            metrics.append(
                f"clustorstor_node_power_state{prom_kv({'node': node_id, 'state': power_state})} 1"
            )

            # Store for reuse in _collect_node_status
            self._storage_systems_data.append(data)

            # Network interfaces (if present) - also fetch in parallel
            nics_url = data.get("NetworkInterfaces", {}).get("@odata.id")
            if nics_url:
                nics = self.client_wrapper.safe_get(nics_url)
                if nics and nics.status == 200:
                    nic_urls = [
                        nic.get("@odata.id")
                        for nic in nics.dict.get("Members", [])
                        if "@odata.id" in nic
                    ]

                    def process_nic(
                        url: str, result: Any
                    ) -> Optional[Tuple[str, Dict]]:
                        if result and result.status == 200:
                            return (url, result.dict)
                        return None

                    nic_results = self._parallel_fetcher.fetch(
                        nic_urls, process_nic, "nics"
                    )

                    for nic_url, nic_data in nic_results:
                        nic_id = nic_data.get("Id", "nic")
                        link_status = nic_data.get("Status", {}).get(
                            "Health", "Unknown"
                        )
                        link_val = 1 if link_status.lower() == "ok" else 0
                        metrics.append(
                            f"clustorstor_node_nic_health{prom_kv({'node': node_id, 'nic': nic_id, 'health': link_status})} {link_val}"
                        )

    def _collect_lustre_metrics(self, metrics: List[str]):
        """Collect Lustre filesystem metrics"""
        storage_root = self._get_cached("/redfish/v1/StorageServices")
        if storage_root is None or storage_root.status != 200:
            return

        # Get all storage services and their filesystems
        filesystem_urls = []

        for store in storage_root.dict.get("Members", []):
            store_url = store.get("@odata.id")
            store_info = self.client_wrapper.safe_get(store_url)
            if store_info is None or store_info.status != 200:
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
                    filesystem_urls.append(fs_member_url)

        # Parallel fetch all filesystems
        def process_fs(url: str, result: Any) -> Optional[Dict]:
            if result is None or result.status != 200:
                return None
            return {"url": url, "data": result.dict}

        fs_results = self._parallel_fetcher.fetch(
            filesystem_urls, process_fs, "filesystems"
        )

        # Process filesystem results
        for fs_data in fs_results:
            data = fs_data["data"]
            fs_member_id = data.get("Id")

            if "FSYS" in fs_member_id:
                # shared storage for management nodes
                continue

            # Get lustre MDT/OST metrics
            lustre_fs_info = data.get("Oem", {}).get("Lustre", {})
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
                            metric_name = "_".join(parts[1:])

                            # Clean up metric name for Prometheus
                            clean_metric_name_result = clean_metric_name(metric_name)

                            # Convert string value to numeric
                            numeric_value = float(stat_value)

                            # Create appropriate Prometheus metric based on metric type
                            labels = {
                                "filesystem": lustre_fs_name,
                                "target": lustre_target,
                                "type": lustre_target_type,
                                "metric": clean_metric_name_result,
                            }

                            metrics.append(
                                f"clustorstor_lustre_metric{prom_kv(labels)} {numeric_value}"
                            )

                            # Also create specific metrics for common operations
                            if clean_metric_name_result in ["read", "write"]:
                                metrics.append(
                                    f"clustorstor_lustre_{clean_metric_name_result}_ops{prom_kv({'filesystem': lustre_fs_name, 'target': lustre_target, 'type': lustre_target_type})} {numeric_value}"
                                )
                            elif clean_metric_name_result in [
                                "free_space",
                                "total_space",
                                "used_space",
                                "available_space",
                            ]:
                                metrics.append(
                                    f"clustorstor_lustre_{clean_metric_name_result}_bytes{prom_kv({'filesystem': lustre_fs_name, 'target': lustre_target, 'type': lustre_target_type})} {numeric_value}"
                                )
                            elif clean_metric_name_result in [
                                "free_inodes",
                                "total_inodes",
                                "used_inodes",
                            ]:
                                metrics.append(
                                    f"clustorstor_lustre_{clean_metric_name_result}{prom_kv({'filesystem': lustre_fs_name, 'target': lustre_target, 'type': lustre_target_type})} {numeric_value}"
                                )
                            elif clean_metric_name_result == "num_exports":
                                metrics.append(
                                    f"clustorstor_lustre_exports{prom_kv({'filesystem': lustre_fs_name, 'target': lustre_target, 'type': lustre_target_type})} {numeric_value}"
                                )
                            elif clean_metric_name_result == "percent_free_space":
                                metrics.append(
                                    f"clustorstor_lustre_free_space_percent{prom_kv({'filesystem': lustre_fs_name, 'target': lustre_target, 'type': lustre_target_type})} {numeric_value}"
                                )

                    except (ValueError, IndexError):
                        # Skip malformed or non-numeric statistics
                        continue

    def _collect_node_status(self, metrics: List[str]):
        """Collect node status and system load metrics"""
        # Reuse data from _collect_storage_systems instead of making redundant API calls
        for data in self._storage_systems_data:
            node_id = data.get("Id", "unknown")
            node_name = data.get("Name", node_id)

            # Health status (already collected, but include for completeness)
            health = data.get("Status", {}).get("Health", "Unknown")
            health_value = 1 if health.lower() == "ok" else 0
            metrics.append(
                f"clustorstor_node_health{prom_kv({'node': node_id, 'health': health})} {health_value}"
            )

            # Power state
            power_state = data.get("PowerState", "Unknown")
            metrics.append(
                f"clustorstor_node_power_state{prom_kv({'node': node_id, 'state': power_state})} 1"
            )

            # Try to get Linux statistics from Oem section
            oem_data = data.get("Oem", {}).get("Hpe", {})
            linux_stats = oem_data.get("LinuxStats", {})

            if linux_stats:
                # CPU metrics
                cpu_util = linux_stats.get("CPUUtilization")
                if cpu_util is not None:
                    metrics.append(
                        f"clustorstor_node_cpu_utilization{prom_kv({'node': node_id})} {cpu_util}"
                    )

                # Memory metrics
                for mem_metric in [
                    "MemoryUtilization",
                    "AvailableMemory",
                    "TotalMemory",
                ]:
                    if mem_metric in linux_stats:
                        metrics.append(
                            f"clustorstor_node_{mem_metric.lower()}{prom_kv({'node': node_id})} {linux_stats[mem_metric]}"
                        )

                # Load averages
                for load_metric in [
                    "LoadAverage1m",
                    "LoadAverage5m",
                    "LoadAverage15m",
                ]:
                    if load_metric in linux_stats:
                        metrics.append(
                            f"clustorstor_node_{load_metric.lower()}{prom_kv({'node': node_id})} {linux_stats[load_metric]}"
                        )

    def _collect_events(self, metrics: List[str]):
        """Collect event service history metrics"""
        events = self._get_cached("/redfish/v1/Events")
        if events is None or events.status != 200:
            return

        event_members = events.dict.get("Members", [])

        # Apply limit if configured
        if self.config.events_limit and len(event_members) > self.config.events_limit:
            event_members = event_members[-self.config.events_limit :]

        metrics.append(f"clustorstor_events_total {len(event_members)}")

        # Get all event URLs
        event_urls = [e.get("@odata.id") for e in event_members if "@odata.id" in e]

        # Parallel fetch events
        def process_event(url: str, result: Any) -> Optional[str]:
            if result and result.status == 200:
                return result.dict.get("Severity", "Unknown")
            return None

        severities = self._parallel_fetcher.fetch(event_urls, process_event, "events")

        # Count by severity
        sev_count = {}
        for severity in severities:
            if severity:
                sev_count[severity] = sev_count.get(severity, 0) + 1

        for severity, val in sev_count.items():
            metrics.append(
                f"clustorstor_events_severity{prom_kv({'severity': severity})} {val}"
            )
