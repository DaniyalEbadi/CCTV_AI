/*
Package webrtc/server.go implements WebRTC server for incoming connections.

Supports multiple signaling protocols:
1. WHEP (WebRTC-HTTP Egress Protocol) - Standard, simple
2. WHIP (WebRTC-HTTP Ingestion Protocol) - Upload video from clients
3. Custom JSON protocol - go2rtc-specific extensions
4. Raw SDP exchange - Minimal, for interop

Use cases:
- WHEP: Browser client downloads stream from server
- WHIP: Browser uploads stream (webcam, desktop) to server
- DELETE: Tear down session (WHEP/WHIP)
- PATCH: Update session (future WHEP extensions)

Internals:
- sessions map: Track active WHEP/WHIP connections by session ID
- Lazy SessionDescription creation: Build SDP on-demand per request
*/

package webrtc

import (
	"encoding/base64"
	"encoding/json"
	"io"
	"net/http"
	"strconv"
	"strings"
	"time"

	"github.com/AlexxIT/go2rtc/internal/api"
	"github.com/AlexxIT/go2rtc/internal/streams"
	"github.com/AlexxIT/go2rtc/pkg/core"
	"github.com/AlexxIT/go2rtc/pkg/webrtc"
	pion "github.com/pion/webrtc/v4"
)

// MimeSDP is the IANA MIME type for SDP content.
const MimeSDP = "application/sdp"

// sessions tracks active WHEP/WHIP connections.
// Key: session ID (generated at creation), Value: PeerConnection wrapper
var sessions = map[string]*webrtc.Conn{}

// syncHandler processes HTTP requests for WebRTC signaling.
// Supports WHEP (egress), WHIP (ingress), and PATCH/DELETE for session management.
//
// Endpoints:
//
//	POST /api/webrtc?src=camera1    -> WHEP (download from camera)
//	POST /api/webrtc?dst=stream1    -> WHIP (upload to stream)
//	DELETE /api/webrtc?id=session   -> Tear down session
//	PATCH /api/webrtc?id=session    -> Update session (future)
//	OPTIONS /api/webrtc             -> CORS preflight
//
// HTTP Methods:
//
//	POST: Create new session (WHEP/WHIP/JSON/raw SDP)
//	PATCH: Update session (future WHEP extensions)
//	DELETE: Delete session
//	OPTIONS: Preflight for CORS
func syncHandler(w http.ResponseWriter, r *http.Request) {
	switch r.Method {
	case "POST":
		// Create new session
		query := r.URL.Query()
		if query.Get("src") != "" {
			// WHEP: Egress (server → client) signaling
			// Client downloads stream from specified source
			outputWebRTC(w, r)
		} else if query.Get("dst") != "" {
			// WHIP: Ingress (client → server) signaling
			// Client uploads stream to specified destination
			inputWebRTC(w, r)
		} else {
			// Invalid request
			http.Error(w, "", http.StatusBadRequest)
		}

	case "PATCH":
		// Update session (WHEP/WHIP extension)
		// Future: support for SDP renegotiation, codec changes, etc.
		http.Error(w, "", http.StatusMethodNotAllowed)

	case "DELETE":
		// Tear down session
		if id := r.URL.Query().Get("id"); id != "" {
			if conn, ok := sessions[id]; ok {
				delete(sessions, id)
				_ = conn.Close() // Gracefully close WebRTC connection
			} else {
				// Session not found
				http.Error(w, "", http.StatusNotFound)
			}
		} else {
			// Missing session ID
			http.Error(w, "", http.StatusBadRequest)
		}

	case "OPTIONS":
		// CORS preflight request
		w.WriteHeader(http.StatusNoContent)

	default:
		http.Error(w, "", http.StatusMethodNotAllowed)
	}
}

