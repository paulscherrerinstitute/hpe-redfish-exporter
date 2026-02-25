# Events API Documentation

This document describes the HPE Redfish Events API and the lessons learned from implementing event collection in the HPE Redfish Exporter.

## Overview

The HPE Redfish Events API provides access to system event history, including alerts, telemetry triggers, and system status changes. Events are crucial for monitoring system health and detecting issues before they impact operations.

## API Structure

### Main Events Endpoint

The primary endpoint is `/redfish/v1/Events` which returns a collection of event references:

```json
{
  "@odata.context": "/redfish/v1/$metadata#EventCollection.EventCollection",
  "@odata.id": "/redfish/v1/Events",
  "@odata.type": "#EventCollection.EventCollection",
  "Members": [
    {
      "@odata.id": "/redfish/v1/Events/fbc75aa8-e79e-4639-b175-61c0e302f90b"
    }
  ],
  "Members@odata.count": 1,
  "Name": "Events"
}
```

### Individual Event Objects

Each member URL returns a complete event object:

```json
{
  "@odata.context": "/redfish/v1/$metadata#Event.Event",
  "@odata.type": "#Event.v1_5_0.Event",
  "Context": "hw-ec",
  "Events": [
    {
      "Actions": {},
      "EventId": "fbc75aa8-e79e-4639-b175-61c0e302f90b",
      "EventTimestamp": "2026-02-25T13:09:48+01:00",
      "EventType": "Alert",
      "MemberId": "0",
      "Message": "ComputerSystem psistorn:Node-R1C1-33U-A has SwapUsage less than 80.00% for 300s",
      "MessageArgs": [
        "FreeSwapSpacePercent"
      ],
      "MessageId": "TelemetryService.Triggers.SwapUsage",
      "OriginOfCondition": {
        "@odata.id": "/redfish/v1/StorageSystems/psistorn:Node-R1C1-33U-A"
      },
      "Severity": "Warning"
    }
  ],
  "Events@odata.count": 1,
  "Id": "fbc75aa8-e79e-4639-b175-61c0e302f90b",
  "Name": "hw-ec Event"
}
```

## Key Fields

### Event Object Fields
- **@odata.context**: Metadata context path
- **@odata.type**: Event type specification
- **Context**: Event source context
- **Events**: Array of message objects (usually contains exactly 1 message)
- **Events@odata.count**: Number of messages in the Events array
- **Id**: Unique event identifier
- **Name**: Event name

### Message Object Fields
- **Actions**: Available actions for the event
- **EventId**: Unique message identifier
- **EventTimestamp**: ISO 8601 timestamp of when the event occurred
- **EventType**: Type of event (Alert, StatusChange, etc.)
- **MemberId**: Member identifier within the event
- **Message**: Human-readable event description
- **MessageArgs**: Array of message arguments for dynamic content
- **MessageId**: Message identifier for localization
- **OriginOfCondition**: Reference to the component that triggered the event
- **Severity**: Event severity level (OK, Warning, Critical, etc.)

## Important Patterns

### 1. Nested Message Structure

Events are wrapped in a parent object that contains an array of messages. Even though the API documentation indicates there should only be one message, the structure always uses an array:

```json
"Events": [
  {
    "Severity": "Warning",
    "Message": "...",
    "EventTimestamp": "..."
  }
]
```

### 2. Message Count Consistency

The `Events@odata.count` field should always match the length of the `Events` array. This provides a quick validation check:

```python
if event_data.get("Events@odata.count") != len(event_data.get("Events", [])):
    # Handle inconsistency
```

### 3. Event ID Uniqueness

Each event has a unique `Id` field that can be used for deduplication and tracking.

## Lessons Learned

### 1. Always Validate API Structure

**What we learned:** The Redfish API structure can vary between different HPE systems and firmware versions.

**Implementation:**
- Always check that `Events` field exists and is a list
- Validate that `Events@odata.count` matches the array length
- Handle cases where expected fields are missing
- Use defensive programming to prevent crashes

### 2. Handle Nested Data Carefully

**What we learned:** The nested message structure requires careful parsing to extract the correct data.

**Implementation:**
- Extract messages from the `Events` array, not from the parent object
- Always access the first (and usually only) message in the array
- Handle cases where the array might be empty
- Validate the structure before accessing nested fields

### 3. Error Handling is Critical

**What we learned:** API inconsistencies can cause crashes if not properly handled.

**Implementation:**
- Use try-catch blocks around event parsing
- Return `None` for invalid events instead of crashing
- Log validation failures for debugging
- Graceful fallback for malformed data

### 4. Performance Considerations

**What we learned:** Events can accumulate quickly and impact performance.

