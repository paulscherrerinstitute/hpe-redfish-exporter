# Changelog

All notable changes to the HPE Redfish Exporter project will be documented in this file.

## [Unreleased]

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
  config = Config(redfish_host="https://host:8081")
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
