/* 
Package webrtc/candidates.go manages ICE (Interactive Connectivity Establishment) candidates.

ICE candidates are network addresses that peers can use to establish a WebRTC connection.
They include:
- Host candidates: local network addresses (eth0, wlan0, etc.)
- Server reflexive: address learned from STUN server
- Peer reflexive: address learned from peer during connection
- Relay: address from TURN server (for NAT/firewall traversal)

This file handles:
1. Building candidate list from configured addresses
2. Filtering candidates based on network policies
3. Converting candidates to ICE format
4. Async candidate exchange during connection setup
*/

package webrtc

import (
	"net"
	"strings"
	"sync"

	"github.com/AlexxIT/go2rtc/internal/api/ws"
	"github.com/AlexxIT/go2rtc/pkg/core"
	"github.com/AlexxIT/go2rtc/pkg/webrtc"
	"github.com/AlexxIT/go2rtc/pkg/xnet"
	pion "github.com/pion/webrtc/v4"
)

// Address represents a single ICE candidate address.
// It can be a static host address or a special "stun" placeholder
// that gets resolved to the public IP at runtime.
type Address struct {
	host     string // IP address or "stun" (resolved to public IP)
	Port     string // Port number
	Network  string // "tcp" or "udp"
	Priority uint32 // ICE priority (higher = preferred). Set by AddCandidate() based on order.
}

// Host returns the actual host address.
// If host is "stun", it fetches the cached public IP from STUN resolution.
// Returns empty string if resolution fails (e.g., no internet connectivity).
func (a *Address) Host() string {
	if a.host == "stun" {
		ip, err := webrtc.GetCachedPublicIP()
		if err != nil {
			// STUN failure: log a warning so we can debug long-running sessions
			// but return empty string to avoid creating an invalid candidate.
			log.Warn().Err(err).Msg("[webrtc] STUN public IP unavailable (will skip stun candidate for now)")
			return ""
		}
		return ip.String()
	}
	return a.host
}

// Marshal converts the Address to ICE candidate string format.
// Format: "candidate:0 1 udp 2130706431 192.168.1.100 54321 typ host"
// Returns empty string if host resolution fails.
func (a *Address) Marshal() string {
	if host := a.Host(); host != "" {
		return webrtc.CandidateICE(a.Network, host, a.Port, a.Priority)
	}
	return ""
}

// addresses is the global list of ICE candidates configured by user.
// Built via AddCandidate() calls during init.
var (
	addressesMu sync.RWMutex
	addresses   []*Address
)

// filters contains network filtering rules (whitelist/blacklist for networks, IPs, etc.)
var filters webrtc.Filters

// AddCandidate adds a new ICE candidate address to the global candidate list.
// If network is empty, adds both TCP and UDP variants of the address.
// Priority is auto-assigned based on order (first added = highest priority).
//
// Examples:
//
//	AddCandidate("tcp", "192.168.1.100:8555")  // Single candidate
//	AddCandidate("", "0.0.0.0:8555")           // Adds both tcp and udp
func AddCandidate(network, address string) {
	// If no specific network, add both TCP and UDP variants
	if network == "" {
		AddCandidate("tcp", address)
		AddCandidate("udp", address)
		return
	}

	host, port, err := net.SplitHostPort(address)
	if err != nil {
		// Invalid address format — don't panic, just ignore this input and log
		log.Warn().Err(err).Str("address", address).Msg("[webrtc] AddCandidate: invalid address format")
		return
	}

	// Priority increases for each candidate in order
	// Start from 1 so manual candidates have lower priority than built-in ones
	// Higher priority = preferred by ICE agent
	addressesMu.Lock()
	candidateIndex := 1 + len(addresses)
	priority := webrtc.CandidateHostPriority(network, candidateIndex)

	addresses = append(addresses, &Address{host, port, network, priority})
	addressesMu.Unlock()
}

// GetCandidates returns all configured ICE candidates as strings.
// Filters out candidates with empty host (failed STUN resolution, etc.).
// Returns: ["candidate:0 1 udp ... typ host", ...]
func GetCandidates() (candidates []string) {
	addressesMu.RLock()
	defer addressesMu.RUnlock()

	for _, address := range addresses {
		if candidate := address.Marshal(); candidate != "" {
			candidates = append(candidates, candidate)
		}
	}
	return
}

