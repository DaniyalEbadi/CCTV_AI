# Diagnostics Quick Start Guide

## What You Just Got

A complete **non-invasive diagnostics system** that tracks streaming freezes, latency, and packet loss without touching any core logic.

## Files Created

```
pkg/diagnostics/
├── diagnostics.go              # Core event tracking
├── webrtc_tracker.go           # WebRTC connection diagnostics  
├── stream_tracker.go           # Stream health tracking
├── api_handler.go              # REST API endpoints
├── INTEGRATION_GUIDE.go        # How to integrate into code
├── README.md                   # Full documentation
└── QUICKSTART.md               # This file
```

## The 5-Minute Setup

### Step 1: Copy Files
Already done! Files are in `pkg/diagnostics/`

### Step 2: Add Global Collector (in main.go)
```go
import "github.com/AlexxIT/go2rtc/pkg/diagnostics"

var diagnosticsCollector *diagnostics.DiagnosticsCollector

func init() {
    diagnosticsCollector = diagnostics.NewDiagnosticsCollector(10000, 500)
}
```

### Step 3: Hook Into WebRTC (in internal/webrtc/webrtc.go)
```go
// When creating connection
tracker := webrtc_diag.NewConnectionTracker("stream_name", diagnosticsCollector, 500)

// When receiving packets
tracker.OnPacketReceived(packet)

// When disconnected
tracker.OnDisconnect("reason")
```

### Step 4: Register API (in internal/api/api.go)
```go
handler := diag_api.NewDiagnosticsHandler(diagnosticsCollector)
http.HandleFunc("/api/diagnostics", handler.HandleDiagnostics)
```

### Step 5: Start Using!
```bash
# Get diagnostics
curl http://localhost:1984/api/diagnostics

# Get freeze events
curl "http://localhost:1984/api/diagnostics/events?type=freeze"

# Get stream health
curl http://localhost:1984/api/diagnostics/stream/camera1
```

## What Each Component Tracks

### DiagnosticsCollector (diagnostics.go)
- Global event storage
- Stream health metrics
- Latency measurements
- Event filtering and retrieval

**Use when:**
- Recording any streaming event
- Querying historical data
- Getting system-wide summary

### ConnectionTracker (webrtc_tracker.go)
- RTP packet sequence
- Freeze detection
- RTT measurements
- Jitter and gaps
- Per-connection diagnostics

**Use when:**
- WebRTC connection needs detailed tracking
- You need packet-level diagnostics
- Connection state changes

### StreamTracker (stream_tracker.go)
- Producer/consumer lifecycle
- Buffer status
- Packet drops
- Overall stream health
- Multi-consumer tracking

**Use when:**
- Tracking stream-level events
- Monitoring producer/consumer
- Buffer overflow analysis

## Common Debug Commands

### Check If Stream is Freezing
```bash
curl "http://localhost:1984/api/diagnostics/events?type=freeze&stream=camera1" | jq '.events | length'
```

### Get Latency Breakdown
```bash
curl http://localhost:1984/api/diagnostics/stream/camera1/latency | jq '.rtt_ms, .network_latency_ms, .processing_time_ms'
```

### Monitor in Real-Time
```bash
watch -n 1 'curl -s http://localhost:1984/api/diagnostics | jq ".critical_count, .warning_count"'
```

### Export Events for Analysis
```bash
curl "http://localhost:1984/api/diagnostics/events?limit=1000" | jq '.events' > events.json
```

### Count Freeze Events Per Stream
```bash
curl "http://localhost:1984/api/diagnostics/all-streams" | jq '.streams[] | {id: .stream_id, freezes: .freeze_count}'
```

## Understanding the Output

### Example Stream Health Response
```json
{
  "stream_id": "camera1",
  "uptime_ms": 3600000,          # Running for 1 hour
  "total_packets": 1200000,       # Received 1.2M packets
  "dropped_packets": 150,         # 150 dropped (check why)
  "freeze_count": 5,              # Froze 5 times
  "total_freeze_time_ms": 12500,  # Total 12.5 seconds frozen
  "packet_loss_percent": 0.0125,  # 0.0125% lost
  "buffer_overflows": 3,          # Buffer full 3 times
  "connection_resets": 1,         # 1 disconnection
  "avg_latency_ms": 85,           # Average 85ms latency
  "max_latency_ms": 450           # Peak 450ms latency
}
```

