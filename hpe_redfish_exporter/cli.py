"""
CLI entry point for HPE Redfish Exporter
"""

import argparse
import sys
from .config import Config
from .core import HPERedfishExporter


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="HPE Redfish Exporter - Prometheus exporter for HPE ClusterStor systems"
    )
    
    # Configuration arguments
    parser.add_argument(
        "--redfish-host",
        default="https://localhost:8081",
        help="Redfish API base URL (default: https://localhost:8081)"
    )
    parser.add_argument(
        "--listen-addr",
        default="127.0.0.1",
        help="Address to listen on (default: 127.0.0.1)"
    )
    parser.add_argument(
        "--listen-port",
        type=int,
        default=9223,
        help="Port to listen on (default: 9223)"
    )
    parser.add_argument(
        "--auth-file",
        default=".hpe_redfish_auth",
        help="Authentication file path (default: .hpe_redfish_auth)"
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="Show version and exit"
    )
    
    args = parser.parse_args()
    
    if args.version:
        from . import __version__
        print(f"HPE Redfish Exporter v{__version__}")
        sys.exit(0)
    
    # Create configuration
    config = Config(
        redfish_host=args.redfish_host,
        exporter_addr=args.listen_addr,
        exporter_port=args.listen_port,
        auth_file=args.auth_file
    )
    
    # Load credentials
    if not config.load_credentials():
        print("ERROR: Failed to load credentials")
        sys.exit(1)
    
    # Create and run exporter
    exporter = HPERedfishExporter(config)
    exporter.run()


if __name__ == "__main__":
    main()