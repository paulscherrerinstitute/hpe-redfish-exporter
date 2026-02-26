# Changelog

All notable changes to the HPE Redfish Exporter project will be documented in this file.

## [2.3.1] - 2026-02-26

### 🚀 RPM Package Support: Added RPM spec files for distribution

### Added
- **RPM Package Support**: Added RPM spec files for building RPM packages:
  - `hpe-redfish-exporter.spec`: Main RPM spec file for HPE Redfish Exporter
  - `contrib/python-redfish.spec`: RPM spec file for python-redfish module
  
- **RPM Build Instructions**: Added documentation for building RPM packages:
  - `python3 setup.py bdist_rpm` - Build RPM from source
  - Manual RPM build process documentation
  
- **Package Dependencies**: Updated requirements for RPM building:
  - `python3-devel` - Python development files
  - `python3-setuptools` - Python setuptools for RPM building
  
### Changed
- **Package Version**: Updated to 2.3.1 to reflect RPM package support
- **Documentation**: Added RPM build instructions to project documentation

### Fixed
- **Build Process**: Improved RPM build process with proper source tarball handling
- **Package Structure**: Updated package structure for RPM compatibility

### Technical Details

**Files Added:**
- `hpe-redfish-exporter.spec` - Main RPM spec file
- `contrib/python-redfish.spec` - Python-redfish RPM spec file

**RPM Build Commands:**
```bash
# Install build dependencies
python3 -m pip install --user setuptools wheel

# Build RPM package
python3 setup.py bdist_rpm

# Or manually using rpmbuild
rpmbuild -bb hpe-redfish-exporter.spec
```

**RPM Package Contents:**
- Main executable: `/usr/bin/hpe-redfish-exporter`
- Python modules: `/usr/lib/python3.X/site-packages/hpe_redfish_exporter/`
- Documentation: `/usr/share/doc/hpe-redfish-exporter/`
- License: `/usr/share/licenses/hpe-redfish-exporter/LICENSE`

### Migration Guide

**For existing users:**
- No configuration changes required
- Optional: Install from RPM packages for easier distribution
- Benefits: System package management, dependency resolution, easier updates

**For new users:**
- Install from source: `pip install -e .`
- Install from RPM: `rpm -ivh hpe-redfish-exporter-2.3.1-1.noarch.rpm`
- Both methods provide identical functionality

## [2.3.0] - 2026-02-26

### 🚀 Dependency Reduction: Migrated from Flask to Python http.server

### Added
- **HTTP Server Migration**: Complete migration from Flask to Python's built-in `http.server`
  - `http_server.py`: New HTTP server implementation with `MetricsHandler` and `HPERedfishExporterServer`
  - Maintains identical API endpoints and functionality
  - Eliminates Flask, Werkzeug, Jinja2, click, and itsdangerous dependencies

- **Dependency Reduction**: Removed 5 external dependencies:
  - Flask (3.1.3)
  - Werkzeug (3.1.6)
  - Jinja2 (3.1.6)
  - click (8.3.1)
  - itsdangerous (2.2.0)

- **Package Size Reduction**: Smaller footprint and reduced attack surface
- **Deployment Simplicity**: No pip installation of web framework required
- **Performance**: Minimal overhead for simple HTTP serving

### Changed
- **Package Version**: Updated to 2.3.0 to reflect dependency reduction
- **Core Architecture**: Replaced Flask-based server with `http.server` implementation
- **Dependencies**: `requirements.txt` and `setup.py` updated to remove Flask dependencies
- **Server Implementation**: `core.py` refactored to use new HTTP server

### Fixed
- **Dependency Bloat**: Eliminated unnecessary web framework dependencies
- **Deployment Complexity**: Simplified installation and deployment process

### Technical Details

**Files Modified:**
- `hpe_redfish_exporter/http_server.py`: New HTTP server implementation
- `hpe_redfish_exporter/core.py`: Replaced Flask with http.server
- `requirements.txt`: Removed Flask-related dependencies
- `setup.py`: Updated install_requires to reflect new dependencies
- `CHANGELOG.md`: Added migration details

**Dependencies Removed:**
- Flask==3.1.3
- Werkzeug==3.1.6
- Jinja2==3.1.6
- click==8.3.1
- itsdangerous==2.2.0

**Dependencies Kept:**
- redfish==3.3.4
- requests==2.32.5
- requests-toolbelt==1.0.0
- requests-unixsocket==0.4.1
- All other essential dependencies

### Migration Guide

**For existing users:**
- No configuration changes required
- No API changes (same endpoints and responses)
- Simply reinstall the package: `pip install -e .`
- Benefits: Smaller package, fewer dependencies, simpler deployment

**Benefits:**
- **No external web framework dependencies**
- **Reduced package size** (removes ~2MB of Flask dependencies)
- **Simplified deployment** (no pip installation of Flask needed)
- **Lower resource usage** (minimal overhead for simple HTTP serving)
- **Same functionality** (identical API endpoints and responses)
- **Maintainable codebase** (uses built-in Python modules)