// outputWebRTC handles WHEP (Egress) requests.
// Client requests stream from server.
// Supports multiple Content-Type variants:
//  1. application/json: {"type":"offer","sdp":"..."} ↔ {"type":"answer","sdp":"..."}
//  2. application/sdp: Raw SDP ↔ Raw SDP (WHEP standard)
//  3. application/x-www-form-urlencoded: Base64-encoded SDP (legacy)
//  4. other: Raw SDP (generic fallback)
//
// Args:
//
//	w: HTTP response writer
//	r: HTTP request with SDP offer in body
func outputWebRTC(w http.ResponseWriter, r *http.Request) {
	// Get source stream name
	u := r.URL.Query().Get("src")
	stream := streams.Get(u)
	if stream == nil {
		http.Error(w, api.StreamNotFound, http.StatusNotFound)
		return
	}

	// Parse Content-Type header
	mediaType := r.Header.Get("Content-Type")
	if mediaType != "" {
		mediaType, _, _ = strings.Cut(mediaType, ";")
		mediaType = strings.ToLower(strings.TrimSpace(mediaType))
	}

	// Read SDP offer from request body (format depends on Content-Type)
	var offer string

	switch mediaType {
	case "application/json":
		// JSON format: {"type":"offer","sdp":"v=0\r\n..."}
		var desc pion.SessionDescription
		if err := json.NewDecoder(r.Body).Decode(&desc); err != nil {
			log.Error().Err(err).Caller().Send()
			http.Error(w, err.Error(), http.StatusBadRequest)
			return
		}
		offer = desc.SDP

	case "application/x-www-form-urlencoded":
		// Form-encoded: data=<base64-sdp>
		if err := r.ParseForm(); err != nil {
			log.Error().Err(err).Caller().Send()
			http.Error(w, err.Error(), http.StatusBadRequest)
			return
		}
		offerB64 := r.Form.Get("data")
		b, err := base64.StdEncoding.DecodeString(offerB64)
		if err != nil {
			log.Error().Err(err).Caller().Send()
			http.Error(w, err.Error(), http.StatusBadRequest)
			return
		}
		offer = string(b)

	default:
		// Raw SDP (default for application/sdp and others)
		body, err := io.ReadAll(r.Body)
		if err != nil {
			log.Error().Err(err).Caller().Send()
			http.Error(w, err.Error(), http.StatusInternalServerError)
			return
		}
		offer = string(body)
	}

	// Determine description type for logging/filtering
	var desc string
	switch mediaType {
	case "application/json":
		desc = "webrtc/json"
	case MimeSDP:
		desc = "webrtc/whep"
	default:
		desc = "webrtc/post"
	}

	// Exchange SDP with stream
	answer, err := ExchangeSDP(stream, offer, desc, r.UserAgent())
	if err != nil {
		log.Error().Err(err).Caller().Send()
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	// Send answer in requested format
	switch mediaType {
	case "application/json":
		// JSON response: {"type":"answer","sdp":"v=0\r\n..."}
		w.Header().Set("Content-Type", mediaType)

		v := pion.SessionDescription{
			Type: pion.SDPTypeAnswer, SDP: answer,
		}
		err = json.NewEncoder(w).Encode(v)

	case "application/x-www-form-urlencoded":
		// Form-encoded response: data=<base64-sdp>
		w.Header().Set("Content-Type", mediaType)
		answerB64 := base64.StdEncoding.EncodeToString([]byte(answer))
		_, err = w.Write([]byte(answerB64))

	case MimeSDP:
		// WHEP standard response: raw SDP with 201 Created
		w.Header().Set("Content-Type", mediaType)
		w.WriteHeader(http.StatusCreated)
		_, err = w.Write([]byte(answer))

	default:
		// Raw SDP response
		w.Header().Set("Content-Type", mediaType)
		_, err = w.Write([]byte(answer))
	}

	if err != nil {
		log.Error().Err(err).Caller().Send()
		http.Error(w, err.Error(), http.StatusInternalServerError)
	}
}

// inputWebRTC handles WHIP (Ingestion) requests.
// Client uploads stream to server.
// Client sends SDP offer in HTTP request body.
// Server responds with SDP answer.
//
// Args:
//
//	w: HTTP response writer
//	r: HTTP request with SDP offer in body
func inputWebRTC(w http.ResponseWriter, r *http.Request) {
	// Get destination stream name
	dst := r.URL.Query().Get("dst")
	stream := streams.Get(dst)
	if stream == nil {
		http.Error(w, api.StreamNotFound, http.StatusNotFound)
		return
	}

	// Step 1: Read SDP offer from request body
	offer, err := io.ReadAll(r.Body)
	if err != nil {
		log.Error().Err(err).Caller().Send()
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	log.Trace().Msgf("[webrtc] WHIP offer\n%s", offer)

	// Step 2: Create PeerConnection (server mode)
	pc, err := PeerConnection(false)
	if err != nil {
		log.Error().Err(err).Caller().Send()
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	// Step 3: Create connection wrapper (producer)
	prod := webrtc.NewConn(pc)
	prod.Mode = core.ModePassiveProducer // Server-side producer
	prod.Protocol = "http"               // HTTP signaling
	prod.UserAgent = r.UserAgent()

	// Step 4: Exchange SDP
	if err = prod.SetOffer(string(offer)); err != nil {
		log.Warn().Err(err).Caller().Send()
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	answer, err := prod.GetCompleteAnswer(GetCandidates(), FilterCandidate)
	if err != nil {
		log.Warn().Err(err).Caller().Send()
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	log.Trace().Msgf("[webrtc] WHIP answer\n%s", answer)

	// Step 5: Register session for later teardown
	id := strconv.FormatInt(time.Now().UnixNano(), 36)
	sessions[id] = prod

	// Step 6: Register connection state handler
	prod.Listen(func(msg any) {
		switch msg := msg.(type) {
		case pion.PeerConnectionState:
			if msg == pion.PeerConnectionStateClosed {
				// Connection closed, remove from stream and sessions
				stream.RemoveProducer(prod)
				delete(sessions, id)
			}
		}
	})

	// Step 7: Add producer to stream
	stream.AddProducer(prod)

	// Step 8: Send answer response
	w.Header().Set("Content-Type", MimeSDP)
	w.Header().Set("Location", "webrtc?id="+id)
	w.WriteHeader(http.StatusCreated)

	if _, err = w.Write([]byte(answer)); err != nil {
		log.Warn().Err(err).Caller().Send()
		return
	}
}
