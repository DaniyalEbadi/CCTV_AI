package diagnostics_api

import (
	"encoding/json"
	"net/http"
	"strings"
	"time"

	"github.com/AlexxIT/go2rtc/pkg/diagnostics"
)

// DiagnosticsHandler handles diagnostics API requests
type DiagnosticsHandler struct {
	collector *diagnostics.DiagnosticsCollector
}

// NewDiagnosticsHandler creates a new handler
func NewDiagnosticsHandler(collector *diagnostics.DiagnosticsCollector) *DiagnosticsHandler {
	return &DiagnosticsHandler{
		collector: collector,
	}
}

// HandleDiagnostics handles requests to /api/diagnostics
// GET /api/diagnostics - Get summary
// GET /api/diagnostics/events - Get recent events
// GET /api/diagnostics/events?type=freeze - Get events by type
// GET /api/diagnostics/stream/:id - Get stream health
// GET /api/diagnostics/stream/:id/latency - Get latency metrics
func (h *DiagnosticsHandler) HandleDiagnostics(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		w.WriteHeader(http.StatusMethodNotAllowed)
		return
	}

	path := strings.TrimPrefix(r.URL.Path, "/api/diagnostics")
	path = strings.TrimPrefix(path, "/")

	w.Header().Set("Content-Type", "application/json")

	if path == "" {
		// Summary
		summary := h.collector.GetSummary()
		json.NewEncoder(w).Encode(summary)
		return
	}

	parts := strings.Split(path, "/")

	if parts[0] == "events" {
		h.handleEvents(w, r)
		return
	}

	if parts[0] == "stream" && len(parts) > 1 {
		streamID := parts[1]

		if len(parts) > 2 && parts[2] == "latency" {
			h.handleStreamLatency(w, streamID)
		} else {
			h.handleStreamHealth(w, streamID)
		}
		return
	}

	if parts[0] == "all-streams" {
		h.handleAllStreamsHealth(w)
		return
	}

	w.WriteHeader(http.StatusNotFound)
}

// handleEvents returns recent events
func (h *DiagnosticsHandler) handleEvents(w http.ResponseWriter, r *http.Request) {
	eventType := r.URL.Query().Get("type")
	streamID := r.URL.Query().Get("stream")
	limitStr := r.URL.Query().Get("limit")

	limit := 100
	if limitStr != "" {
		_, _ = json.Unmarshal([]byte(limitStr), &limit)
		if limit > 1000 {
			limit = 1000
		}
	}

	var events []diagnostics.StreamEvent

	if eventType != "" {
		events = h.collector.GetEventsByType(eventType)
	} else if streamID != "" {
		events = h.collector.GetEventsByStreamID(streamID)
	} else {
		events = h.collector.GetRecentEvents(limit)
	}

	// Limit results
	if len(events) > limit {
		events = events[len(events)-limit:]
	}

	response := map[string]interface{}{
		"events": events,
		"count":  len(events),
	}

	json.NewEncoder(w).Encode(response)
}

// handleStreamHealth returns health info for a stream
func (h *DiagnosticsHandler) handleStreamHealth(w http.ResponseWriter, streamID string) {
	health := h.collector.GetStreamHealth(streamID)
	if health == nil {
		w.WriteHeader(http.StatusNotFound)
		json.NewEncoder(w).Encode(map[string]string{"error": "stream not found"})
		return
	}

	response := map[string]interface{}{
		"stream_id":            health.StreamID,
		"uptime_ms":            health.LastPacketTime.Sub(health.StartTime).Milliseconds(),
		"total_packets":        health.TotalPackets,
		"dropped_packets":      health.DroppedPackets,
		"freeze_count":         health.FreezeCount,
		"total_freeze_time_ms": health.FreezeTime.Milliseconds(),
		"packet_loss_percent":  health.PacketLossPercent,
		"buffer_overflows":     health.BufferOverflows,
		"connection_resets":    health.ConnectionResets,
		"avg_latency_ms":       health.AvgLatency.Milliseconds(),
		"max_latency_ms":       health.MaxLatency.Milliseconds(),
	}

	json.NewEncoder(w).Encode(response)
}

// handleStreamLatency returns latency metrics
func (h *DiagnosticsHandler) handleStreamLatency(w http.ResponseWriter, streamID string) {
	metrics := h.collector.GetLatencyMetrics(streamID)
	if metrics == nil {
		w.WriteHeader(http.StatusNotFound)
		json.NewEncoder(w).Encode(map[string]string{"error": "no latency data"})
		return
	}

	response := map[string]interface{}{
		"stream_id":          streamID,
		"rtt_ms":             metrics.RTT.Milliseconds(),
		"network_latency_ms": metrics.NetworkLatency.Milliseconds(),
		"processing_time_ms": metrics.ProcessingTime.Milliseconds(),
		"client_buffer_ms":   metrics.ClientBufferTime.Milliseconds(),
		"jitter_ms":          metrics.Jitter.Milliseconds(),
	}

	json.NewEncoder(w).Encode(response)
}

// handleAllStreamsHealth returns health for all streams
func (h *DiagnosticsHandler) handleAllStreamsHealth(w http.ResponseWriter, r *http.Request) {
	allHealth := h.collector.GetAllStreamsHealth()

	streams := make([]map[string]interface{}, 0)
	for _, health := range allHealth {
		stream := map[string]interface{}{
			"stream_id":            health.StreamID,
			"uptime_ms":            health.LastPacketTime.Sub(health.StartTime).Milliseconds(),
			"total_packets":        health.TotalPackets,
			"dropped_packets":      health.DroppedPackets,
			"freeze_count":         health.FreezeCount,
			"total_freeze_time_ms": health.FreezeTime.Milliseconds(),
			"packet_loss_percent":  health.PacketLossPercent,
		}
		streams = append(streams, stream)
	}

	response := map[string]interface{}{
		"streams": streams,
		"count":   len(streams),
	}

	json.NewEncoder(w).Encode(response)
}

// JSON response for critical events
type CriticalEventAlert struct {
	Timestamp time.Time               `json:"timestamp"`
	Event     diagnostics.StreamEvent `json:"event"`
	Severity  string                  `json:"severity"`
	Action    string                  `json:"action"`
}