## [2.2.0] - 2026-02-25

### 🔧 Events Collection: Enhanced Error Handling and Validation

### Added
- **Enhanced Error Handling**: Improved validation in events collection with explicit checks:
  - Validates event data structure before processing
  - Checks for proper message count consistency
  - Handles cases where API response doesn't match expected format
  - Graceful fallback for malformed or unexpected data

- **Better Error Reporting**: More informative error handling in event processing:
  - Validates that `Events` field exists and is a list
  - Checks that message count matches actual array length
  - Returns `None` for invalid events instead of crashing
  - Maintains existing functionality while adding robustness

- **GPL-3.0 License**: Added GNU General Public License v3.0 or later
  - License file: `LICENSE`
  - License notice added to `README.md`

### Changed
- **Package Version**: Updated to 2.2.0 to reflect enhanced error handling
- **Event Processing**: More defensive programming in `_collect_events` method
- **API Validation**: Added structure validation for Redfish API responses

### Fixed
- **API Inconsistency Handling**: Better handling of unexpected API response formats
- **Error Resilience**: Prevents crashes from malformed event data
- **Data Validation**: Ensures proper message count before processing

### Technical Details

**Files Modified:**
- `hpe_redfish_exporter/metrics.py`: Enhanced `_collect_events` method with validation
- `README.md`: Added license information

**Key Changes:**
- Added explicit type and structure validation
- Improved error handling for API inconsistencies
- Better handling of unexpected response formats
- Maintained existing functionality while adding robustness

### Migration Guide

**For existing users:**
- No configuration changes required
- Improved reliability when API responses vary
- Better error handling without breaking changes
- Enhanced logging for debugging issues

**Benefits:**
- More resilient to API inconsistencies
- Better error reporting and handling
- Prevents crashes from malformed data
- Maintains existing functionality

## [2.1.0] - 2026-02-25

### 🚀 Performance Optimization: Parallel API Fetching with Caching

### Added
- **Parallel API Fetching**: All metric collection now uses parallel requests with configurable concurrency:
  - `ResponseCache` class: Caches top-level API responses (StorageSystems, StorageServices, Events)
  - `ParallelFetcher` class: Handles parallel API requests with semaphore rate limiting
  - Default 20 parallel workers (configurable)
  - Progress logging for large fetches

- **New Configuration Options**:
  - `--parallel-workers`: Number of parallel API requests (default: 20)
  - `--cache-ttl`: Cache TTL in seconds for top-level endpoints (default: 30)
  - `--events-limit`: Limit number of events to fetch (default: all)
  - `--debug-timing`: Enable timing output for performance debugging (default: off)

- **New Metrics**:
  - `clustorstor_fetch_errors_total`: Total number of failed API fetches

### Changed
- **Package Version**: Updated to 2.1.0
- **Storage Systems Collection**: Now parallelized with 16+ concurrent requests
- **Lustre Metrics Collection**: Now parallelized with 20+ concurrent requests
- **Events Collection**: Now parallelized with up to 20 concurrent requests
- **Node Status Collection**: Reuses cached data from storage systems (eliminates redundant API calls)
- **Error Handling**: Failed fetches are logged and skipped gracefully
- **Timing Output**: Added detailed timing information for debugging performance

### Performance Improvement
| Function | Before | After |
|----------|--------|-------|
| Storage systems | ~0.3s | ~0.1s |
| Lustre metrics | ~1-2s | ~0.2s |
| Node status | ~0.3s | ~0s (reused) |
| Events | ~15s | ~0.5s |
| **Total** | **~17s** | **~1s** |

### Technical Details

**Files Modified:**
- `hpe_redfish_exporter/config.py`: Added parallel_workers, cache_ttl, events_limit, debug_timing options
- `hpe_redfish_exporter/cli.py`: Added --parallel-workers, --cache-ttl, --events-limit, --debug-timing arguments
- `hpe_redfish_exporter/metrics.py`: Complete refactor with caching and parallel fetching

**New Classes:**
- `ResponseCache`: Thread-safe cache for API responses
- `ParallelFetcher`: Parallel fetching with rate limiting and error handling

### Migration Guide

**For existing users:**
- No configuration changes required (defaults work well)
- Optional: Tune `--parallel-workers` for your environment
- Optional: Set `--events-limit` if you don't need all historical events
- Optional: Use `--debug-timing` to debug performance issues

## [2.0.0] - 2026-02-24

### 🚀 Major Architecture Change: Converted to Installable Python Package

### Added
- **Installable Python Package**: Complete restructuring as a proper Python package with:
  - `setup.py` with all dependencies and entry points
  - Proper module structure (`hpe_redfish_exporter/`)
  - Package metadata and version management
  - Wheel and source distribution support

