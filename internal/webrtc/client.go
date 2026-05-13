/*
Package webrtc/client.go implements WebRTC client for multiple camera and device types.

Supported protocols:
1. go2rtc: Direct WebSocket connection to go2rtc server
2. WHEP: WebRTC-HTTP Egress Protocol (standard)
3. Kinesis: AWS Kinesis Video Streams (with custom signaling)
4. Wyze: Wyze camera WebRTC bridge (uses Kinesis under the hood)
5. Creality: Creality 3D printer cameras (base64 JSON encoding)
6. Milestone: Milestone XProtect surveillance system
7. OpenIPC: OpenIPC open-source camera firmware
8. SwitchBot: SwitchBot lock/device WebRTC integration

Main components:
- streamsHandler: Dispatcher that routes to specific client based on URL format
- go2rtcClient: Direct WebSocket signaling
- whepClient: Standard WebRTC-HTTP signaling
- Supporting clients: kinesisClient, milestoneClient, etc. (defined in separate files)
*/

package webrtc

import (
	"encoding/base64"
	"errors"
	"io"
	"net/http"
	"net/url"
	"strings"
	"sync"
	"time"

	"github.com/AlexxIT/go2rtc/internal/api/ws"
	"github.com/AlexxIT/go2rtc/internal/streams"
	"github.com/AlexxIT/go2rtc/pkg/core"
	"github.com/AlexxIT/go2rtc/pkg/webrtc"
	"github.com/gorilla/websocket"
	pion "github.com/pion/webrtc/v4"
)

// streamsHandler is the main dispatcher for WebRTC client connections.
// Routes URLs to appropriate client implementation based on scheme and format.
//
// Supported URL formats:
//  1. webrtc:http://host/path/to/api          -> WHEP
//  2. webrtc:ws://host/path/to/api            -> go2rtc or Kinesis/OpenIPC/SwitchBot
//  3. webrtc:http://host/path#format=milestone -> Milestone XProtect
//  4. webrtc:http://host/path#format=wyze     -> Wyze camera
//  5. webrtc:http://host/path#format=creality -> Creality 3D printer
//
// The URL may include a fragment (#) with parameters:
//   - format=kinesis|milestone|wyze|creality|openipc|switchbot
//   - client_id=... (for Kinesis/Wyze)
//   - ice_servers=[...] (ICE server configuration)
//
// Args:
//
//	rawURL: URL string starting with "webrtc:"
//
// Returns:
//
//	core.Producer: Established WebRTC connection
//	error: Connection failed or unsupported format
func streamsHandler(rawURL string) (core.Producer, error) {
	// Parse fragment parameters (e.g., #format=kinesis#client_id=abc)
	var query url.Values
	if i := strings.IndexByte(rawURL, '#'); i > 0 {
		query = streams.ParseQuery(rawURL[i+1:])
		rawURL = rawURL[:i] // Remove fragment from URL
	}

	rawURL = rawURL[7:] // Remove "webrtc:" prefix

	// Extract scheme (ws, wss, http, https)
	if i := strings.IndexByte(rawURL, ':'); i > 0 {
		scheme := rawURL[:i]
		format := query.Get("format")

		// Route based on scheme and format
		switch scheme {
		case "ws", "wss":
			// WebSocket-based signaling
			if format == "kinesis" {
				// AWS Kinesis Video Streams (proprietary signaling)
				// https://aws.amazon.com/kinesis/video-streams/
				return kinesisClient(rawURL, query, "webrtc/kinesis", nil)
			} else if format == "openipc" {
				// OpenIPC cameras (open-source firmware)
				// https://openipc.org/
				return openIPCClient(rawURL, query)
			} else if format == "switchbot" {
				// SwitchBot smart locks and devices
				// https://github.com/OpenWonderLabs/SwitchBotAPI
				return switchbotClient(rawURL, query)
			} else {
				// Default: go2rtc WebSocket signaling
				// Standard go2rtc server connection
				return go2rtcClient(rawURL)
			}

		case "http", "https":
			// HTTP-based signaling (WHEP or proprietary)
			if format == "milestone" {
				// Milestone XProtect VMS (video management system)
				// https://www.milestonexsf.com/
				return milestoneClient(rawURL, query)
			} else if format == "wyze" {
				// Wyze camera WebRTC bridge
				// https://github.com/mrlt8/docker-wyze-bridge
				return wyzeClient(rawURL)
			} else if format == "creality" {
				// Creality 3D printer cameras
				// https://www.creality.com/
				return crealityClient(rawURL)
			} else {
				// Default: WHEP (WebRTC-HTTP Egress Protocol)
				// Standard protocol for WebRTC over HTTP
				// https://www.ietf.org/id/draft-ietf-wish-whep.html
				return whepClient(rawURL)
			}
		}
	}

	return nil, errors.New("unsupported url: " + rawURL)
}

