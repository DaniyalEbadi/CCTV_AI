/*
Package webrtc/openipc.go implements WebRTC client for OpenIPC cameras.

OpenIPC is an open-source firmware for IP cameras, supporting various chipsets.
Uses WebSocket for WebRTC signaling with JSON message format.

Connection flow:
1. Connect WebSocket to camera
2. Load ICE servers from query params
3. Create PeerConnection
4. Generate SDP offer
5. Send offer via WebSocket
6. Receive answer via WebSocket
7. Exchange ICE candidates (trickle ICE)
8. Connection established

URL format:
  webrtc:wss://camera-host:9000/webrtc#format=openipc

Reference:
  https://openipc.org/
*/

package webrtc

import (
	"encoding/json"
	"errors"
	"io"
	"net/url"

	"github.com/AlexxIT/go2rtc/pkg/core"
	"github.com/AlexxIT/go2rtc/pkg/webrtc"
	"github.com/gorilla/websocket"
	pion "github.com/pion/webrtc/v4"
)

// openIPCClient establishes WebRTC connection to OpenIPC camera.
//
// WebSocket message flow:
// 1. Client sends: {"req":"webrtc_offer","data":"<base64-sdp>"}
// 2. Server responds: {"reply":"webrtc_answer","data":"<sdp-json>"}
// 3. Client/Server exchange: {"req"/"reply":"webrtc_candidate","data":"<candidate>"}
//
// Args:
//
//	rawURL: WebSocket URL to OpenIPC camera
//	        (e.g., wss://camera.local:9000/webrtc)
//	query: URL query parameters
//	       - ice_servers: Base64-encoded JSON with ICE server list
//
// Returns:
//
//	core.Producer: Established WebRTC connection to camera
//	error: WebSocket connection, signaling, or SDP error
func openIPCClient(rawURL string, query url.Values) (core.Producer, error) {
	// Step 1: Connect to OpenIPC WebSocket signaling
	conn, _, err := websocket.DefaultDialer.Dial(rawURL, nil)
	if err != nil {
		return nil, err
	}

	// Step 2: Load ICE servers from query params
	conf := pion.Configuration{}

	if s := query.Get("ice_servers"); s != "" {
		// Decode base64-encoded JSON with ICE server list
		conf.ICEServers, err = webrtc.UnmarshalICEServers([]byte(s))
		if err != nil {
			log.Warn().Err(err).Caller().Send()
		}
	}

	// Close WebSocket when exiting (on error or after getting producer)
	defer conn.Close()

	// Step 3: Create PeerConnection with OpenIPC config
	api, err := webrtc.NewAPI()
	if err != nil {
		return nil, err
	}

	pc, err := api.NewPeerConnection(conf)
	if err != nil {
		return nil, err
	}

	// Synchronization: buffer ICE candidates that arrive before offer is sent
	var sendAnswer core.Waiter

	// Synchronization: wait for connection to establish or error
	var connState core.Waiter

	// Create connection wrapper
	prod := webrtc.NewConn(pc)
	prod.FormatName = "webrtc/openipc"
	prod.Mode = core.ModeActiveProducer // We're active initiator
	prod.Protocol = "ws"                // WebSocket signaling
	prod.URL = rawURL

	// Listen to connection events
	prod.Listen(func(msg any) {
		switch msg := msg.(type) {
		case *pion.ICECandidate:
			// Wait for answer before sending candidates
			_ = sendAnswer.Wait()

			// Send ICE candidate
			req := openIPCReq{
				Data: msg.ToJSON().Candidate,
				Req:  "candidate",
			}
			if err = conn.WriteJSON(&req); err != nil {
				connState.Done(err)
				return
			}

			log.Trace().Msgf("[webrtc] openipc send: %s", req)

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

	// Step 4: Generate SDP offer
	medias := []*core.Media{
		{Kind: core.KindVideo, Direction: core.DirectionRecvonly},
		{Kind: core.KindAudio, Direction: core.DirectionRecvonly},
	}

	offer, err := prod.CreateOffer(medias)
	if err != nil {
		return nil, err
	}

	// Step 5: Send offer wrapped in OpenIPC message format
	req := openIPCReq{
		Data: offer,
		Req:  "webrtc_offer",
	}
	if err = conn.WriteJSON(&req); err != nil {
		return nil, err
	}

	log.Trace().Msgf("[webrtc] openipc send: %s", req)

	// Step 6-7: Receive answer and exchange ICE candidates
	go func() {
		var err error

		// Loop: receive messages from camera
		for err == nil {
			var rep openIPCReply
			if err = conn.ReadJSON(&rep); err != nil {
				// Handle unexpected EOF (some buggy cameras)
				if errors.Is(err, io.ErrUnexpectedEOF) {
					continue
				}
				break
			}

			log.Trace().Msgf("[webrtc] openipc recv: %s", rep)

			switch rep.Reply {
			case "webrtc_answer":
				// Received SDP answer from camera
				var sd pion.SessionDescription
				if err = json.Unmarshal(rep.Data, &sd); err != nil {
					break
				}

				// Set answer from camera
				if err = prod.SetOffer(sd.SDP); err != nil {
					break
				}

				// Generate our answer
				var answer string
				if answer, err = prod.GetAnswer(); err != nil {
					break
				}

				// Send our answer back
				req := openIPCReq{Data: answer, Req: "answer"}
				if err = conn.WriteJSON(req); err != nil {
					break
				}

				log.Trace().Msgf("[webrtc] openipc send: %s", req)

				// Signal that answer has been sent (candidates can now be sent)
				sendAnswer.Done(nil)

			case "webrtc_candidate":
				// Received ICE candidate from camera
				var ci pion.ICECandidateInit
				if err = json.Unmarshal(rep.Data, &ci); err != nil {
					break
				}

				// Add candidate to enable ICE connection
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

// openIPCReply is the message format received from OpenIPC camera.
type openIPCReply struct {
	Data  json.RawMessage `json:"data"`  // JSON-encoded SDP or ICE candidate
	Reply string          `json:"reply"` // "webrtc_answer" or "webrtc_candidate"
}

// String returns a human-readable representation.
func (r openIPCReply) String() string {
	b, _ := json.Marshal(r)
	return string(b)
}

// openIPCReq is the message format sent to OpenIPC camera.
type openIPCReq struct {
	Data string `json:"data"` // SDP or ICE candidate string
	Req  string `json:"req"`  // "webrtc_offer", "answer", "candidate"
}

// String returns a human-readable representation.
func (r openIPCReq) String() string {
	b, _ := json.Marshal(r)
	return string(b)
}
