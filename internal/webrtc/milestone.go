/*
Package webrtc/milestone.go implements WebRTC client for Milestone XProtect VMS.

Milestone XProtect is a professional video management system (VMS) widely used in
enterprise surveillance. It exposes cameras via a REST API with WebRTC support.

Connection flow:
1. Authenticate via OAuth2 (client_credentials grant)
2. Create WebRTC session (returns session ID and SDP offer)
3. Generate SDP answer
4. Send answer back to Milestone
5. Connection established

URL format:
  webrtc:https://milestone-host/api#format=milestone#username=User#password=Pass#cameraId=<uuid>

Reference:
  https://github.com/milestonesys/mipsdk-samples-protocol/tree/main/WebRTC_JavaScript
*/

package webrtc

import (
	"bytes"
	"encoding/json"
	"errors"
	"net/http"
	"net/url"
	"strconv"
	"strings"

	"github.com/AlexxIT/go2rtc/pkg/core"
	"github.com/AlexxIT/go2rtc/pkg/tcp"
	"github.com/AlexxIT/go2rtc/pkg/webrtc"
	pion "github.com/pion/webrtc/v4"
)

// milestoneAPI encapsulates OAuth2 token and session management.
type milestoneAPI struct {
	url       string     // Base URL of Milestone server
	query     url.Values // Query parameters (username, password, cameraId, etc.)
	token     string     // OAuth2 access token
	sessionID string     // Milestone WebRTC session ID
}

// GetToken authenticates with Milestone server using OAuth2.
// Uses client_credentials grant with username/password (Resource Owner Password Credentials).
//
// Endpoint: /IDP/connect/token
// Request: client_id=GrantValidatorClient&grant_type=password&username=...&password=...
// Response: {"access_token":"...", ...}
//
// Args: (receiver) m *milestoneAPI with url and query set
//
// Returns:
//
//	error: HTTP error, invalid response, or missing token
func (m *milestoneAPI) GetToken() error {
	// Build OAuth2 request body (application/x-www-form-urlencoded)
	data := url.Values{
		"client_id":  {"GrantValidatorClient"}, // Milestone OAuth2 client ID
		"grant_type": {"password"},             // Password grant type
		"username":   m.query["username"],      // Username from URL params
		"password":   m.query["password"],      // Password from URL params
	}

	// Create POST request to token endpoint
	req, err := http.NewRequest(
		"POST",
		m.url+"/IDP/connect/token",
		strings.NewReader(data.Encode()),
	)
	if err != nil {
		return err
	}
	req.Header.Set("Content-Type", "application/x-www-form-urlencoded")

	// Execute request (supports httpx protocol via tcp.Do)
	res, err := tcp.Do(req)
	if err != nil {
		return err
	}
	defer res.Body.Close()

	// Check HTTP status
	if res.StatusCode != http.StatusOK {
		return errors.New("milestone: authentication failed: " + res.Status)
	}

	// Parse response
	var payload map[string]interface{}
	if err = json.NewDecoder(res.Body).Decode(&payload); err != nil {
		return err
	}

	// Extract access token
	token, ok := payload["access_token"].(string)
	if !ok {
		return errors.New("milestone: token not found in response")
	}

	m.token = token
	return nil
}

// parseFloat converts string to float64 (returns 0 on error).
// Used for parsing Milestone query parameters that may be missing.
func parseFloat(s string) float64 {
	if s == "" {
		return 0
	}
	f, _ := strconv.ParseFloat(s, 64)
	return f
}

// GetOffer requests SDP offer from Milestone server.
// The server creates a new WebRTC session and returns the offer.
//
// Endpoint: /REST/v1/WebRTC/Session
// Request: POST with camera ID and optional playback parameters
// Response: {"sessionId":"...", "offerSDP":"..."}
//
// Args: (receiver) m *milestoneAPI with token and query set
//
// Returns:
//
//	string: SDP offer from server
//	error: HTTP error or invalid response
func (m *milestoneAPI) GetOffer() (string, error) {
	// Build WebRTC session request
	request := struct {
		CameraId         string `json:"cameraId"`           // Camera UUID
		StreamId         string `json:"streamId,omitempty"` // Optional stream selection
		PlaybackTimeNode struct {
			PlaybackTime string  `json:"playbackTime,omitempty"` // Timestamp for playback
			SkipGaps     bool    `json:"skipGaps,omitempty"`     // Skip gaps in recording
			Speed        float64 `json:"speed,omitempty"`        // Playback speed (default=1.0)
		} `json:"playbackTimeNode,omitempty"`
	}{
		CameraId: m.query.Get("cameraId"),
		StreamId: m.query.Get("streamId"),
	}

	// Parse optional playback parameters
	request.PlaybackTimeNode.PlaybackTime = m.query.Get("playbackTime")
	request.PlaybackTimeNode.SkipGaps = m.query.Has("skipGaps")
	request.PlaybackTimeNode.Speed = parseFloat(m.query.Get("speed"))

	// Serialize request to JSON
	data, err := json.Marshal(request)
	if err != nil {
		return "", err
	}

	// Create POST request with Bearer token authentication
	req, err := http.NewRequest("POST", m.url+"/REST/v1/WebRTC/Session", bytes.NewBuffer(data))
	if err != nil {
		return "", err
	}
	req.Header.Set("Authorization", "Bearer "+m.token)
	req.Header.Set("Content-Type", "application/json")

	// Execute request
	res, err := tcp.Do(req)
	if err != nil {
		return "", err
	}
	defer res.Body.Close()

	// Check HTTP status
	if res.StatusCode != http.StatusOK {
		return "", errors.New("milestone: create session: " + res.Status)
	}

	// Parse response
	var response struct {
		SessionId string `json:"sessionId"` // Session ID for further operations
		OfferSDP  string `json:"offerSDP"`  // SDP offer (JSON string)
	}
	if err = json.NewDecoder(res.Body).Decode(&response); err != nil {
		return "", err
	}

	// Parse SDP offer (it's JSON-encoded in the response)
	var offer pion.SessionDescription
	if err = json.Unmarshal([]byte(response.OfferSDP), &offer); err != nil {
		return "", err
	}

	// Save session ID for later use (when sending answer)
	m.sessionID = response.SessionId

	return offer.SDP, nil
}