// go2rtcClient establishes WebRTC connection to another go2rtc server.
// Uses WebSocket signaling for SDP and ICE candidate exchange.
//
// Connection flow (trickle ICE):
// 1. Connect WebSocket to go2rtc server
// 2. Create PeerConnection (client mode)
// 3. Generate SDP offer
// 4. Send offer via WebSocket
// 5. Receive answer via WebSocket
// 6. Exchange ICE candidates via WebSocket (trickling)
// 7. Connection established when ICE completes
//
// Supports authentication via URL credentials:
//
//	ws://user:pass@host:port/path -> uses Basic auth
//
// Args:
//
//	url: WebSocket URL to go2rtc server
//	     (e.g., ws://localhost:1984/api/ws?src=camera1)
//
// Returns:
//
//	core.Producer: Established connection to remote stream
//	error: Connection, signaling, or authentication failed
func go2rtcClient(url string) (core.Producer, error) {
	// Step 1: Connect to WebSocket signaling server
	conn, _, err := Dial(url)
	if err != nil {
		return nil, err
	}

	// Ensure connection closes when we exit (on error or success)
	defer conn.Close()

	// Step 2: Create PeerConnection in client mode (we're initiator)
	pc, err := PeerConnection(true)
	if err != nil {
		return nil, err
	}

	defer func() {
		if err != nil {
			_ = pc.Close() // Close on error
		}
	}()

	// Synchronization: wait for connection to establish or error
	var connState core.Waiter
	var connMu sync.Mutex // Protect WebSocket writes

	// Create connection wrapper for Pion
	prod := webrtc.NewConn(pc)
	prod.Mode = core.ModeActiveProducer // We're active initiator
	prod.Protocol = "ws"                // WebSocket signaling
	prod.URL = url

	// Listen to connection events
	prod.Listen(func(msg any) {
		switch msg := msg.(type) {
		case *pion.ICECandidate:
			// Step 6a: Send local ICE candidates to remote
			s := msg.ToJSON().Candidate
			log.Trace().Str("candidate", s).Msg("[webrtc] local")

			connMu.Lock()
			_ = conn.WriteJSON(&ws.Message{Type: "webrtc/candidate", Value: s})
			connMu.Unlock()

		case pion.PeerConnectionState:
			// Track connection state
			switch msg {
			case pion.PeerConnectionStateConnecting:
				// Still negotiating
			case pion.PeerConnectionStateConnected:
				// Successfully established
				connState.Done(nil)
			default:
				// Failed or closed
				connState.Done(errors.New("webrtc: " + msg.String()))
			}
		}
	})

	// Step 3: Generate SDP offer requesting video and audio
	medias := []*core.Media{
		{Kind: core.KindVideo, Direction: core.DirectionRecvonly}, // Receive video
		{Kind: core.KindAudio, Direction: core.DirectionRecvonly}, // Receive audio
		{Kind: core.KindAudio, Direction: core.DirectionSendonly}, // Send audio (mic)
	}

	offer, err := prod.CreateOffer(medias)
	if err != nil {
		return nil, err
	}

	// Step 4: Send offer via WebSocket
	msg := &ws.Message{Type: "webrtc/offer", Value: offer}
	connMu.Lock()
	_ = conn.WriteJSON(msg)
	connMu.Unlock()

	// Step 5: Receive answer via WebSocket
	if err = conn.ReadJSON(msg); err != nil {
		return nil, err
	}

	if msg.Type != "webrtc/answer" {
		err = errors.New("wrong answer: " + msg.String())
		return nil, err
	}

	answer := msg.String()
	if err = prod.SetAnswer(answer); err != nil {
		return nil, err
	}

	// Step 6b: Receive ICE candidates from remote
	go func() {
		var err error

		for {
			// Receive data from remote
			var msg ws.Message
			if err = conn.ReadJSON(&msg); err != nil {
				break
			}

			switch msg.Type {
			case "webrtc/candidate":
				// Only process non-empty candidates
				if msg.Value != nil {
					_ = prod.AddCandidate(msg.String())
				}
			}
		}

		connState.Done(err)
	}()

	// Wait for connection to establish or error
	if err = connState.Wait(); err != nil {
		return nil, err
	}

	return prod, nil
}