**Implementation:**
- Added `--events-limit` configuration option
- Implemented parallel fetching with rate limiting
- Used caching for top-level endpoints
- Processed events in batches

## Implementation Details

### Current Implementation

The HPE Redfish Exporter implements event collection with the following approach:

1. **Fetch Event Collection**: Get the list of event member URLs from `/redfish/v1/Events`
2. **Apply Limits**: Respect the `--events-limit` configuration
3. **Parallel Fetch**: Fetch individual event objects in parallel
4. **Validate Structure**: Check that `Events` field exists and is a list
5. **Count Validation**: Ensure `Events@odata.count` matches array length
6. **Extract Severity**: Get severity from the first message in the array
7. **Aggregate Results**: Count events by severity level

### Key Functions

#### `process_event` Function

The core event processing logic:

```python
def process_event(url: str, result: Any) -> Optional[str]:
    if result and result.status == 200:
        event_data = result.dict
        
        # Validate structure
        if not isinstance(event_data, dict):
            return None
        if "Events" not in event_data or not isinstance(event_data["Events"], list):
            return None
        if len(event_data["Events"]) == 0:
            return None
        
        # Validate count consistency
        event_msgs_count = event_data.get("Events@odata.count", 1)
        event_msgs = event_data["Events"]
        if event_msgs_count != 1 and len(event_msgs) != event_msgs_count:
            return None
        
        # Extract severity
        return event_msgs[0].get("Severity", "Unknown")
    return None
```

#### Error Handling Strategy

The implementation uses a defensive programming approach:

- **Structure Validation**: Check data types before accessing fields
- **Graceful Fallback**: Return `None` for invalid events
- **Parallel Processing**: Handle errors without stopping other requests
- **Logging**: Track fetch errors for debugging

## Prometheus Metrics Generated

### Event Count Metrics
```prometheus
clustorstor_events_total{limit="all"} 747
```

### Severity Distribution Metrics
```prometheus
clustorstor_events_severity{severity="OK"} 120
clustorstor_events_severity{severity="Warning"} 45
clustorstor_events_severity{severity="Critical"} 3
```

## Best Practices

### 1. API Validation

Always validate the API response structure before processing:

```python
if not isinstance(response_data, dict):
    return None
if "Events" not in response_data or not isinstance(response_data["Events"], list):
    return None
```

### 2. Count Consistency

Check that the message count matches the array length:

```python
count = response_data.get("Events@odata.count", 1)
if count != len(response_data.get("Events", [])):
    # Handle inconsistency
```

### 3. Defensive Programming

Use try-catch blocks and validation to prevent crashes:

```python
try:
    # Processing logic
except Exception:
    return None
```

### 4. Performance Optimization

- Use parallel fetching for large event collections
- Implement caching for frequently accessed endpoints
- Apply limits to prevent performance issues
- Process events in batches

## Troubleshooting

### Common Issues

#### 1. Empty Events Array

**Symptom**: `Events` field exists but is empty
**Cause**: No events available or API inconsistency
**Solution**: Return `None` and continue processing other events

#### 2. Missing Events Field

**Symptom**: `Events` field not present in response
**Cause**: API version mismatch or malformed response
**Solution**: Return `None` and log the issue

#### 3. Count Mismatch

**Symptom**: `Events@odata.count` doesn't match array length
**Cause**: API inconsistency or data corruption
**Solution**: Validate and handle gracefully

#### 4. Performance Issues

**Symptom**: Event collection takes too long
**Cause**: Large number of events or slow API
**Solution**: Use `--events-limit` and parallel processing

### Debugging Tips

1. **Check Raw API Response**: Use `curl` to inspect the actual API response
2. **Validate Structure**: Ensure the expected fields are present
3. **Check Counts**: Verify that `Events@odata.count` matches array length
4. **Review Logs**: Look for error messages during event collection
5. **Test Limits**: Use `--events-limit` to test with smaller datasets

## Future Enhancements

### 1. Event Filtering

Add support for filtering events by:
- Time range
- Severity level
- Event type
- Component

### 2. Event Deduplication

Implement deduplication based on:
- Event ID
- Message content
- Timestamp

### 3. Alert Integration

Add integration with alerting systems:
- Prometheus Alertmanager
- External monitoring systems
- Custom alerting rules

### 4. Historical Analysis

Add support for:
- Event trend analysis
- Severity pattern detection
- Component health tracking

## Related Documentation

- [Main README](README.md) - Project overview and setup
- [Performance Tuning](README.md#performance-tuning) - Performance optimization
- [Manual API Usage](manual_api_usage.md) - How to query the API manually
- [HPE Redfish API Documentation](ClusterStor-Redfish-Swordfish-REST-API-7.2-030.pdf) - Official API reference