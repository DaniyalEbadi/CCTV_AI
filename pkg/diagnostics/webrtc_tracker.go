package webrtc_diagnostics

import (
	"sync"
	"time"

	"github.com/AlexxIT/go2rtc/pkg/diagnostics"
	"github.com/pion/rtp"
)

// ConnectionTracker tracks WebRTC connection health
type ConnectionTracker struct {
	mu sync.RWMutex

	// Timing metrics
	lastPacketTime     time.Time
	lastProcessedTime  time.Time
	freezeStartTime    time.Time
	isFrozen           bool
	consecutiveFreezes uint32

	// Packet tracking
	lastSeqNum    uint32
	lastTimestamp uint32
	packetCount   uint64
	seqNumGaps    uint64
	timestampGaps uint64

	// Latency tracking
	lastRTT       time.Duration
	rttSamples    []time.Duration
	maxRTTSamples int

	// Connection state
	isConnected         bool
	connectionStartTime time.Time

	// Reference to diagnostics collector
	diagnostics     *diagnostics.DiagnosticsCollector
	streamID        string
	freezeThreshold time.Duration
}

// NewConnectionTracker creates a new connection tracker
func NewConnectionTracker(streamID string, diag *diagnostics.DiagnosticsCollector, freezeThresholdMs int64) *ConnectionTracker {
	return &ConnectionTracker{
		streamID:          streamID,
		diagnostics:       diag,
		freezeThreshold:   time.Duration(freezeThresholdMs) * time.Millisecond,
		maxRTTSamples:     100,
		rttSamples:        make([]time.Duration, 0, 100),
		lastPacketTime:    time.Now(),
		lastProcessedTime: time.Now(),
	}
}

// OnConnect records connection established
func (ct *ConnectionTracker) OnConnect() {
	ct.mu.Lock()
	defer ct.mu.Unlock()

	ct.isConnected = true
	ct.connectionStartTime = time.Now()
	ct.lastPacketTime = time.Now()
	ct.lastProcessedTime = time.Now()

	if ct.diagnostics != nil {
		ct.diagnostics.RecordEvent(ct.streamID, "connection_established", "info", 0, map[string]interface{}{
			"timestamp": time.Now(),
		})
	}
}

// OnDisconnect records connection lost
func (ct *ConnectionTracker) OnDisconnect(reason string) {
	ct.mu.Lock()
	defer ct.mu.Unlock()

	ct.isConnected = false
	duration := time.Since(ct.connectionStartTime)

	if ct.diagnostics != nil {
		ct.diagnostics.RecordConnectionReset(ct.streamID, reason)
		ct.diagnostics.RecordEvent(ct.streamID, "connection_closed", "info", duration, map[string]interface{}{
			"reason":          reason,
			"connection_time": duration.Milliseconds(),
		})
	}
}

// OnPacketReceived tracks incoming RTP packets
func (ct *ConnectionTracker) OnPacketReceived(packet *rtp.Packet) {
	ct.mu.Lock()
	defer ct.mu.Unlock()

	now := time.Now()

	// Check for freeze (no packets received)
	timeSinceLastPacket := now.Sub(ct.lastPacketTime)
	if timeSinceLastPacket > ct.freezeThreshold && !ct.isFrozen {
		ct.isFrozen = true
		ct.freezeStartTime = ct.lastPacketTime
		ct.consecutiveFreezes++

		if ct.diagnostics != nil {
			ct.diagnostics.RecordEvent(ct.streamID, "freeze_start", "critical", timeSinceLastPacket, map[string]interface{}{
				"time_since_last_packet_ms": timeSinceLastPacket.Milliseconds(),
				"freeze_count":              ct.consecutiveFreezes,
			})
		}
	}

	// Check for freeze recovery
	if ct.isFrozen && timeSinceLastPacket <= ct.freezeThreshold {
		freezeDuration := now.Sub(ct.freezeStartTime)
		ct.isFrozen = false

		if ct.diagnostics != nil {
			ct.diagnostics.RecordFreeze(ct.streamID, freezeDuration)
		}
	}

	// Check for sequence number gaps
	if ct.lastSeqNum != 0 {
		expectedSeq := ct.lastSeqNum + 1
		if packet.SequenceNumber != expectedSeq {
			ct.seqNumGaps++

			if ct.diagnostics != nil {
				ct.diagnostics.RecordEvent(ct.streamID, "sequence_gap", "warning", 0, map[string]interface{}{
					"expected_seq": expectedSeq,
					"actual_seq":   packet.SequenceNumber,
					"total_gaps":   ct.seqNumGaps,
					"gap_size":     int32(packet.SequenceNumber) - int32(expectedSeq),
				})
			}
		}
	}

	// Check for timestamp discontinuity
	if ct.lastTimestamp != 0 && packet.Timestamp != ct.lastTimestamp {
		// Only flag if it's not a normal increment
		expectedDelta := uint32(3600) // Common RTP timestamp delta for video
		actualDelta := packet.Timestamp - ct.lastTimestamp

		if actualDelta > expectedDelta*2 || actualDelta < expectedDelta/2 {
			ct.timestampGaps++
		}
	}

	ct.lastPacketTime = now
	ct.lastSeqNum = packet.SequenceNumber
	ct.lastTimestamp = packet.Timestamp
	ct.packetCount++

	if ct.diagnostics != nil {
		ct.diagnostics.RecordPacket(ct.streamID, len(packet.Payload), packet.SequenceNumber)
	}
}

