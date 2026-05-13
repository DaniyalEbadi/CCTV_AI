/*
Package webtorrent/tracker.go implements a WebTorrent tracker.

WebTorrent is a peer-to-peer protocol for live video streaming:
- Multiple peers share video streams
- Decentralized (no central server)
- Works over WebSocket (browser-compatible)
- Reduces server bandwidth (peers upload to each other)

This tracker:
- Maintains peer registry (who has what torrent)
- Routes offers between peers
- Exchanges SDP answers for WebRTC connections
- Implements announce protocol

Typical flow:
1. Peer A joins torrent "xyz" and sends offer
2. Tracker sends peer A's offer to peer B
3. Peer B responds with answer
4. Peer B's answer sent back to peer A
5. Peers establish WebRTC connection directly
6. Video streams peer-to-peer
*/

package webtorrent

import (
	"fmt"
	"net/http"

	"github.com/AlexxIT/go2rtc/pkg/webtorrent"
	"github.com/gorilla/websocket"
)

var upgrader *websocket.Upgrader
var hashes map[string]map[string]*websocket.Conn

// tracker handles WebSocket tracker protocol.
// Manages peer registry and message routing.
//
// Args:
//
//	w: HTTP response writer
//	r: HTTP request (will be upgraded to WebSocket)
func tracker(w http.ResponseWriter, r *http.Request) {
	// Lazy initialization: create upgrader on first request
	if upgrader == nil {
		upgrader = &websocket.Upgrader{
			ReadBufferSize:  1024,
			WriteBufferSize: 2028,
		}
		// Allow all origins (permissive for testing)
		upgrader.CheckOrigin = func(r *http.Request) bool {
			return true
		}
	}

	// Upgrade HTTP connection to WebSocket
	ws, err := upgrader.Upgrade(w, r, nil)
	if err != nil {
		log.Warn().Err(err).Send()
		return
	}

	defer ws.Close()

	// Message loop: read messages from peer
	for {
		var msg webtorrent.Message
		if err = ws.ReadJSON(&msg); err != nil {
			return
		}

		//log.Trace().Msgf("[webtorrent] message=%v", msg)

		// Validate message fields
		if msg.InfoHash == "" || msg.PeerId == "" {
			continue
		}

		// Lazy initialization: create peer registry
		if hashes == nil {
			hashes = map[string]map[string]*websocket.Conn{}
		}

		// Get or create peer list for this torrent
		clients := hashes[msg.InfoHash]
		if clients == nil {
			clients = map[string]*websocket.Conn{
				msg.PeerId: ws,
			}
			hashes[msg.InfoHash] = clients
		} else {
			// Update or add peer to existing torrent
			clients[msg.PeerId] = ws
		}

		// Route message based on type
		switch {
		case msg.Offers != nil:
			// Peer is sending offers (wants to stream)

			// Send announce response (keep-alive)
			raw := fmt.Sprintf(
				`{"action":"announce","interval":120,"info_hash":"%s","complete":0,"incomplete":1}`,
				msg.InfoHash,
			)
			if err = ws.WriteMessage(websocket.TextMessage, []byte(raw)); err != nil {
				log.Warn().Err(err).Send()
				return
			}

			// Skip if no offers (server/receiver mode)
			if len(msg.Offers) == 0 {
				continue
			}

			// Get first offer (use only one offer per message)
			offer := msg.Offers[0]
			if offer.OfferId == "" || offer.Offer.Type != "offer" || offer.Offer.SDP == "" {
				continue
			}

			// Broadcast offer to all other peers in this torrent
			raw = fmt.Sprintf(
				`{"action":"announce","info_hash":"%s","peer_id":"%s","offer_id":"%s","offer":{"type":"offer","sdp":"%s"}}`,
				msg.InfoHash, msg.PeerId, offer.OfferId, offer.Offer.SDP,
			)

			for _, server := range clients {
				// Don't send offer back to originator
				if server != ws {
					_ = server.WriteMessage(websocket.TextMessage, []byte(raw))
				}
			}

		case msg.OfferId != "" && msg.ToPeerId != "" && msg.Answer != nil:
			// Peer is sending answer to specific peer

			ws1, ok := clients[msg.ToPeerId]
			if !ok {
				// Recipient not found (left)
				continue
			}

			// Send answer only to recipient
			raw := fmt.Sprintf(
				`{"action":"announce","info_hash":"%s","peer_id":"%s","offer_id":"%s","answer":{"type":"answer","sdp":"%s"}}`,
				msg.InfoHash, msg.PeerId, msg.OfferId, msg.Answer.SDP,
			)
			_ = ws1.WriteMessage(websocket.TextMessage, []byte(raw))
		}
	}
}
