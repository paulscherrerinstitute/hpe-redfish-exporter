"""
Core exporter functionality for HPE Redfish Exporter
"""

from .http_server import HPERedfishExporterServer
from .config import Config
from .metrics import MetricsCollector


class HPERedfishExporter:
    """Main exporter class that provides Prometheus metrics endpoint"""

    def __init__(self, config: Config):
        self.config = config
        self.metrics_collector = MetricsCollector(config)
        self.server = None

    def run(self):
        """Run the exporter server"""
        # Create server address
        server_address = (self.config.exporter_addr, self.config.exporter_port)

        # Create and start server
        self.server = HPERedfishExporterServer(server_address, self.config)

        try:
            self.server.serve_forever()
        except KeyboardInterrupt:
            self.server.shutdown()

    def get_app(self):
        """Get server instance for external use (e.g., with gunicorn)"""
        return self.server
