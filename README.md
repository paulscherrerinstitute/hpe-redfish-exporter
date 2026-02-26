# HPE Redfish Exporter for Prometheus

A Prometheus exporter for HPE ClusterStor systems that collects metrics via the HPE Redfish REST API.

## Overview

This exporter queries HPE Redfish API endpoints to gather comprehensive system metrics including:
- Storage system health and status
- Node power states and network interfaces
- Lustre filesystem statistics (IO operations, capacity, inodes)
- Linux system metrics (CPU, memory, load averages)
- Event history and severity counts

## Features

### Lustre Filesystem Metrics
- **Comprehensive monitoring**: IO operations, capacity usage, inode counts, exports
- **Target-specific metrics**: Both MDT and OST target statistics
- **Prometheus-compatible**: Properly labeled metrics with filesystem, target, and type information
- **Detailed documentation**: See [Lustre Metrics Documentation](docs/lustre-metrics.md)

### System Monitoring
- Node health and power states
- Network interface status
- CPU, memory, and load metrics
- Event tracking and severity analysis

## Quick Start

### Prerequisites
- Python 3.8+
- Access to HPE Redfish API endpoint
- Valid Redfish credentials

### Installation

#### Option 1: Install as Python package (recommended)

```bash
# Clone the repository
git clone https://github.com/paulscherrerinstitute/hpe-redfish-exporter.git
cd hpe-redfish-exporter

# Set up virtual environment
python -m venv .venv
source .venv/bin/activate

# Install package in development mode
pip install -e .
```

#### Option 2: Traditional installation

```bash
# Clone the repository
git clone https://github.com/paulscherrerinstitute/hpe-redfish-exporter.git
cd hpe-redfish-exporter

# Set up virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Configuration

Create `.hpe_redfish_auth` file with your credentials:

```json
{
  "username": "your-username",
  "password": "your-password"
}
```

### Running the Exporter

#### Using installed package:
```bash
source .venv/bin/activate
hpe-redfish-exporter
```

#### Using wrapper script (backward compatibility):
```bash
source .venv/bin/activate
python hpe-redfish-exporter-wrapper.py
```

#### With custom configuration:
```bash
hpe-redfish-exporter \
  --redfish-host "https://your-clustorstor:8081" \
  --listen-addr "0.0.0.0" \
  --listen-port 9223 \
  --auth-file "/path/to/auth.json" \
  --parallel-workers 20 \
  --cache-ttl 30 \
  --events-limit 100 \
  --debug-timing
```

The exporter will start on `http://127.0.0.1:9223/metrics`

## Metrics Collected

### Lustre Filesystem Metrics
See [Lustre Metrics Documentation](docs/lustre-metrics.md) for detailed information.

**Key metrics:**
- `clustorstor_lustre_read_ops` / `clustorstor_lustre_write_ops` - IO operations
- `clustorstor_lustre_free_space_bytes` / `clustorstor_lustre_used_space_bytes` - Capacity
- `clustorstor_lustre_free_inodes` / `clustorstor_lustre_used_inodes` - Inode usage
- `clustorstor_lustre_exports` - Export counts
- `clustorstor_lustre_free_space_percent` - Capacity percentage

### System Metrics
- `clustorstor_node_health` - Node health status
- `clustorstor_node_power_state` - Node power state
- `clustorstor_node_cpu_utilization` - CPU usage
- `clustorstor_node_memory_utilization` - Memory usage
- `clustorstor_node_load_average1m` / `load_average5m` / `load_average15m` - System load
- `clustorstor_events_total` - Total event count
- `clustorstor_events_severity` - Events by severity level
- `clustorstor_fetch_errors_total` - Total number of failed API fetches

## Example Queries

### Lustre Filesystem Capacity Usage
```prometheus
100 * (
  sum(clustorstor_lustre_used_space_bytes) by (filesystem)
  / 
  sum(clustorstor_lustre_total_space_bytes) by (filesystem)
)
```

### Lustre IO Operations Rate
```prometheus
sum by(target) (rate(clustorstor_lustre_read_ops[5m]))
sum by(target) (rate(clustorstor_lustre_write_ops[5m]))
```

### Node Health Status
```prometheus
clustorstor_node_health{health="OK"}
```

## Documentation

- **[Lustre Metrics](docs/lustre-metrics.md)** - Detailed Lustre filesystem metrics documentation
- **[Manual API Usage](docs/manual_api_usage.md)** - How to manually query the HPE Redfish API
- **[Setup Guide](docs/setup.md)** - Development environment setup
- **[HPE Redfish API Reference](docs/ClusterStor-Redfish-Swordfish-REST-API-7.2-030.pdf)** - Official API documentation

## Development

### Package Development

#### Python Wheel package

To work on the package development:

```bash
# Install in development mode
pip install -e .

# Run tests (if available)
python -m pytest

# Build package
python setup.py sdist bdist_wheel
```

#### RPM package

To generate a RPM package:

```bash
# ensure you have rpm tools installed and the `rpmbuild/` directory structure
# setup correctly.

# download the source
cd ${RPMBUILD_SOURCE_DIR}
curl -OL https://github.com/paulscherrerinstitute/hpe-redfish-exporter/archive/refs/tags/${VERSION}.tar.gz

# from the project root, build RPM
rpmbuild -bb hpe-redfish-exporter.spec
```

### Testing

The exporter includes debug capabilities. To test Lustre metrics specifically:

```bash
# Query a specific filesystem endpoint to see raw statistics
curl -k -H "X-Auth-Token: $HPE_RF_AUTH" \
  https://localhost:8081/redfish/v1/StorageServices/MXE300001B3VS0C5/FileSystems/psistor-OST0000 | jq '.Oem.Lustre.Statistics'
```

### Code Structure

```
hpe_redfish_exporter/
├── __init__.py          # Package initialization
├── cli.py               # CLI entry point
├── core.py              # Core exporter functionality
├── config.py            # Configuration management
├── metrics.py           # Metrics collection logic
├── redfish_client.py    # Redfish client wrapper
└── utils.py             # Utility functions
├── setup.py             # Package installation
├── hpe-redfish-exporter-wrapper.py  # Backward compatibility
├── docs/                # Documentation files
├── .venv/               # Python virtual environment
└── requirements.txt      # Python dependencies
```

## Performance Tuning

The exporter uses parallel API requests to maximize performance. Default settings work well for most environments, but can be tuned:

### Configuration Options

| Option | Default | Description |
|--------|---------|-------------|
| `--parallel-workers` | 20 | Number of parallel API requests |
| `--cache-ttl` | 30 | Cache TTL in seconds for top-level endpoints |
| `--events-limit` | none | Limit number of events to fetch (optional) |
| `--debug-timing` | off | Enable timing output for performance debugging |

### Tuning Tips

- **Increase `--parallel-workers`** if your Redfish API can handle more load
- **Decrease `--parallel-workers`** if you're seeing API errors or timeouts
- **Set `--events-limit`** if you don't need all historical events (reduces collection time)
- **Reduce `--cache-ttl`** if metrics need to be more fresh (at cost of more API calls)

### Timing Output

Enable timing output with the `--debug-timing` flag to see detailed performance information:

```bash
hpe-redfish-exporter --debug-timing
```

Example output:
```
[TIMING] Storage systems: 0.10s
[TIMING]   storage_nodes: 0.08s (16 items, 0 errors)
[TIMING] Lustre metrics: 0.20s
[TIMING]   filesystems: 0.18s (42 items, 0 errors)
[TIMING] Node status: 0.00s
[TIMING] Events: 0.50s
[TIMING]   events: 0.48s (747 items, 0 errors)
[TIMING] Total collection: 0.80s
```

## Troubleshooting

### No Metrics Appearing

1. **Check API connectivity**: Verify the Redfish endpoint is accessible
2. **Validate credentials**: Ensure username/password are correct
3. **Review logs**: Look for error messages during startup
4. **Test endpoints manually**: Use `curl` to verify API responses

### Lustre Metrics Missing

- Check that StorageServices endpoints are accessible
- Verify filesystem endpoints return Lustre statistics
- Review the [Lustre Metrics Documentation](docs/lustre-metrics.md) for troubleshooting tips

## Contributing

Contributions are welcome! Please follow these guidelines:

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/your-feature`
3. **Make your changes** and add tests if applicable
4. **Update documentation** for new features
5. **Submit a pull request**

## License

This project is licensed under the GNU General Public License v3.0 or later. See the [LICENSE](LICENSE) file for details.

## Support

For issues or questions:
- [Open an issue](https://github.com/your-repo/hpe-redfish-exporter/issues)
- Check the [documentation](docs/)
- Review the [HPE Redfish API documentation](docs/ClusterStor-Redfish-Swordfish-REST-API-7.2-030.pdf)

## Recent Changes

### Add RPM packaging v2.3.1 (2026-02-26)
- **Issue**: Distribute to systems that can't use `pip` or Python environments
- **Features**:
  - Created RPM spec which packages the HPE Redfish Exporter
  - Created RPM spec for dependency python-redfish library (see `contrib/` directory)
- **Documentation**: Added RPM build steps and information about the python-redfish RPM spec

### Dependency Reduction v2.3.0 (2026-02-26)
- **Issue**: Flask web framework added unnecessary complexity and dependencies
- **Fix**: Migrated from Flask to Python's built-in `http.server`
- **Result**: Eliminated 5 external dependencies (Flask, Werkzeug, Jinja2, click, itsdangerous)
- **Benefits**: Smaller footprint, reduced attack surface, simpler deployment
- **Documentation**: Updated with migration details and benefits

### Performance Optimization v2.1.0 (2026-02-25)
- **Issue**: Metrics collection took up to 20 seconds due to sequential API calls
- **Fix**: Implemented parallel API fetching with caching
- **Result**: Collection time reduced from ~17s to ~1s (17x speedup)
- **Features**:
  - Parallel fetching with configurable concurrency (default: 20 workers)
  - Caching for top-level API endpoints (default TTL: 30s)
  - Optional event limit to reduce collection time
  - New `clustorstor_fetch_errors_total` metric for monitoring API failures
- **Documentation**: Added Performance Tuning section in README

### Fixed Lustre Filesystem Statistics (2026-02-24)
- **Issue**: Lustre metrics collection was broken due to incorrect statistics parsing
- **Fix**: Properly handle HPE Redfish API's compound statistic keys (e.g., "OST0000 read")
- **Result**: All Lustre filesystem metrics now correctly collected and exposed
- **Documentation**: Added comprehensive [Lustre Metrics Documentation](docs/lustre-metrics.md)

See [CHANGELOG.md](CHANGELOG.md) for complete change history.