// whepClient establishes WebRTC connection using WHEP (WebRTC-HTTP Egress Protocol).
// Standard protocol defined by IETF for server-to-client WebRTC over HTTP.
//
// WHEP flow (complete offer/answer in single HTTP round-trip):
// 1. Create PeerConnection (client mode)
// 2. Generate SDP offer with all candidates (complete offer)
// 3. POST offer to WHEP endpoint
// 4. Receive answer in HTTP response
// 5. Connection established (no trickle ICE)
//
// Advantages over trickle ICE:
// - Single HTTP request/response (simpler)
// - No WebSocket connection needed
// - Works through proxies and firewalls
//
// Args:
//
//	url: HTTP endpoint for WHEP
//	     (e.g., http://192.168.1.100:1984/api/webrtc?src=camera1)
//
// Returns:
//
//	core.Producer: Established WebRTC connection
//	error: Connection or signaling failed
func whepClient(url string) (core.Producer, error) {
	// Step 1: Create PeerConnection in client mode
	pc, err := PeerConnection(true)
	if err != nil {
		log.Error().Err(err).Caller().Send()
		return nil, err
	}

	// Create connection wrapper
	prod := webrtc.NewConn(pc)
	prod.Mode = core.ModeActiveProducer // We're initiator
	prod.Protocol = "http"              // HTTP signaling (not WebSocket)
	prod.URL = url

	// Step 2: Generate complete SDP offer (includes all candidates)
	medias := []*core.Media{
		{Kind: core.KindVideo, Direction: core.DirectionRecvonly}, // Receive video
		{Kind: core.KindAudio, Direction: core.DirectionRecvonly}, // Receive audio
	}

	offer, err := prod.CreateCompleteOffer(medias)
	if err != nil {
		return nil, err
	}

	// Step 3: POST offer to WHEP endpoint
	req, err := http.NewRequest("POST", url, strings.NewReader(offer))
	if err != nil {
		return nil, err
	}
	req.Header.Set("Content-Type", MimeSDP) // Content-Type: application/sdp

	client := http.Client{Timeout: 5 * time.Second}
	defer client.CloseIdleConnections()

	res, err := client.Do(req)
	if err != nil {
		return nil, err
	}

	// Step 4: Receive answer in HTTP response body
	answer, err := io.ReadAll(res.Body)
	if err != nil {
		return nil, err
	}

	// Step 5: Set answer (connection will establish via candidates in offer)
	if err = prod.SetAnswer(string(answer)); err != nil {
		return nil, err
	}

	return prod, nil
}

// Dial establishes WebSocket connection with optional Basic authentication.
// Extracts credentials from URL (ws://user:pass@host) and adds Authorization header.
//
// Args:
//
//	rawURL: WebSocket URL
//	        (e.g., ws://user:pass@localhost:1984/api/ws)
//
// Returns:
//
//	*websocket.Conn: Established WebSocket connection
//	*http.Response: HTTP response from upgrade
//	error: Connection failed or invalid URL
func Dial(rawURL string) (*websocket.Conn, *http.Response, error) {
	u, err := url.Parse(rawURL)
	if err != nil {
		return nil, nil, err
	}

	// No credentials in URL, use default dialer
	if u.User == nil {
		return websocket.DefaultDialer.Dial(rawURL, nil)
	}

	// Extract username and password from URL
	user := u.User.Username()
	pass, _ := u.User.Password()
	u.User = nil // Remove credentials from URL (send via header instead)

	// Create Authorization header for Basic auth
	header := http.Header{
		"Authorization": []string{
			"Basic " + base64.StdEncoding.EncodeToString([]byte(user+":"+pass)),
		},
	}

	// Connect with auth header
	return websocket.DefaultDialer.Dial(u.String(), header)
}
