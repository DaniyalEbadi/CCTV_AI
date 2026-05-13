package stream_diagnostics

import (
	"sync"
	"time"

	"github.com/AlexxIT/go2rtc/pkg/diagnostics"
)

// StreamTracker tracks overall stream health
type StreamTracker struct {
	mu sync.RWMutex

	streamID    string
	diagnostics *diagnostics.DiagnosticsCollector

	// Producer tracking
	producerConnectTime    time.Time
	producerDisconnectTime time.Time
	isProducerConnected    bool

	// Consumer tracking
	consumerCount  int32
	consumerEvents map[string]consumerEvent

	// Buffer tracking
	bufferSize        int
	maxBufferSize     int
	bufferUtilization float64

	// Packet tracking
	packetsPerSecond float64
	bitrate          float64
	droppedPackets   uint64
	totalPackets     uint64

	// Freeze tracking
	freezeCount     uint32
	totalFreezeTime time.Duration
	lastFreezeTime  time.Time
	minInterFreeze  time.Duration
	maxInterFreeze  time.Duration
}

type consumerEvent struct {
	connectTime    time.Time
	disconnectTime time.Time
	connected      bool
	bytesReceived  uint64
}

// NewStreamTracker creates a new stream tracker
func NewStreamTracker(streamID string, diag *diagnostics.DiagnosticsCollector) *StreamTracker {
	return &StreamTracker{
		streamID:       streamID,
		diagnostics:    diag,
		consumerEvents: make(map[string]consumerEvent),
	}
}

// OnProducerConnect records producer connection
func (st *StreamTracker) OnProducerConnect(source string) {
	st.mu.Lock()
	defer st.mu.Unlock()

	st.isProducerConnected = true
	st.producerConnectTime = time.Now()

	if st.diagnostics != nil {
		st.diagnostics.RecordEvent(st.streamID, "producer_connect", "info", 0, map[string]interface{}{
			"source": source,
		})
	}
}

// OnProducerDisconnect records producer disconnection
func (st *StreamTracker) OnProducerDisconnect(reason string) {
	st.mu.Lock()
	defer st.mu.Unlock()

	st.isProducerConnected = false
	st.producerDisconnectTime = time.Now()
	uptime := time.Since(st.producerConnectTime)

	if st.diagnostics != nil {
		st.diagnostics.RecordEvent(st.streamID, "producer_disconnect", "warning", uptime, map[string]interface{}{
			"reason":    reason,
			"uptime_ms": uptime.Milliseconds(),
		})
	}
}

// OnConsumerConnect records consumer connection
func (st *StreamTracker) OnConsumerConnect(consumerID string) {
	st.mu.Lock()
	defer st.mu.Unlock()

	st.consumerCount++
	st.consumerEvents[consumerID] = consumerEvent{
		connectTime: time.Now(),
		connected:   true,
	}

	if st.diagnostics != nil {
		st.diagnostics.RecordEvent(st.streamID, "consumer_connect", "info", 0, map[string]interface{}{
			"consumer_id":     consumerID,
			"total_consumers": st.consumerCount,
		})
	}
}

// OnConsumerDisconnect records consumer disconnection
func (st *StreamTracker) OnConsumerDisconnect(consumerID string, reason string) {
	st.mu.Lock()
	defer st.mu.Unlock()

	if event, ok := st.consumerEvents[consumerID]; ok {
		event.disconnectTime = time.Now()
		event.connected = false
		st.consumerEvents[consumerID] = event
		st.consumerCount--

		duration := event.disconnectTime.Sub(event.connectTime)

		if st.diagnostics != nil {
			st.diagnostics.RecordEvent(st.streamID, "consumer_disconnect", "info", duration, map[string]interface{}{
				"consumer_id":         consumerID,
				"reason":              reason,
				"session_duration":    duration.Milliseconds(),
				"remaining_consumers": st.consumerCount,
			})
		}
	}
}

// OnBufferEvent records buffer-related events
func (st *StreamTracker) OnBufferEvent(size, maxSize int, utilization float64) {
	st.mu.Lock()
	defer st.mu.Unlock()

	st.bufferSize = size
	st.maxBufferSize = maxSize
	st.bufferUtilization = utilization

	severity := "info"
	if utilization > 0.8 {
		severity = "warning"
	}
	if utilization > 0.95 {
		severity = "critical"
	}

	if st.diagnostics != nil {
		st.diagnostics.RecordEvent(st.streamID, "buffer_status", severity, 0, map[string]interface{}{
			"current_size": size,
			"max_size":     maxSize,
			"utilization":  utilization,
		})
	}
}

