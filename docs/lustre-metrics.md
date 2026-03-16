# Lustre Filesystem Metrics Collection

This document describes how the HPE Redfish Exporter collects and exposes Lustre filesystem metrics from HPE ClusterStor systems.

## Overview

The exporter queries HPE Redfish API endpoints to gather comprehensive Lustre filesystem statistics including:
- I/O operations (read/write operations)
- Storage capacity (free/total/used space)
- Inode usage (free/total/used inodes)
- Export counts and filesystem status
- Target-specific metrics for both MDT and OST targets

**Note**: This documentation applies to version 2.0.0+ of the HPE Redfish Exporter, which has been restructured as an installable Python package.

## API Endpoints Used

The exporter collects Lustre metrics from the following HPE Redfish API endpoints:

```
/redfish/v1/StorageServices/{StorageServiceId}/FileSystems/{FilesystemId}
```

Example:
```
/redfish/v1/StorageServices/MXE300001B3VS0C5/FileSystems/psistor-OST0000
```

## Statistics Format

The HPE Redfish API returns Lustre statistics in a specific format where keys are compound strings:

```json
{
  "Statistics": {
    "OST0000 free_inodes": "20460794",
    "OST0000 total_inodes": "40072320", 
    "OST0000 used_inodes": "19611526",
    "OST0000 available_space": "34019832709120",
    "OST0000 free_space": "34440171204608",
    "OST0000 total_space": "41666114793472",
    "OST0000 used_space": "7225943588864",
    "OST0000 num_exports": "101",
    "OST0000 percent_free_space": "82",
    "OST0000 read": "0",
    "OST0000 write": "86549022"
  }
}
```

## Prometheus Metrics Generated

The exporter generates two types of Prometheus metrics for each statistic:

### 1. Generic Metrics

All statistics are exposed as generic metrics with a `metric` label:

```prometheus
hpe_redfish_clustorstor_lustre_metric{
  filesystem="psistor",
  target="psistor-OST0000", 
  type="OST",
  metric="free_inodes"
} 20460794.0
```

### 2. Specific Metrics

Common operations get dedicated metric names for easier querying:

#### I/O Operations
```prometheus
hpe_redfish_clustorstor_lustre_read_ops{
  filesystem="psistor",
  target="psistor-OST0000",
  type="OST"
} 0.0

hpe_redfish_clustorstor_lustre_write_ops{
  filesystem="psistor",
  target="psistor-OST0000", 
  type="OST"
} 86549022.0
```

#### Storage Capacity (bytes)
```prometheus
hpe_redfish_clustorstor_lustre_free_space_bytes{
  filesystem="psistor",
  target="psistor-OST0000",
  type="OST"
} 34440171204608.0

hpe_redfish_clustorstor_lustre_total_space_bytes{
  filesystem="psistor",
  target="psistor-OST0000",
  type="OST"
} 41666114793472.0

hpe_redfish_clustorstor_lustre_used_space_bytes{
  filesystem="psistor",
  target="psistor-OST0000",
  type="OST"
} 7225943588864.0

hpe_redfish_clustorstor_lustre_available_space_bytes{
  filesystem="psistor",
  target="psistor-OST0000",
  type="OST"
} 34019832709120.0
```

#### Inode Usage
```prometheus
hpe_redfish_clustorstor_lustre_free_inodes{
  filesystem="psistor",
  target="psistor-OST0000",
  type="OST"
} 20460794.0

hpe_redfish_clustorstor_lustre_total_inodes{
  filesystem="psistor",
  target="psistor-OST0000",
  type="OST"
} 40072320.0

hpe_redfish_clustorstor_lustre_used_inodes{
  filesystem="psistor",
  target="psistor-OST0000",
  type="OST"
} 19611526.0
```

#### Additional Metrics
```prometheus
hpe_redfish_clustorstor_lustre_exports{
  filesystem="psistor",
  target="psistor-OST0000",
  type="OST"
} 101.0

hpe_redfish_clustorstor_lustre_free_space_percent{
  filesystem="psistor",
  target="psistor-OST0000",
  type="OST"
} 82.0
```

## Metric Labels

All Lustre metrics include the following labels:

- `filesystem`: Lustre filesystem name (e.g., "psistor")
- `target`: Target identifier (e.g., "psistor-OST0000", "psistor-MDT0000")
- `type`: Target type ("OST" for Object Storage Target, "MDT" for Metadata Target)

## Query Examples

### Monitor read/write operations per OST
```prometheus
sum by(target) (rate(hpe_redfish_clustorstor_lustre_read_ops[5m]))
sum by(target) (rate(hpe_redfish_clustorstor_lustre_write_ops[5m]))
```

### Check filesystem capacity usage
```prometheus
100 * (
  sum(hpe_redfish_clustorstor_lustre_used_space_bytes) by (filesystem)
  / 
  sum(hpe_redfish_clustorstor_lustre_total_space_bytes) by (filesystem)
)
```

### Monitor inode usage
```prometheus
100 * (
  sum(hpe_redfish_clustorstor_lustre_used_inodes) by (filesystem)
  / 
  sum(hpe_redfish_clustorstor_lustre_total_inodes) by (filesystem)
)
```

### Alert on high capacity usage
```prometheus
100 * (
  sum(hpe_redfish_clustorstor_lustre_used_space_bytes) by (filesystem)
  / 
  sum(hpe_redfish_clustorstor_lustre_total_space_bytes) by (filesystem)
) > 90
```

## Troubleshooting

### No Lustre metrics appearing

1. **Check Redfish API connectivity**: Verify the exporter can connect to the Redfish endpoint
2. **Verify StorageServices endpoint**: Ensure `/redfish/v1/StorageServices` is accessible
3. **Check filesystem endpoints**: Verify individual filesystem endpoints return data
4. **Review exporter logs**: Look for error messages during metric collection

### Missing specific metrics

- Some metrics may not be available for all target types
- MDT targets may have different metrics than OST targets
- Check the raw API response to see what statistics are available

### Debugging

To see the raw statistics structure, you can query the API directly:

```bash
curl -k -H "X-Auth-Token: $HPE_RF_AUTH" \
  https://localhost:8081/redfish/v1/StorageServices/MXE300001B3VS0C5/FileSystems/psistor-OST0000 | jq '.Oem.Lustre.Statistics'
```

## Implementation Details

The exporter:
1. Queries all StorageServices to find Lustre filesystems
2. Iterates through each filesystem endpoint
3. Extracts statistics from the `Oem.Lustre.Statistics` section
4. Parses compound metric names (e.g., "OST0000 free_space" → "free_space")
5. Converts string values to numeric
6. Generates both generic and specific Prometheus metrics
7. Handles errors gracefully for malformed data

## Related Documentation

- [Manual API Usage](manual_api_usage.md) - How to manually query the HPE Redfish API
- [Setup Guide](setup.md) - How to set up the development environment
- [HPE Redfish API Documentation](ClusterStor-Redfish-Swordfish-REST-API-7.2-030.pdf) - Official API reference
