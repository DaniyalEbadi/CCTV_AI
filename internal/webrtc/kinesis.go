/*
Package webrtc/kinesis.go implements WebRTC client for AWS Kinesis Video Streams.

AWS Kinesis Video Streams provides secure, low-latency video ingestion and storage.
The WebRTC signaling protocol differs from standard WebRTC:
- Uses WebSocket with JSON message format
- Sends SDP offer/answer wrapped in Kinesis-specific message envelope
- Messages contain "action" field and "messagePayload" (JSON-encoded SDP)
- Supports trickle ICE (candidates exchanged during connection)

Also handles:
- Wyze cameras (use Kinesis WebRTC backend)
- Other vendors using Kinesis SDK

Connection flow:
1. Connect WebSocket to Kinesis signaling server
2. Create PeerConnection with ICE servers from config
3. Create SDP offer
4. Wrap offer in Kinesis message format and send
5. Receive Kinesis answer message
6. Exchange ICE candidates (trickle ICE)
7. Connection established when ICE completes
*/

package webrtc

import (
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"time"

	"github.com/AlexxIT/go2rtc/pkg/core"
	"github.com/AlexxIT/go2rtc/pkg/webrtc"
	"github.com/gorilla/websocket"
	pion "github.com/pion/webrtc/v4"
)

// kinesisRequest is the Kinesis signaling message format sent to server.
// All fields are required by AWS Kinesis protocol.
type kinesisRequest struct {
	Action   string `json:"action"`            // "SDP_OFFER" or "ICE_CANDIDATE"
	ClientID string `json:"recipientClientId"` // Recipient client ID (for routing)
	Payload  []byte `json:"messagePayload"`    // JSON-encoded SDP or ICE candidate
}

// String returns a human-readable representation of the request.
func (k kinesisRequest) String() string {
	return fmt.Sprintf("action=%s, payload=%s", k.Action, k.Payload)
}

// kinesisResponse is the Kinesis signaling message format received from server.
type kinesisResponse struct {
	Payload []byte `json:"messagePayload"` // JSON-encoded SDP or ICE candidate
	Type    string `json:"messageType"`    // "SDP_ANSWER" or "ICE_CANDIDATE"
}

// String returns a human-readable representation of the response.
func (k kinesisResponse) String() string {
	return fmt.Sprintf("type=%s, payload=%s", k.Type, k.Payload)
}

