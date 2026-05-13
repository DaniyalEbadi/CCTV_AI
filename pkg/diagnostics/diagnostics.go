package diagnostics

import (
	"sync"
	"time"
)

// StreamEvent tracks specific streaming events (freeze, lag, packet loss, etc.)
type StreamEvent struct {
	Timestamp  time.Time
	StreamID   string
	EventType  string // "freeze", "lag", "packet_loss", "buffer_overflow", "connection_reset"
	Severity   string // "critical", "warning", "info"
	Duration   time.Duration
	Details    map[string]interface{}
	StackTrace string
}

// LatencyMetrics tracks latency information
type LatencyMetrics struct {
	RTT              time.Duration // Round-trip time
	NetworkLatency   time.Duration // Network delay
	ProcessingTime   time.Duration // Server processing
	ClientBufferTime time.Duration // Client-side buffer
	Jitter           time.Duration // Packet jitter
}

// StreamHealth tracks overall stream health
type StreamHealth struct {
	StreamID          string
	StartTime         time.Time
	LastPacketTime    time.Time
	TotalPackets      uint64
	DroppedPackets    uint64
	FreezeCount       uint32
	FreezeTime        time.Duration
	TotalLatency      time.Duration
	AvgLatency        time.Duration
	MaxLatency        time.Duration
	PacketLossPercent float64
	BufferOverflows   uint32
	ConnectionResets  uint32
}

// DiagnosticsCollector collects all diagnostic information
type DiagnosticsCollector struct {
	mu              sync.RWMutex
	events          []StreamEvent
	streamHealth    map[string]*StreamHealth
	latencyMetrics  map[string]*LatencyMetrics
	maxEventsStored int
	freezeThreshold time.Duration // Time without packets = freeze
}

// NewDiagnosticsCollector creates a new diagnostics collector
func NewDiagnosticsCollector(maxEvents int, freezeThresholdMs int64) *DiagnosticsCollector {
	return &DiagnosticsCollector{
		events:          make([]StreamEvent, 0, maxEvents),
		streamHealth:    make(map[string]*StreamHealth),
		latencyMetrics:  make(map[string]*LatencyMetrics),
		maxEventsStored: maxEvents,
		freezeThreshold: time.Duration(freezeThresholdMs) * time.Millisecond,
	}
}

// RecordEvent records a streaming event
func (dc *DiagnosticsCollector) RecordEvent(streamID, eventType, severity string, duration time.Duration, details map[string]interface{}) {
	dc.mu.Lock()
	defer dc.mu.Unlock()

	event := StreamEvent{
		Timestamp: time.Now(),
		StreamID:  streamID,
		EventType: eventType,
		Severity:  severity,
		Duration:  duration,
		Details:   details,
	}

	dc.events = append(dc.events, event)

	// Keep only last N events
	if len(dc.events) > dc.maxEventsStored {
		dc.events = dc.events[len(dc.events)-dc.maxEventsStored:]
	}
}

// RecordFreeze records a freeze event
func (dc *DiagnosticsCollector) RecordFreeze(streamID string, duration time.Duration) {
	dc.mu.Lock()
	defer dc.mu.Unlock()

	health, ok := dc.streamHealth[streamID]
	if !ok {
		health = &StreamHealth{
			StreamID:  streamID,
			StartTime: time.Now(),
		}
		dc.streamHealth[streamID] = health
	}

	health.FreezeCount++
	health.FreezeTime += duration

	dc.RecordEventLocked(streamID, "freeze", "critical", duration, map[string]interface{}{
		"freeze_duration_ms": duration.Milliseconds(),
		"total_freezes":      health.FreezeCount,
	})
}

