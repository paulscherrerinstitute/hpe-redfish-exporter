"""
Core exporter functionality for HPE Redfish Exporter
"""

from flask import Flask, Response
from .config import Config
from .metrics import MetricsCollector


class HPERedfishExporter:
    """Main exporter class that provides Prometheus metrics endpoint"""
    
    def __init__(self, config: Config):
        self.config = config
        self.metrics_collector = MetricsCollector(config)
        self.app = Flask(__name__)
        
        # Set up routes
        self._setup_routes()
        
    def _setup_routes(self):
        """Set up Flask routes"""
        @self.app.route("/metrics")
        def metrics():
            text = self.metrics_collector.collect()
            return Response(text, mimetype="text/plain")
            
        @self.app.route("/health")
        def health():
            return Response("OK", mimetype="text/plain")
    
    def run(self):
        """Run the exporter server"""
        print(f"Starting ClusterStor Redfish Exporter on {self.config.exporter_addr}:{self.config.exporter_port}")
        self.app.run(host=self.config.exporter_addr, port=self.config.exporter_port)
    
    def get_app(self) -> Flask:
        """Get Flask app for external use (e.g., with gunicorn)"""
        return self.app