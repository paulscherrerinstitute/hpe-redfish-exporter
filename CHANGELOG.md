# Changelog

All notable changes to the HPE Redfish Exporter project will be documented in this file.

## [Unreleased]

## [1.1.0] - 2024-02-24

### Fixed
- **Lustre Filesystem Statistics Collection**: Fixed broken Lustre metrics collection that was caused by:
  - Incorrect parsing of HPE Redfish API's compound statistic keys (e.g., "OST0000 read" instead of simple "read")
  - Bug on line 155 that was appending entire statistics dictionary as string instead of individual metrics
  - Wrong assumption about statistics data structure

### Added
- **Comprehensive Lustre Metrics Documentation**: Created detailed documentation in `docs/lustre-metrics.md` covering:
  - API endpoints and statistics format
  - All Prometheus metrics generated
  - Query examples and troubleshooting
  - Implementation details

- **Project README**: Added comprehensive `README.md` with:
  - Project overview and features
  - Quick start guide
  - Configuration instructions
  - Metrics documentation
  - Example queries
  - Development and troubleshooting information

### Changed
- **Lustre Statistics Parsing**: Completely rewrote the statistics parsing logic to:
  - Properly handle compound metric names (e.g., "OST0000 free_space" → "free_space")
  - Generate both generic and specific Prometheus metrics
  - Include robust error handling for malformed data
  - Convert string values to proper numeric types

- **Metric Generation**: Enhanced to produce:
  - Generic metrics: `clustorstor_lustre_metric{metric="..."}` for all statistics
  - Specific metrics: Dedicated metrics for common operations (IO ops, space, inodes, etc.)
  - Proper Prometheus labels: `filesystem`, `target`, `type`, and `metric`

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

## [1.0.0] - 2024-02-23

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