// kinesisClient establishes WebRTC connection via AWS Kinesis Video Streams.
//
// The sdpOffer parameter is a callback that allows customization of the offer
// for different camera types (e.g., Wyze cameras send different parameters).
//
// Connection flow:
// 1. Connect to Kinesis signaling WebSocket
// 2. Load ICE servers from query params
// 3. Create PeerConnection
// 4. Create SDP offer (custom or default)
// 5. Send offer wrapped in Kinesis message
// 6. Receive answer wrapped in Kinesis message
// 7. Exchange ICE candidates (trickle ICE)
// 8. Connection established
//
// Args:
//
//	rawURL: WebSocket URL to Kinesis signaling server
//	        (e.g., wss://kinesisvideo.us-east-1.amazonaws.com/...)
//	query: URL query parameters
//	       - client_id: This client's ID (for routing)
//	       - ice_servers: Base64-encoded JSON with ICE server list
//	format: Format name for logging ("webrtc/kinesis", "webrtc/wyze", etc.)
//	sdpOffer: Optional callback to generate custom SDP offer
//	          If nil, uses default SDP offer (video + audio)
//
// Returns:
//
//	core.Producer: Established WebRTC connection
//	error: WebSocket connection, signaling, or SDP error
func kinesisClient(
	rawURL string, query url.Values, format string,
	sdpOffer func(prod *webrtc.Conn, query url.Values) (any, error),
) (core.Producer, error) {
	// Step 1: Connect to Kinesis WebSocket signaling server
	conn, _, err := websocket.DefaultDialer.Dial(rawURL, nil)
	if err != nil {
		return nil, err
	}

	// Step 2: Load ICE servers from query params (base64-encoded JSON)
	conf := pion.Configuration{}

	if s := query.Get("ice_servers"); s != "" {
		// Decode base64 JSON with ICE server list
		conf.ICEServers, err = webrtc.UnmarshalICEServers([]byte(s))
		if err != nil {
			log.Warn().Err(err).Caller().Send()
		}
	}

	// Close WebSocket when exiting (either on error or after getting producer)
	defer conn.Close()

	// Step 3: Create PeerConnection with Kinesis config
	api, err := webrtc.NewAPI()
	if err != nil {
		return nil, err
	}

	pc, err := api.NewPeerConnection(conf)
	if err != nil {
		return nil, err
	}

	// Synchronization: buffer ICE candidates that arrive before offer is sent
	var sendOffer core.Waiter

	// Synchronization: wait for connection to establish or error
	var connState core.Waiter

	// Message envelope for Kinesis
	req := kinesisRequest{
		ClientID: query.Get("client_id"), // Client ID for routing
	}

	// Create connection wrapper
	prod := webrtc.NewConn(pc)
	prod.FormatName = format            // "webrtc/kinesis" or "webrtc/wyze"
	prod.Mode = core.ModeActiveProducer // We're active initiator
	prod.Protocol = "ws"                // WebSocket signaling
	prod.URL = rawURL

	// Listen to connection events
	prod.Listen(func(msg any) {
		switch msg := msg.(type) {
		case *pion.ICECandidate:
			// Wait for offer to be sent before sending candidates
			_ = sendOffer.Wait()

			// Wrap ICE candidate in Kinesis message format
			req.Action = "ICE_CANDIDATE"
			req.Payload, _ = json.Marshal(msg.ToJSON())

			// Send candidate via WebSocket
			if err = conn.WriteJSON(&req); err != nil {
				connState.Done(err)
				return
			}

			log.Trace().Msgf("[webrtc] kinesis send: %s", req)

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

	// Step 4: Create SDP offer
	var payload any

	if sdpOffer == nil {
		// Default offer: video + audio (both receive)
		medias := []*core.Media{
			{Kind: core.KindVideo, Direction: core.DirectionRecvonly},
			{Kind: core.KindAudio, Direction: core.DirectionRecvonly},
		}

		var offer string
		if offer, err = prod.CreateOffer(medias); err != nil {
			return nil, err
		}

		// Wrap in Pion SessionDescription (Kinesis expects this format)
		payload = pion.SessionDescription{
			Type: pion.SDPTypeOffer,
			SDP:  offer,
		}
	} else {
		// Custom offer generation (e.g., Wyze cameras)
		if payload, err = sdpOffer(prod, query); err != nil {
			return nil, err
		}
	}

	// Step 5: Send offer wrapped in Kinesis message
	req.Action = "SDP_OFFER"
	req.Payload, _ = json.Marshal(payload)

	if err = conn.WriteJSON(req); err != nil {
		return nil, err
	}

	log.Trace().Msgf("[webrtc] kinesis send: %s", req)

	// Signal that offer has been sent (ICE candidates can now be sent)
	sendOffer.Done(nil)

	// Step 6-7: Receive answer and exchange ICE candidates
	go func() {
		var err error

		// Loop: receive messages from server (answer + candidates)
		for {
			var res kinesisResponse
			if err = conn.ReadJSON(&res); err != nil {
				// Amazon servers sometimes send malformed messages, skip them
				if errors.Is(err, io.ErrUnexpectedEOF) {
					continue
				}
				break
			}

			log.Trace().Msgf("[webrtc] kinesis recv: %s", res)

			switch res.Type {
			case "SDP_ANSWER":
				// Received SDP answer from server
				var sd pion.SessionDescription
				if err = json.Unmarshal(res.Payload, &sd); err != nil {
					break
				}

				// Set answer (no further negotiation)
				if err = prod.SetAnswer(sd.SDP); err != nil {
					break
				}

			case "ICE_CANDIDATE":
				// Received ICE candidate from server
				var ci pion.ICECandidateInit
				if err = json.Unmarshal(res.Payload, &ci); err != nil {
					break
				}

				// Add candidate (allows ICE probing)
				if err = prod.AddCandidate(ci.Candidate); err != nil {
					break
				}
			}
		}

		// Signal connection state (success or error)
		connState.Done(err)
	}()

	// Wait for connection to establish or error
	if err = connState.Wait(); err != nil {
		return nil, err
	}

	return prod, nil
}

// wyzeKVS is the response from Wyze camera API.
// Camera returns signaling server URL and authentication tokens.
type wyzeKVS struct {
	ClientId string          `json:"ClientId"`     // Client ID for Kinesis
	Cam      string          `json:"cam"`          // Camera ID
	Result   string          `json:"result"`       // "ok" or error
	Servers  json.RawMessage `json:"servers"`      // ICE servers (base64 JSON)
	URL      string          `json:"signalingUrl"` // Kinesis signaling server URL
}

// wyzeClient establishes WebRTC connection to Wyze camera.
// Wyze cameras don't expose WebRTC directly; instead they:
// 1. Return Kinesis signaling server URL
// 2. Return authentication tokens
// 3. Use standard Kinesis WebRTC protocol for actual connection
//
// Args:
//
//	rawURL: HTTP URL to Wyze camera KVS endpoint
//
// Returns:
//
//	core.Producer: Established WebRTC connection to camera
//	error: Camera API failed or signaling error
func wyzeClient(rawURL string) (core.Producer, error) {
	// Step 1: Query Wyze camera for Kinesis signaling server info
	client := http.Client{Timeout: 5 * time.Second}
	res, err := client.Get(rawURL)
	if err != nil {
		return nil, err
	}

	// Step 2: Parse response
	b, err := io.ReadAll(res.Body)
	if err != nil {
		return nil, err
	}

	var kvs wyzeKVS
	if err = json.Unmarshal(b, &kvs); err != nil {
		return nil, err
	}

	// Step 3: Check for API errors
	if kvs.Result != "ok" {
		return nil, errors.New("wyze: wrong result: " + kvs.Result)
	}

	// Step 4: Use Kinesis client with Wyze-specific parameters
	query := url.Values{
		"client_id":   []string{kvs.ClientId},
		"ice_servers": []string{string(kvs.Servers)},
	}

	return kinesisClient(kvs.URL, query, "webrtc/wyze", nil)
}