// OnDroppedPackets records dropped packets
func (st *StreamTracker) OnDroppedPackets(count uint64, reason string) {
	st.mu.Lock()
	defer st.mu.Unlock()

	st.droppedPackets += count

	if st.diagnostics != nil {
		st.diagnostics.RecordEvent(st.streamID, "packets_dropped", "warning", 0, map[string]interface{}{
			"dropped_count": count,
			"total_dropped": st.droppedPackets,
			"reason":        reason,
		})
	}
}

// OnFreeze records freeze event
func (st *StreamTracker) OnFreeze(duration time.Duration) {
	st.mu.Lock()
	defer st.mu.Unlock()

	st.freezeCount++
	st.totalFreezeTime += duration

	if !st.lastFreezeTime.IsZero() {
		interFreeze := time.Since(st.lastFreezeTime)
		if st.minInterFreeze == 0 || interFreeze < st.minInterFreeze {
			st.minInterFreeze = interFreeze
		}
		if interFreeze > st.maxInterFreeze {
			st.maxInterFreeze = interFreeze
		}
	}
	st.lastFreezeTime = time.Now()

	if st.diagnostics != nil {
		st.diagnostics.RecordFreeze(st.streamID, duration)
	}
}

// UpdateStats updates traffic statistics
func (st *StreamTracker) UpdateStats(packetsPerSec float64, bitrateMbps float64) {
	st.mu.Lock()
	defer st.mu.Unlock()

	st.packetsPerSecond = packetsPerSec
	st.bitrate = bitrateMbps

	if st.diagnostics != nil {
		st.diagnostics.RecordEvent(st.streamID, "traffic_stats", "info", 0, map[string]interface{}{
			"packets_per_second": packetsPerSec,
			"bitrate_mbps":       bitrateMbps,
		})
	}
}

// GetStats returns stream statistics
func (st *StreamTracker) GetStats() map[string]interface{} {
	st.mu.RLock()
	defer st.mu.RUnlock()

	avgFreezeTime := time.Duration(0)
	if st.freezeCount > 0 {
		avgFreezeTime = st.totalFreezeTime / time.Duration(st.freezeCount)
	}

	return map[string]interface{}{
		"stream_id":            st.streamID,
		"producer_connected":   st.isProducerConnected,
		"producer_uptime_ms":   time.Since(st.producerConnectTime).Milliseconds(),
		"consumer_count":       st.consumerCount,
		"buffer_size":          st.bufferSize,
		"buffer_max_size":      st.maxBufferSize,
		"buffer_utilization":   st.bufferUtilization,
		"packets_per_second":   st.packetsPerSecond,
		"bitrate_mbps":         st.bitrate,
		"dropped_packets":      st.droppedPackets,
		"total_packets":        st.totalPackets,
		"freeze_count":         st.freezeCount,
		"total_freeze_time_ms": st.totalFreezeTime.Milliseconds(),
		"avg_freeze_time_ms":   avgFreezeTime.Milliseconds(),
		"min_inter_freeze_ms":  st.minInterFreeze.Milliseconds(),
		"max_inter_freeze_ms":  st.maxInterFreeze.Milliseconds(),
	}
}

// GetConsumerStats returns statistics for a specific consumer
func (st *StreamTracker) GetConsumerStats(consumerID string) map[string]interface{} {
	st.mu.RLock()
	defer st.mu.RUnlock()

	event, ok := st.consumerEvents[consumerID]
	if !ok {
		return nil
	}

	return map[string]interface{}{
		"consumer_id":     consumerID,
		"connected":       event.connected,
		"connect_time":    event.connectTime,
		"disconnect_time": event.disconnectTime,
		"bytes_received":  event.bytesReceived,
	}
}

// GetHealth performs health check
func (st *StreamTracker) GetHealth() (healthy bool, issues []string) {
	st.mu.RLock()
	defer st.mu.RUnlock()

	healthy = true
	issues = []string{}

	if !st.isProducerConnected {
		healthy = false
		issues = append(issues, "Producer is disconnected")
	}

	if st.bufferUtilization > 0.95 {
		healthy = false
		issues = append(issues, "Buffer critically full")
	}

	if st.freezeCount > 10 {
		healthy = false
		issues = append(issues, "Excessive freeze events")
	}

	if st.droppedPackets > 1000 {
		healthy = false
		issues = append(issues, "Excessive packet drops")
	}

	if st.minInterFreeze > 0 && st.minInterFreeze < 5*time.Second {
		healthy = false
		issues = append(issues, "Freezes occurring too frequently")
	}

	return
}
