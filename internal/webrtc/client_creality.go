/*
Package webrtc/client_creality.go implements WebRTC client for Creality 3D printers.

Creality cameras (used in Creality 3D printers, Ender, CR-10, etc.) expose a proprietary
WebRTC API that:
1. Requires SDP offer encoded as base64 JSON
2. Returns SDP answer as base64 JSON
3. Uses non-standard SDP format with extra attributes that break Pion parsing

This file handles:
1. Encoding offer to base64 JSON for Creality
2. Decoding answer from base64 JSON
3. Fixing malformed SDP (removing x-google attributes that break Pion)
4. Creating valid WebRTC connection via standard Pion API

Reference: https://github.com/AlexxIT/go2rtc/issues/1600
*/

package webrtc

import (
	"encoding/base64"
	"encoding/json"
	"io"
	"net/http"
	"strings"
	"time"

	"github.com/AlexxIT/go2rtc/pkg/core"
	"github.com/AlexxIT/go2rtc/pkg/webrtc"
	"github.com/pion/sdp/v3"
)

// crealityClient establishes WebRTC connection with Creality 3D printer.
//
// Steps:
// 1. Create PeerConnection (client-mode, initiates connection)
// 2. Generate SDP offer with video stream request
// 3. Encode offer as base64-wrapped JSON
// 4. POST to camera HTTP endpoint
// 5. Receive and decode base64 JSON response
// 6. Fix malformed SDP (remove x-google attributes)
// 7. Set answer and establish connection
//
// Args:
//
//	url: HTTP endpoint of Creality camera (e.g., http://192.168.1.100:5000/api/webrtc)
//
// Returns:
//
//	core.Producer: WebRTC producer that streams video from camera
//	error: Connection failed or malformed response
func crealityClient(url string) (core.Producer, error) {
	// Step 1: Create PeerConnection in client mode (we initiate the connection)
	pc, err := PeerConnection(true)
	if err != nil {
		return nil, err
	}

	// Create wrapper for PeerConnection (handles Pion library)
	prod := webrtc.NewConn(pc)
	prod.FormatName = "webrtc/creality"
	prod.Mode = core.ModeActiveProducer // We're active initiator
	prod.Protocol = "http"              // Using HTTP for signaling (not WebSocket)
	prod.URL = url

	// Step 2: Generate SDP offer requesting video stream
	medias := []*core.Media{
		{Kind: core.KindVideo, Direction: core.DirectionRecvonly}, // Receive video from camera
	}

	offer, err := prod.CreateCompleteOffer(medias)
	if err != nil {
		return nil, err
	}

	log.Trace().Msgf("[webrtc] offer:\n%s", offer)

	// Step 3: Encode offer as base64 JSON (Creality proprietary format)
	body, err := offerToB64(offer)
	if err != nil {
		return nil, err
	}

	// Step 4: POST encoded offer to camera
	req, err := http.NewRequest("POST", url, body)
	if err != nil {
		return nil, err
	}
	req.Header.Set("Content-Type", "plain/text")

	client := http.Client{Timeout: 5 * time.Second}
	defer client.CloseIdleConnections()

	res, err := client.Do(req)
	if err != nil {
		return nil, err
	}

	// Step 5: Receive and decode base64 JSON response
	answer, err := answerFromB64(res.Body)
	if err != nil {
		return nil, err
	}

	log.Trace().Msgf("[webrtc] answer:\n%s", answer)

	// Step 6: Fix malformed SDP (remove x-google attributes that break Pion)
	if answer, err = fixCrealitySDP(answer); err != nil {
		return nil, err
	}

	// Step 7: Set answer and establish connection
	if err = prod.SetAnswer(answer); err != nil {
		return nil, err
	}

	return prod, nil
}

// offerToB64 converts SDP offer to base64-encoded JSON.
// Creality cameras expect offers in this format:
//
//	base64("{"type":"offer","sdp":"v=0\r\n..."}")
//
// Args:
//
//	sdp: SDP offer string from Pion
//
// Returns:
//
//	io.Reader: Base64-encoded JSON ready to send in HTTP body
//	error: JSON marshal or encode failed
func offerToB64(sdp string) (io.Reader, error) {
	// Create JavaScript object format
	v := map[string]string{
		"type": "offer",
		"sdp":  sdp,
	}

	// Convert to JSON bytes
	b, err := json.Marshal(v)
	if err != nil {
		return nil, err
	}

	// Encode as base64 (why Creality does this is unclear, but they do)
	s := base64.StdEncoding.EncodeToString(b)

	return strings.NewReader(s), nil
}

// answerFromB64 decodes base64-encoded JSON response from camera.
// Reverses offerToB64() process:
//
//	base64-string -> JSON -> extract "sdp" field -> SDP
//
// Args:
//
//	r: HTTP response body containing base64-encoded JSON
//
// Returns:
//
//	string: SDP answer ready for Pion SetAnswer()
//	error: Invalid base64, JSON, or missing "sdp" field
func answerFromB64(r io.Reader) (string, error) {
	// Read response body as base64 string
	b, err := io.ReadAll(r)
	if err != nil {
		return "", err
	}

	// Decode from base64 to JSON bytes
	if b, err = base64.StdEncoding.DecodeString(string(b)); err != nil {
		return "", err
	}

	// Parse JSON to extract "sdp" field
	var v map[string]string
	if err = json.Unmarshal(b, &v); err != nil {
		return "", err
	}

	// Extract and return SDP string
	return v["sdp"], nil
}

// fixCrealitySDP removes attributes that break Pion's SDP parser.
// Creality cameras include:
// - Multiple "fmtp" lines for the same codec
// - "x-google-max-bitrate", "x-google-min-bitrate" (Google-specific, not standard)
// These cause Pion to fail parsing
//
// Solution:
// 1. Parse SDP using Pion's SDP parser
// 2. Remove codec entries for first codec format (seems to be dummy)
// 3. Strip all fmtp lines with first codec or x-google attributes
// 4. Re-serialize SDP
//
// Args:
//
//	value: Malformed SDP from Creality
//
// Returns:
//
//	string: Fixed SDP compatible with Pion
//	error: SDP parse/marshal failed
func fixCrealitySDP(value string) (string, error) {
	// Parse SDP to struct
	var sd sdp.SessionDescription
	if err := sd.UnmarshalString(value); err != nil {
		return "", err
	}

	md := sd.MediaDescriptions[0]

	// Skip first codec format (seems to be a dummy format in Creality SDP)
	// This is a workaround for Creality's non-standard SDP generation
	skip := md.MediaName.Formats[0]
	md.MediaName.Formats = md.MediaName.Formats[1:]

	// Filter attributes to remove problematic ones
	attrs := make([]sdp.Attribute, 0, len(md.Attributes))
	for _, attr := range md.Attributes {
		switch attr.Key {
		case "fmtp", "rtpmap":
			// Remove fmtp for the skipped codec OR any x-google attributes
			// x-google attributes are Google-specific extensions that Pion doesn't recognize
			if strings.HasPrefix(attr.Value, skip) || strings.Contains(attr.Value, "x-google") {
				continue
			}
		}
		attrs = append(attrs, attr)
	}

	md.Attributes = attrs

	// Re-serialize fixed SDP
	b, err := sd.Marshal()
	if err != nil {
		return "", err
	}
	return string(b), nil
}