// OnPacketProcessed records when packet is processed
func (ct *ConnectionTracker) OnPacketProcessed(packet *rtp.Packet, processingTimeMs int64) {
	ct.mu.Lock()
	defer ct.mu.Unlock()

	now := time.Now()
	ct.lastProcessedTime = now

	if ct.diagnostics != nil {
		ct.diagnostics.RecordEvent(ct.streamID, "packet_processed", "info", 0, map[string]interface{}{
			"processing_time_ms": processingTimeMs,
			"seq_num":            packet.SequenceNumber,
			"payload_size":       len(packet.Payload),
		})
	}
}

// RecordRTT records round-trip time measurement
func (ct *ConnectionTracker) RecordRTT(rtt time.Duration) {
	ct.mu.Lock()
	defer ct.mu.Unlock()

	ct.lastRTT = rtt
	ct.rttSamples = append(ct.rttSamples, rtt)

	if len(ct.rttSamples) > ct.maxRTTSamples {
		ct.rttSamples = ct.rttSamples[1:]
	}

	severity := "info"
	if rtt > 500*time.Millisecond {
		severity = "warning"
	}
	if rtt > 1000*time.Millisecond {
		severity = "critical"
	}

	if ct.diagnostics != nil {
		ct.diagnostics.RecordEvent(ct.streamID, "rtt_measurement", severity, 0, map[string]interface{}{
			"rtt_ms": rtt.Milliseconds(),
		})
	}
}

// RecordPacketLoss records RTCP packet loss report
func (ct *ConnectionTracker) RecordPacketLoss(lostPackets, totalPackets uint64) {
	ct.mu.Lock()
	defer ct.mu.Unlock()

	if ct.diagnostics != nil {
		ct.diagnostics.RecordPacketLoss(ct.streamID, lostPackets, totalPackets)
	}
}

// RecordBufferOverflow records when send buffer overflows
func (ct *ConnectionTracker) RecordBufferOverflow() {
	ct.mu.Lock()
	defer ct.mu.Unlock()

	if ct.diagnostics != nil {
		ct.diagnostics.RecordBufferOverflow(ct.streamID)
	}
}

// GetStats returns current connection statistics
func (ct *ConnectionTracker) GetStats() map[string]interface{} {
	ct.mu.RLock()
	defer ct.mu.RUnlock()

	avgRTT := time.Duration(0)
	maxRTT := time.Duration(0)

	if len(ct.rttSamples) > 0 {
		for _, rtt := range ct.rttSamples {
			avgRTT += rtt
			if rtt > maxRTT {
				maxRTT = rtt
			}
		}
		avgRTT /= time.Duration(len(ct.rttSamples))
	}

	timeSinceLastPacket := time.Since(ct.lastPacketTime)
	isCurrentlyFrozen := timeSinceLastPacket > ct.freezeThreshold

	return map[string]interface{}{
		"stream_id":                 ct.streamID,
		"is_connected":              ct.isConnected,
		"total_packets":             ct.packetCount,
		"sequence_gaps":             ct.seqNumGaps,
		"timestamp_gaps":            ct.timestampGaps,
		"consecutive_freezes":       ct.consecutiveFreezes,
		"is_currently_frozen":       isCurrentlyFrozen,
		"time_since_last_packet_ms": timeSinceLastPacket.Milliseconds(),
		"last_rtt_ms":               ct.lastRTT.Milliseconds(),
		"avg_rtt_ms":                avgRTT.Milliseconds(),
		"max_rtt_ms":                maxRTT.Milliseconds(),
		"connection_uptime_ms":      time.Since(ct.connectionStartTime).Milliseconds(),
	}
}

// CheckHealth performs a health check
func (ct *ConnectionTracker) CheckHealth() (healthy bool, issues []string) {
	ct.mu.RLock()
	defer ct.mu.RUnlock()

	healthy = true
	issues = []string{}

	timeSinceLastPacket := time.Since(ct.lastPacketTime)

	if timeSinceLastPacket > ct.freezeThreshold {
		healthy = false
		issues = append(issues, "Currently frozen - no packets for "+timeSinceLastPacket.String())
	}

	if ct.seqNumGaps > 10 {
		healthy = false
		issues = append(issues, "High sequence number gaps detected")
	}

	if ct.lastRTT > 2000*time.Millisecond {
		healthy = false
		issues = append(issues, "RTT critically high: "+ct.lastRTT.String())
	}

	if ct.consecutiveFreezes > 5 {
		healthy = false
		issues = append(issues, "Multiple consecutive freezes detected")
	}

	return
}
