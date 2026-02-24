# AI Agent Instructions for HPE Redfish Exporter

## Project Overview

**Purpose**: Prometheus exporter for HPE ClusterStor systems using Redfish API
**Main File**: `hpe-redfish-exporter.py`
**Language**: Python 3.8+

## Key Responsibilities

### Code Maintenance
- **Primary Focus**: `hpe-redfish-exporter.py` - Main exporter logic
- **Secondary Files**: Documentation in `docs/` directory
- **Configuration**: Environment variables and `.hpe_redfish_auth` file

### Common Tasks

#### 1. Bug Fixes
- **Lustre Metrics**: Lines 120-200 (StorageServices/FileSystems parsing)
- **System Metrics**: Lines 50-120 (StorageSystems collection)
- **Error Handling**: `safe_get()` function and try/catch blocks

#### 2. Feature Enhancements
- **New Metrics**: Add to appropriate section in `collect_metrics()`
- **API Endpoints**: Follow existing pattern with `safe_get()`
- **Prometheus Format**: Use `prom_kv()` helper for labels

#### 3. Documentation
- **User Docs**: Update `README.md` and `docs/lustre-metrics.md`
- **Technical Docs**: Add implementation details to relevant files
- **Changelog**: Add entries to `CHANGELOG.md`

## Important Patterns

### API Query Pattern
```python
response = safe_get(client, "/redfish/v1/Endpoint")
if response and response.status == 200:
    # Process response.dict
```

### Metric Generation
```python
metrics.append(f'metric_name{prom_kv(labels)} {value}')
```

### Error Handling
```python
def safe_get(client, path):
    try:
        return client.get(path)
    except Exception:
        return None
```

## Key Sections

### Configuration (Lines 12-25)
- `REDFISH_HOST`, `USERNAME`, `PASSWORD`
- `EXPORTER_LISTEN_ADDR`, `EXPORTER_LISTEN_PORT`

### Core Functions
- `get_client()`: Redfish client setup
- `safe_get()`: Safe API querying
- `prom_kv()`: Prometheus label formatting
- `collect_metrics()`: Main metrics collection

### Metric Collection Sections
1. **Storage Systems** (Lines 50-120): Node health, power, network
2. **Lustre Filesystem** (Lines 120-200): IO ops, capacity, inodes
3. **Telemetry Service** (Lines 200-220): Metric reports (currently passive)
4. **Node Status** (Lines 220-260): CPU, memory, load averages
5. **Event Service** (Lines 260-280): Event history

## Common Issues

### Lustre Metrics Problems
- **Check**: Statistics format from `/redfish/v1/StorageServices/*/FileSystems/*`
- **Pattern**: Keys like `"OST0000 free_space"` (not simple `"free_space"`)
- **Fix Location**: Lines 157-200 in `collect_metrics()`

### API Connectivity
- **Verify**: Redfish endpoint accessibility
- **Check**: Authentication credentials in `.hpe_redfish_auth`
- **Test**: Manual `curl` commands to API endpoints

## Testing Approach

### Manual Testing
```bash
# Test specific endpoint
curl -k -H "X-Auth-Token: $HPE_RF_AUTH" \
  https://localhost:8081/redfish/v1/StorageServices/ID/FileSystems/NAME
```

### Validation
- **Metrics Endpoint**: `http://localhost:9223/metrics`
- **Expected**: Valid Prometheus format with proper labels
- **Verify**: All expected metrics present

## Documentation Standards

### File Locations
- **User Guides**: `README.md`, `docs/*.md`
- **Technical Docs**: In-code comments for complex logic
- **API Reference**: `docs/ClusterStor-Redfish-Swordfish-REST-API-7.2-030.pdf`

### Update Rules
1. **New Features**: Add to README + create dedicated doc if complex
2. **Bug Fixes**: Update CHANGELOG + relevant documentation
3. **API Changes**: Document in both code comments and user docs

## Quick Reference

### Common Commands
```bash
# Run exporter
source .venv/bin/activate && python hpe-redfish-exporter.py

# Test API
curl -k -H "X-Auth-Token: $HPE_RF_AUTH" https://localhost:8081/redfish/v1/StorageSystems

# Check metrics
curl http://localhost:9223/metrics
```

### Key Metrics
- **Lustre**: `clustorstor_lustre_*` (read_ops, write_ops, space_bytes, inodes)
- **System**: `clustorstor_node_*` (health, power_state, cpu_utilization)
- **Events**: `clustorstor_events_*` (total, severity)

## Decision Making

### When to Ask
- **Architecture changes** affecting multiple components
- **API interpretation** questions (check official PDF first)
- **Breaking changes** to existing metrics

### Autonomous Actions
- **Bug fixes** in existing patterns
- **Documentation updates** for clarity
- **Error handling** improvements
- **Code cleanup** (formatting, comments)

**Remember**: This project follows HPE Redfish API specifications - always verify against the official documentation when in doubt.