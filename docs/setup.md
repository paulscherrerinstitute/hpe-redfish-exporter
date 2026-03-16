# Setup for Development environment

This is a Python-based project, which needs specific modules. A
`requirements.txt` file is provided in the root of the project listing out all
needed modules.

A Python `venv` can be created and used, to ensure we have a clean development environment.

## Creating the Venv

NOTE: You only need to create the Venv if the `.venv` directory does not exist!

### Option 1: Traditional Installation (for running the script)

```console
$ python -m venv redfish && mv redfish .venv && ls -a
.  ..  docs  .git  .gitignore  .hpe_redfish_auth  hpe-redfish-exporter.py  requirements.txt  .venv

$ source .venv/bin/activate

$ pip install -r requirements.txt
```

### Option 2: Package Installation (recommended for development)

```console
$ python -m venv .venv
$ source .venv/bin/activate
$ pip install -e .
```

This will install the package in development mode, allowing you to make changes
and test them immediately.

## Running the Exporter

### Using the installed package:
```console
$ source .venv/bin/activate
$ hpe-redfish-exporter
```

### Using the wrapper script (backward compatibility):
```console
$ source .venv/bin/activate
$ python hpe-redfish-exporter-wrapper.py
```

### With custom configuration:
```console
$ hpe-redfish-exporter \
  --redfish-host "https://your-clusterstor:8081" \
  --listen-addr "0.0.0.0" \
  --listen-port 9223 \
  --auth-file "/path/to/auth.json" \
  --parallel-workers 20 \
  --cache-ttl 30 \
  --events-limit 100 \
  --debug-timing
```

### Performance Options

The exporter supports performance tuning via CLI arguments:

- `--parallel-workers`: Number of parallel API requests (default: 20)
- `--cache-ttl`: Cache TTL in seconds for top-level endpoints (default: 30)
- `--events-limit`: Limit number of events to fetch (optional, default: all)
- `--debug-timing`: Enable timing output for debugging (default: off)

See [README.md](../README.md) for detailed performance tuning information.

## Package Development

To work on the package itself:

```console
# Install in development mode
$ pip install -e .

# Build the package
$ python setup.py sdist bdist_wheel

# Run tests (if available)
$ python -m pytest
```

## Project Structure

The project now follows a proper Python package structure:

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