// RecordPacketLoss records packet loss
func (dc *DiagnosticsCollector) RecordPacketLoss(streamID string, lost, total uint64) {
	dc.mu.Lock()
	defer dc.mu.Unlock()

	health, ok := dc.streamHealth[streamID]
	if !ok {
		health = &StreamHealth{
			StreamID:  streamID,
			StartTime: time.Now(),
		}
		dc.streamHealth[streamID] = health
	}

	health.DroppedPackets = lost
	health.TotalPackets = total
	if total > 0 {
		health.PacketLossPercent = (float64(lost) / float64(total)) * 100
	}

	dc.RecordEventLocked(streamID, "packet_loss", "warning", 0, map[string]interface{}{
		"lost_packets":    lost,
		"total_packets":   total,
		"loss_percentage": health.PacketLossPercent,
	})
}

// RecordBufferOverflow records buffer overflow
func (dc *DiagnosticsCollector) RecordBufferOverflow(streamID string) {
	dc.mu.Lock()
	defer dc.mu.Unlock()

	health, ok := dc.streamHealth[streamID]
	if !ok {
		health = &StreamHealth{
			StreamID:  streamID,
			StartTime: time.Now(),
		}
		dc.streamHealth[streamID] = health
	}

	health.BufferOverflows++

	dc.RecordEventLocked(streamID, "buffer_overflow", "warning", 0, map[string]interface{}{
		"total_overflows": health.BufferOverflows,
	})
}

// RecordLatency records latency metrics
func (dc *DiagnosticsCollector) RecordLatency(streamID string, metrics LatencyMetrics) {
	dc.mu.Lock()
	defer dc.mu.Unlock()

	health, ok := dc.streamHealth[streamID]
	if !ok {
		health = &StreamHealth{
			StreamID:  streamID,
			StartTime: time.Now(),
		}
		dc.streamHealth[streamID] = health
	}

	dc.latencyMetrics[streamID] = &metrics

	totalLatency := metrics.RTT + metrics.NetworkLatency + metrics.ProcessingTime

	if health.TotalLatency == 0 {
		health.AvgLatency = totalLatency
		health.MaxLatency = totalLatency
	} else {
		health.MaxLatency = max(health.MaxLatency, totalLatency)
		health.AvgLatency = (health.AvgLatency + totalLatency) / 2
	}

	health.TotalLatency = totalLatency

	severity := "info"
	if totalLatency > 1000*time.Millisecond {
		severity = "warning"
	}
	if totalLatency > 3000*time.Millisecond {
		severity = "critical"
	}

	dc.RecordEventLocked(streamID, "latency", severity, 0, map[string]interface{}{
		"rtt_ms":             metrics.RTT.Milliseconds(),
		"network_latency_ms": metrics.NetworkLatency.Milliseconds(),
		"processing_time_ms": metrics.ProcessingTime.Milliseconds(),
		"client_buffer_ms":   metrics.ClientBufferTime.Milliseconds(),
		"jitter_ms":          metrics.Jitter.Milliseconds(),
		"total_latency_ms":   totalLatency.Milliseconds(),
	})
}

// RecordConnectionReset records connection reset
func (dc *DiagnosticsCollector) RecordConnectionReset(streamID string, reason string) {
	dc.mu.Lock()
	defer dc.mu.Unlock()

	health, ok := dc.streamHealth[streamID]
	if !ok {
		health = &StreamHealth{
			StreamID:  streamID,
			StartTime: time.Now(),
		}
		dc.streamHealth[streamID] = health
	}

	health.ConnectionResets++

	dc.RecordEventLocked(streamID, "connection_reset", "critical", 0, map[string]interface{}{
		"reason":       reason,
		"total_resets": health.ConnectionResets,
	})
}

// RecordPacket records every packet for timing analysis
func (dc *DiagnosticsCollector) RecordPacket(streamID string, packetSize int, seqNum uint32) {
	dc.mu.Lock()
	defer dc.mu.Unlock()

	health, ok := dc.streamHealth[streamID]
	if !ok {
		health = &StreamHealth{
			StreamID:  streamID,
			StartTime: time.Now(),
		}
		dc.streamHealth[streamID] = health
	}

	health.TotalPackets++
	health.LastPacketTime = time.Now()
}