// SetAnswer sends SDP answer back to Milestone server.
// The server uses this to complete the WebRTC handshake.
//
// Endpoint: /REST/v1/WebRTC/Session/{sessionId}
// Request: PATCH with SDP answer
// Response: HTTP 200 OK (on success)
//
// Args:
//
//	sdp: SDP answer string from Pion
//
// Returns:
//
//	error: HTTP error or invalid response
func (m *milestoneAPI) SetAnswer(sdp string) error {
	// Wrap answer in SessionDescription format
	answer := pion.SessionDescription{
		Type: pion.SDPTypeAnswer,
		SDP:  sdp,
	}

	// Serialize to JSON
	data, err := json.Marshal(answer)
	if err != nil {
		return err
	}

	// Create PATCH request body
	request := struct {
		AnswerSDP string `json:"answerSDP"`
	}{
		AnswerSDP: string(data),
	}

	// Serialize request
	if data, err = json.Marshal(request); err != nil {
		return err
	}

	// Create PATCH request to update session with answer
	req, err := http.NewRequest(
		"PATCH",
		m.url+"/REST/v1/WebRTC/Session/"+m.sessionID,
		bytes.NewBuffer(data),
	)
	if err != nil {
		return err
	}
	req.Header.Set("Authorization", "Bearer "+m.token)
	req.Header.Set("Content-Type", "application/json")

	// Execute request
	res, err := tcp.Do(req)
	if err != nil {
		return err
	}
	defer res.Body.Close()

	// Check HTTP status
	if res.StatusCode != http.StatusOK {
		return errors.New("milestone: patch session: " + res.Status)
	}

	return nil
}

// milestoneClient establishes WebRTC connection to Milestone XProtect camera.
//
// Full connection flow:
// 1. Authenticate (OAuth2) to get access token
// 2. Create WebRTC session (get offer from server)
// 3. Create PeerConnection and set offer
// 4. Generate SDP answer
// 5. Send answer back to Milestone
// 6. Connection established (no trickle ICE)
//
// Args:
//
//	rawURL: HTTPS URL to Milestone server
//	        (e.g., https://milestone-host/api)
//	query: URL query parameters
//	       - username: Milestone username
//	       - password: Milestone password
//	       - cameraId: Camera UUID
//	       - streamId: (optional) Stream selection
//	       - playbackTime: (optional) For recording playback
//	       - speed: (optional) Playback speed
//
// Returns:
//
//	core.Producer: Established WebRTC connection to camera
//	error: Authentication, session creation, or signaling failed
func milestoneClient(rawURL string, query url.Values) (core.Producer, error) {
	// Initialize Milestone API wrapper
	mc := &milestoneAPI{url: rawURL, query: query}

	// Step 1: Authenticate and get OAuth2 token
	if err := mc.GetToken(); err != nil {
		return nil, err
	}

	// Step 2: Create PeerConnection
	api, err := webrtc.NewAPI()
	if err != nil {
		return nil, err
	}

	conf := pion.Configuration{} // No special ICE servers needed
	pc, err := api.NewPeerConnection(conf)
	if err != nil {
		return nil, err
	}

	// Create connection wrapper
	prod := webrtc.NewConn(pc)
	prod.FormatName = "webrtc/milestone"
	prod.Mode = core.ModeActiveProducer // We're initiator
	prod.Protocol = "http"              // HTTP signaling
	prod.URL = rawURL

	// Step 3: Get SDP offer from Milestone
	offer, err := mc.GetOffer()
	if err != nil {
		return nil, err
	}

	// Step 4: Set offer and create answer
	if err = prod.SetOffer(offer); err != nil {
		return nil, err
	}

	answer, err := prod.GetAnswer()
	if err != nil {
		return nil, err
	}

	// Step 5: Send answer back to Milestone
	if err = mc.SetAnswer(answer); err != nil {
		return nil, err
	}

	return prod, nil
}
