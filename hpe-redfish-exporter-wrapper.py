#!/usr/bin/env python3
"""
Backward compatibility wrapper for the old hpe-redfish-exporter.py script
"""

import sys
import os

# Add current directory to path to import the package
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from hpe_redfish_exporter.cli import main

if __name__ == "__main__":
    main()