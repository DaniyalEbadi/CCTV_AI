/*
Package webrtc/webrtc_test.go contains unit tests for WebRTC message parsing.

Tests cover:
- API v1: Raw SDP format (backward compatibility)
- API v2: JSON SessionDescription format (modern)
- SDP parsing: Verify Pion can parse responses
*/

package webrtc

import (
	"encoding/json"
	"strings"
	"testing"

	"github.com/AlexxIT/go2rtc/internal/api/ws"
	pion "github.com/pion/webrtc/v4"
	"github.com/stretchr/testify/require"
)

// TestWebRTCAPIv1 tests the original raw SDP message format.
// Messages are sent as plain text SDP wrapped in ws.Message.
//
// Format: {"type":"webrtc/offer","value":"v=0\n..."}
func TestWebRTCAPIv1(t *testing.T) {
	// Example WebSocket message with raw SDP
	raw := `{"type":"webrtc/offer","value":"v=0\n..."}`

	// Parse message
	msg := new(ws.Message)
	err := json.Unmarshal([]byte(raw), msg)
	require.Nil(t, err)

	// Verify message contains SDP
	require.Equal(t, "v=0\n...", msg.String())
}

// TestWebRTCAPIv2 tests the modern JSON SessionDescription format.
// Messages are sent as JSON objects with type and SDP.
//
// Format: {"type":"webrtc","value":{"type":"offer","sdp":"v=0\n...","ice_servers":[...]}}
func TestWebRTCAPIv2(t *testing.T) {
	// Example WebSocket message with JSON SDP and ICE servers
	raw := `{"type":"webrtc","value":{"type":"offer","sdp":"v=0\n...","ice_servers":[{"urls":["stun:stun.l.google.com:19302"]}]}}`

	// Parse message
	msg := new(ws.Message)
	err := json.Unmarshal([]byte(raw), msg)
	require.Nil(t, err)

	// Extract SessionDescription
	var offer struct {
		Type       string           `json:"type"`        // "offer" or "answer"
		SDP        string           `json:"sdp"`         // SDP string
		ICEServers []pion.ICEServer `json:"ice_servers"` // Optional ICE servers
	}
	err = msg.Unmarshal(&offer)
	require.Nil(t, err)

	// Verify parsed values
	require.Equal(t, "offer", offer.Type)
	require.Equal(t, "v=0\n...", offer.SDP)
	require.Equal(t, "stun:stun.l.google.com:19302", offer.ICEServers[0].URLs[0])
}

// TestCrealitySDP tests SDP fixup for Creality cameras.
// Creality cameras send malformed SDP with x-google attributes.
// This test verifies we can remove those attributes.
func TestCrealitySDP(t *testing.T) {
	// Real-world SDP from Creality camera
	sdp := `v=0
o=- 1495799811084970 1495799811084970 IN IP4 0.0.0.0
s=-
t=0 0
a=msid-semantic:WMS *
a=group:BUNDLE 0
m=video 9 UDP/TLS/RTP/SAVPF 96 98
a=rtcp-fb:98 nack
a=rtcp-fb:98 nack pli
a=fmtp:96 profile-level-id=42e01f;level-asymmetry-allowed=1
a=fmtp:98 profile-level-id=42e01f;packetization-mode=1;level-asymmetry-allowed=1
a=fmtp:98 x-google-max-bitrate=6000;x-google-min-bitrate=2000;x-google-start-bitrate=4000
a=rtpmap:96 H264/90000
a=rtpmap:98 H264/90000
a=ssrc:1 cname:pear
c=IN IP4 0.0.0.0
a=sendonly
a=mid:0
a=rtcp-mux
a=ice-ufrag:7AVa
a=ice-pwd:T+F/5y05Paw+mtG5Jrd8N3
a=ice-options:trickle
a=fingerprint:sha-256 A5:AB:C0:4E:29:5B:BD:3B:7D:88:24:6C:56:6B:2A:79:A3:76:99:35:57:75:AD:C8:5A:A6:34:20:88:1B:68:EF
a=setup:passive
a=candidate:1 1 UDP 2015363327 172.22.233.10 48929 typ host
a=candidate:2 1 TCP 1015021823 172.22.233.10 0 typ host tcptype active
a=candidate:3 1 TCP 1010827519 172.22.233.10 60677 typ host tcptype passive
`

	// Fix SDP
	sdp, err := fixCrealitySDP(sdp)
	require.Nil(t, err)

	// Verify x-google attributes removed
	require.False(t, strings.Contains(sdp, "x-google-max-bitrate"))
	require.False(t, strings.Contains(sdp, "x-google-min-bitrate"))
	require.False(t, strings.Contains(sdp, "x-google-start-bitrate"))
}