// RecordEventLocked internal helper (must be called with lock held)
func (dc *DiagnosticsCollector) RecordEventLocked(streamID, eventType, severity string, duration time.Duration, details map[string]interface{}) {
	event := StreamEvent{
		Timestamp: time.Now(),
		StreamID:  streamID,
		EventType: eventType,
		Severity:  severity,
		Duration:  duration,
		Details:   details,
	}

	dc.events = append(dc.events, event)

	if len(dc.events) > dc.maxEventsStored {
		dc.events = dc.events[len(dc.events)-dc.maxEventsStored:]
	}
}

// GetStreamHealth returns health info for a stream
func (dc *DiagnosticsCollector) GetStreamHealth(streamID string) *StreamHealth {
	dc.mu.RLock()
	defer dc.mu.RUnlock()

	if health, ok := dc.streamHealth[streamID]; ok {
		return health
	}
	return nil
}

// GetLatencyMetrics returns latency metrics for a stream
func (dc *DiagnosticsCollector) GetLatencyMetrics(streamID string) *LatencyMetrics {
	dc.mu.RLock()
	defer dc.mu.RUnlock()

	if metrics, ok := dc.latencyMetrics[streamID]; ok {
		return metrics
	}
	return nil
}

// GetRecentEvents returns recent events
func (dc *DiagnosticsCollector) GetRecentEvents(limit int) []StreamEvent {
	dc.mu.RLock()
	defer dc.mu.RUnlock()

	if limit > len(dc.events) {
		limit = len(dc.events)
	}

	result := make([]StreamEvent, limit)
	copy(result, dc.events[len(dc.events)-limit:])
	return result
}

// GetEventsByType returns events of a specific type
func (dc *DiagnosticsCollector) GetEventsByType(eventType string) []StreamEvent {
	dc.mu.RLock()
	defer dc.mu.RUnlock()

	var result []StreamEvent
	for _, e := range dc.events {
		if e.EventType == eventType {
			result = append(result, e)
		}
	}
	return result
}

// GetEventsByStreamID returns events for a specific stream
func (dc *DiagnosticsCollector) GetEventsByStreamID(streamID string) []StreamEvent {
	dc.mu.RLock()
	defer dc.mu.RUnlock()

	var result []StreamEvent
	for _, e := range dc.events {
		if e.StreamID == streamID {
			result = append(result, e)
		}
	}
	return result
}

// GetAllStreamsHealth returns health for all streams
func (dc *DiagnosticsCollector) GetAllStreamsHealth() map[string]*StreamHealth {
	dc.mu.RLock()
	defer dc.mu.RUnlock()

	result := make(map[string]*StreamHealth)
	for k, v := range dc.streamHealth {
		result[k] = v
	}
	return result
}

// ClearOldEvents removes events older than duration
func (dc *DiagnosticsCollector) ClearOldEvents(duration time.Duration) {
	dc.mu.Lock()
	defer dc.mu.Unlock()

	cutoff := time.Now().Add(-duration)
	var filtered []StreamEvent

	for _, e := range dc.events {
		if e.Timestamp.After(cutoff) {
			filtered = append(filtered, e)
		}
	}

	dc.events = filtered
}

// GetSummary returns a summary of all diagnostics
func (dc *DiagnosticsCollector) GetSummary() map[string]interface{} {
	dc.mu.RLock()
	defer dc.mu.RUnlock()

	criticalCount := 0
	warningCount := 0
	freezeCount := 0
	packetLossCount := 0

	for _, e := range dc.events {
		switch e.Severity {
		case "critical":
			criticalCount++
		case "warning":
			warningCount++
		}

		switch e.EventType {
		case "freeze":
			freezeCount++
		case "packet_loss":
			packetLossCount++
		}
	}

	return map[string]interface{}{
		"total_events":      len(dc.events),
		"critical_count":    criticalCount,
		"warning_count":     warningCount,
		"freeze_count":      freezeCount,
		"packet_loss_count": packetLossCount,
		"streams":           len(dc.streamHealth),
	}
}

func max(a, b time.Duration) time.Duration {
	if a > b {
		return a
	}
	return b
}