// FilterCandidate returns true if the candidate should be sent to remote peer.
// Filters out:
// - nil candidates
// - Docker internal IPs (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16 in Docker context)
// - Candidates not in the host whitelist (if filtering enabled)
// - Candidates with network types not in whitelist (e.g., filter out ipv6)
//
// Used to prevent leaking internal network topology or blocking certain network types.
func FilterCandidate(candidate *pion.ICECandidate) bool {
	if candidate == nil {
		log.Trace().Msg("[webrtc] FilterCandidate: nil candidate")
		return false
	}

	// Remove Docker-internal IPs (e.g., docker0 bridge, container IPs)
	// These are useless for external connectivity
	if ip := net.ParseIP(candidate.Address); ip != nil && xnet.Docker.Contains(ip) {
		log.Debug().Str("candidate", candidate.Address).Msg("[webrtc] FilterCandidate: rejected docker internal IP")
		return false
	}

	// Host candidates (local IPs) must be in the configured whitelist
	// Prevents exposing internal network IPs to remote peers
	if candidate.Typ == pion.ICECandidateTypeHost && filters.Candidates != nil {
		if !core.Contains(filters.Candidates, candidate.Address) {
			log.Debug().Str("candidate", candidate.Address).Msg("[webrtc] FilterCandidate: rejected not in host whitelist")
			return false
		}
	}

	// Network type filtering (tcp4, tcp6, udp4, udp6)
	// Allows blocking ipv6-only or tcp-only networks
	if filters.Networks != nil {
		networkType := NetworkType(candidate.Protocol.String(), candidate.Address)
		if !core.Contains(filters.Networks, networkType) {
			log.Debug().
				Str("candidate", candidate.Address).
				Str("networkType", networkType).
				Msg("[webrtc] FilterCandidate: rejected network type")
			return false
		}
	}

	// If reached here, candidate is allowed
	log.Trace().
		Str("candidate", candidate.Address).
		Str("type", candidate.Typ.String()).
		Str("protocol", candidate.Protocol.String()).
		Msg("[webrtc] FilterCandidate: accepted")
	return true
}

// NetworkType converts a network protocol and address to typed network.
// Detects IPv6 vs IPv4 based on a reliable parse; falls back to heuristic if needed.
//
// Examples:
//
//	NetworkType("tcp", "192.168.1.1") -> "tcp4"
//	NetworkType("udp", "::1") -> "udp6"
//	NetworkType("tcp", "2001:db8::1") -> "tcp6"
func NetworkType(network, host string) string {
	// Try reliable parse first
	if ip := net.ParseIP(host); ip != nil {
		if ip.To4() == nil {
			return network + "6"
		}
		return network + "4"
	}

	// Fallback heuristic: ":" presence (covers some corner cases)
	if strings.IndexByte(host, ':') >= 0 {
		return network + "6"
	} else {
		return network + "4"
	}
}

// asyncCandidates sends pre-configured ICE candidates to the remote peer.
// This happens after SDP answer is exchanged.
//
// Flow:
// 1. Check if any candidates arrived before webrtc.Conn was initialized
// 2. Add those buffered candidates to the connection
// 3. Send all configured candidates to remote peer via WebSocket
//
// Why async? Candidates may arrive from remote peer before local connection is ready.
// We buffer them in the transport context and process when ready.
func asyncCandidates(tr *ws.Transport, cons *webrtc.Conn) {
	// Process any candidates that arrived before this point
	tr.WithContext(func(ctx map[any]any) {
		if candidates, ok := ctx["candidate"].([]string); ok {
			// Add buffered candidates to connection
			for _, candidate := range candidates {
				_ = cons.AddCandidate(candidate)
			}

			// Clear buffer since we've processed them
			delete(ctx, "candidate")
		}

		// Register this connection as ready for future candidates
		ctx["webrtc"] = cons
	})

	// Send all pre-configured candidates from server to client
	for _, candidate := range GetCandidates() {
		log.Trace().Str("candidate", candidate).Msg("[webrtc] config")
		tr.Write(&ws.Message{Type: "webrtc/candidate", Value: candidate})
	}
}

// candidateHandler processes incoming ICE candidates from remote peer.
// Candidates may arrive before or after the webrtc.Conn is initialized.
//
// Two cases:
//  1. Connection ready (webrtc.Conn in context):
//     Add candidate directly to connection (immediate ICE probing)
//  2. Connection not ready yet:
//     Buffer candidate in context for later processing
func candidateHandler(tr *ws.Transport, msg *ws.Message) error {
	// Process incoming candidate in sync function
	// Context ensures thread-safe access to transport state
	tr.WithContext(func(ctx map[any]any) {
		candidate := msg.String()
		log.Trace().Str("candidate", candidate).Msg("[webrtc] remote")

		if cons, ok := ctx["webrtc"].(*webrtc.Conn); ok {
			// WebRTC connection already initialized, add candidate immediately
			// This starts ICE probing on this path
			_ = cons.AddCandidate(candidate)
		} else {
			// WebRTC connection not yet initialized, buffer this candidate
			// It will be added when asyncCandidates() is called
			list, _ := ctx["candidate"].([]string)
			ctx["candidate"] = append(list, candidate)
		}
	})

	return nil
}
