"""
HTTP server implementation using Python's built-in http.server
"""

from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import sys
from typing import Optional

from .config import Config
from .metrics import MetricsCollector


class MetricsHandler(BaseHTTPRequestHandler):
    """HTTP request handler for metrics and health endpoints"""

    def __init__(self, *args, **kwargs):
        self.config = kwargs.pop("config", None)
        self.metrics_collector = kwargs.pop("metrics_collector", None)
        super().__init__(*args, **kwargs)

    def do_GET(self):
        """Handle GET requests"""
        try:
            if self.path == "/metrics":
                self._handle_metrics()
            elif self.path == "/health":
                self._handle_health()
            else:
                self.send_error(404, "Endpoint not found")
        except Exception as e:
            self.send_error(500, f"Internal Server Error: {str(e)}")

    def _handle_metrics(self):
        """Handle metrics endpoint"""
        try:
            # Collect metrics
            metrics_text = self.metrics_collector.collect()
            # Send response
            self.send_response(200)
            self.send_header("Content-type", "text/plain; version=0.0.4; charset=utf-8")
            self.end_headers()
            self.wfile.write(metrics_text.encode("utf-8"))
        except Exception as e:
            self.send_error(500, f"Failed to collect metrics: {str(e)}")

    def _handle_health(self):
        """Handle health endpoint"""
        try:
            # Send simple health response
            self.send_response(200)
            self.send_header("Content-type", "text/plain")
            self.end_headers()
            self.wfile.write(b"OK")
        except Exception as e:
            self.send_error(500, f"Health check failed: {str(e)}")


class HPERedfishExporterServer(HTTPServer):
    """Custom HTTP server for HPE Redfish Exporter"""

    def __init__(self, server_address, config: Config):
        self.config = config
        self.metrics_collector = MetricsCollector(config)

        # Create server with custom handler
        super().__init__(
            server_address,
            lambda *args, **kwargs: MetricsHandler(
                *args, config=config, metrics_collector=self.metrics_collector, **kwargs
            ),
        )

    def serve_forever(self, poll_interval=0.5):
        """Start serving requests"""
        ip = str(self.server_address[0])
        port = int(self.server_address[1])
        print(
            f"Starting ClusterStor Redfish Exporter on {ip}:{port}"
        )
        super().serve_forever(poll_interval)

    def shutdown(self):
        """Shutdown the server"""
        print("Shutting down ClusterStor Redfish Exporter")
        super().shutdown()