- **Modular Code Structure**: Split functionality into logical modules:
  - `cli.py`: CLI entry point with argument parsing
  - `core.py`: Core exporter functionality (Flask app)
  - `config.py`: Configuration management
  - `metrics.py`: Metrics collection logic
  - `redfish_client.py`: Redfish client wrapper
  - `utils.py`: Utility functions

- **CLI Enhancements**: New command-line interface with:
  - `--redfish-host`: Configure Redfish API endpoint
  - `--listen-addr`: Configure listen address
  - `--listen-port`: Configure listen port
  - `--auth-file`: Configure authentication file path
  - `--version`: Show version information
  - `--help`: Comprehensive help text

- **Programmatic API**: Can now be imported and used as a library:
  ```python
  from hpe_redfish_exporter import HPERedfishExporter, Config
  
  # Create configuration
  config = Config(
      redfish_host="https://localhost:8081",
      exporter_addr="127.0.0.1", 
      exporter_port=9223,
      auth_file=".hpe_redfish_auth"
  )
  
  # Load credentials
  if config.load_credentials():
      # Create and run exporter
      exporter = HPERedfishExporter(config)
      exporter.run()
  ```

- **Health Endpoint**: Added `/health` endpoint for monitoring
- **Backward Compatibility**: Wrapper script for existing users

### Changed
- **Package Version**: Updated to 2.0.0 to reflect major architecture changes
- **Configuration System**: Enhanced configuration management with validation
- **Error Handling**: Improved error handling throughout all modules
- **Code Organization**: Professional module structure following Python best practices
- **Type Annotations**: Added comprehensive type hints throughout the codebase

### Fixed
- **Version Consistency**: Fixed version mismatch between module and changelog
- **Installation Process**: Proper package installation with `pip install -e .`

### Technical Details

**Files Added:**
- `hpe_redfish_exporter/__init__.py` - Package initialization
- `hpe_redfish_exporter/cli.py` - CLI entry point
- `hpe_redfish_exporter/core.py` - Core exporter functionality
- `hpe_redfish_exporter/config.py` - Configuration management
- `hpe_redfish_exporter/metrics.py` - Metrics collection logic
- `hpe_redfish_exporter/redfish_client.py` - Redfish client wrapper
- `hpe_redfish_exporter/utils.py` - Utility functions
- `setup.py` - Package installation configuration
- `MANIFEST.in` - Package data inclusion
- `hpe-redfish-exporter-wrapper.py` - Backward compatibility wrapper

**Files Modified:**
- `README.md` - Updated with new installation and usage instructions
- `CHANGELOG.md` - Updated with version 2.0.0 changes
- `requirements.txt` - Maintained dependencies

### Migration Guide

**For existing users:**
1. Install the new package: `pip install -e .`
2. Use the new CLI: `hpe-redfish-exporter`
3. Or use the wrapper: `python hpe-redfish-exporter-wrapper.py`

**For new users:**
1. Install: `pip install -e .`
2. Configure: Create `.hpe_redfish_auth` file
3. Run: `hpe-redfish-exporter`

### Breaking Changes

- **CLI Command**: Changed from `python hpe-redfish-exporter.py` to `hpe-redfish-exporter`
- **Configuration**: Now uses command-line arguments instead of editing source file
- **Import Paths**: If importing (unlikely for most users), paths have changed

### Benefits

- **Professional Installation**: Standard Python package installation
- **Better Maintainability**: Clear module separation
- **Programmatic Use**: Can be used as a library
- **Standard Practices**: Follows Python packaging best practices
- **Future-Proof**: Easy to add new features and maintain

### Technical Details

**Files Modified:**
- `hpe-redfish-exporter.py`: Fixed Lustre metrics collection (lines 155-200)

**Files Added:**
- `docs/lustre-metrics.md`: Comprehensive Lustre metrics documentation
- `README.md`: Project overview and setup guide

**Metrics Now Available:**
- `clustorstor_lustre_read_ops` / `clustorstor_lustre_write_ops`
- `clustorstor_lustre_free_space_bytes` / `clustorstor_lustre_used_space_bytes`
- `clustorstor_lustre_total_space_bytes` / `clustorstor_lustre_available_space_bytes`
- `clustorstor_lustre_free_inodes` / `clustorstor_lustre_used_inodes` / `clustorstor_lustre_total_inodes`
- `clustorstor_lustre_exports`
- `clustorstor_lustre_free_space_percent`
- `clustorstor_lustre_metric{metric="..."}` (generic metric for all statistics)

## [1.0.0] - 2026-02-23

### Added
- Initial release of HPE Redfish Exporter
- Basic storage system monitoring
- Node health and power state metrics
- Network interface status
- Event history collection
- Initial Lustre filesystem metrics (broken - fixed in 1.1.0)

## Format

This changelog follows the [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) format.

### Categories
- **Added**: New features
- **Changed**: Changes in existing functionality
- **Deprecated**: Soon-to-be removed features
- **Removed**: Removed features
- **Fixed**: Bug fixes
- **Security**: Vulnerability fixes
