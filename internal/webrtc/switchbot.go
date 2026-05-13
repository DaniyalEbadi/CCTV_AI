/*
Package webrtc/switchbot.go implements WebRTC client for SwitchBot smart devices.

SwitchBot provides smart locks, hubs, and cameras via WebRTC.
Uses Kinesis-based signaling (AWS backend) but with SwitchBot-specific parameters.

Connection flow: Same as Kinesis but with SwitchBot-specific SDP offer.
*/

package webrtc

import (
	"net/url"

	"github.com/AlexxIT/go2rtc/pkg/core"
	"github.com/AlexxIT/go2rtc/pkg/webrtc"
)

// switchbotClient establishes WebRTC connection to SwitchBot device.
// Uses Kinesis signaling with SwitchBot-specific parameters.
//
// SwitchBot-specific offer parameters:
//   - resolution: 0 (HD), 1 (SD), 2 (auto)
//   - play_type: Stream type selection
//
// Args:
//
//	rawURL: Kinesis WebSocket URL
//	query: URL query parameters including resolution and play_type
//
// Returns:
//
//	core.Producer: Established WebRTC connection to SwitchBot device
//	error: Connection or signaling failed
func switchbotClient(rawURL string, query url.Values) (core.Producer, error) {
	// Use Kinesis client with SwitchBot-specific offer generator
	return kinesisClient(
		rawURL,
		query,
		"webrtc/switchbot",
		func(prod *webrtc.Conn, query url.Values) (any, error) {
			// Generate SwitchBot-specific SDP offer
			medias := []*core.Media{
				{Kind: core.KindVideo, Direction: core.DirectionRecvonly},
			}

			offer, err := prod.CreateOffer(medias)
			if err != nil {
				return nil, err
			}

			// Build SwitchBot offer format
			v := struct {
				Type       string `json:"type"`       // "offer"
				SDP        string `json:"sdp"`        // SDP string
				Resolution int    `json:"resolution"` // 0=HD, 1=SD, 2=auto
				PlayType   int    `json:"play_type"`  // Stream type
			}{
				Type: "offer",
				SDP:  offer,
			}

			// Parse resolution parameter
			switch query.Get("resolution") {
			case "hd":
				v.Resolution = 0
			case "sd":
				v.Resolution = 1
			case "auto":
				v.Resolution = 2
			}

			// Parse play type (default = 0)
			v.PlayType = core.Atoi(query.Get("play_type"))

			return v, nil
		},
	)
}