**Red flags:**
- `freeze_count` > 10
- `packet_loss_percent` > 1%
- `buffer_overflows` > 5
- `max_latency_ms` > 1000

### Example Latency Response
```json
{
  "rtt_ms": 45,                   # Network roundtrip 45ms
  "network_latency_ms": 30,       # Pure network delay
  "processing_time_ms": 12,       # Server processing 12ms
  "client_buffer_ms": 3,          # Browser buffer 3ms
  "jitter_ms": 2                  # Jitter variation 2ms
}
```

**Analysis:**
- Total latency = 45ms (good for real-time)
- Most delay is network (30ms)
- Server is fast (12ms)

## Integration Checklist

- [ ] Copy diagnostics files to `pkg/diagnostics/`
- [ ] Create global `diagnosticsCollector` in main.go
- [ ] Import diagnostics in webrtc files
- [ ] Add tracker creation in WebRTC connection setup
- [ ] Hook OnPacketReceived() and OnPacketProcessed()
- [ ] Register API handler
- [ ] Test with: `curl http://localhost:1984/api/diagnostics`
- [ ] Query events: `curl "http://localhost:1984/api/diagnostics/events?type=freeze"`
- [ ] Create monitoring dashboard

## How to Read Event Details

Each event has:
```json
{
  "timestamp": "2026-02-01T10:30:45Z",  # When it happened
  "stream_id": "camera1",               # Which stream
  "event_type": "freeze",               # What happened
  "severity": "critical",               # How bad (info/warning/critical)
  "duration": 2500,                     # How long (milliseconds)
  "details": {                          # Event-specific data
    "freeze_duration_ms": 2500,
    "total_freezes": 5
  }
}
```

## Troubleshooting Integration

### Compiler Error: "undefined diagnostics"
- Check import path: `"github.com/AlexxIT/go2rtc/pkg/diagnostics"`
- Ensure files are in correct directory

### API endpoint returns 404
- Check if handler is registered
- Verify path matches: `/api/diagnostics`
- Check http.HandleFunc call

### Events not recording
- Verify collector is created and not nil
- Check tracker initialization
- Ensure tracker methods are called

## Next: Manual Testing

After integration, test with:

```bash
# 1. Start go2rtc (should start without errors)
# 2. Stream for 30 seconds
# 3. Check events
curl "http://localhost:1984/api/diagnostics/events?limit=10"

# 4. Should see something like:
{
  "events": [
    {
      "timestamp": "...",
      "stream_id": "...",
      "event_type": "producer_connect"
    }
  ]
}
```

## Performance Tuning

Default settings:
- Max events stored: 10,000
- Freeze threshold: 500ms
- Memory usage: ~5MB

Adjust in NewDiagnosticsCollector():
- More events = more memory
- Lower threshold = more freeze detections
- Higher threshold = miss short freezes

## What NOT to Do

❌ Don't modify diagnostics logic for streaming
❌ Don't add heavy processing in event recording
❌ Don't store events indefinitely
❌ Don't query with huge limits in production

## What TO Do

✅ Call tracker methods in hot paths
✅ Use diagnostics to find problems
✅ Keep event limit reasonable (10,000)
✅ Clear old events periodically
✅ Monitor from external systems

## Output Examples

### Stream Health for Healthy Stream
```json
{
  "freeze_count": 0,
  "packet_loss_percent": 0,
  "buffer_overflows": 0,
  "avg_latency_ms": 50
}
```
→ **Good to go!**

### Stream Health with Issues
```json
{
  "freeze_count": 15,
  "packet_loss_percent": 2.5,
  "buffer_overflows": 8,
  "avg_latency_ms": 350
}
```
→ **Investigate network, camera, and bitrate**

## Getting Help

1. **Stream freezing?** → Check `events?type=freeze`
2. **Packet loss?** → Check `events?type=packet_loss`
3. **High latency?** → Check stream latency endpoint
4. **Buffer issues?** → Check `events?type=buffer_overflow`
5. **Connection dropping?** → Check `events?type=connection_reset`

## Advanced: Correlating Events

```bash
# Get all events for one stream
curl "http://localhost:1984/api/diagnostics/events?stream=camera1" | jq '.'

# Sort by timestamp to understand sequence
cat events.json | jq 'sort_by(.timestamp)'

# Find patterns in freezes
cat events.json | jq '.[] | select(.event_type=="freeze") | .duration'
```

---

**You now have a complete diagnostics system!** Start with the checklist above, integrate step by step, and use the API endpoints to track down your streaming issues.
