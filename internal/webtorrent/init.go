/*
Package webtorrent/init.go initializes WebTorrent peer-to-peer streaming.

WebTorrent allows:
- Decentralized video sharing (no central CDN)
- Browser peers upload to each other
- Magnet links for easy sharing
- Private shares (password protected)

This module:
- Connects to public tracker (OpenWebTorrent by default)
- Manages shares (stream → torrent magnet link)
- Routes API requests for share management
- Integrates with WebRTC for peer connections
*/

package webtorrent

import (
	"errors"
	"fmt"
	"net/http"
	"net/url"

	"github.com/AlexxIT/go2rtc/internal/api"
	"github.com/AlexxIT/go2rtc/internal/app"
	"github.com/AlexxIT/go2rtc/internal/streams"
	"github.com/AlexxIT/go2rtc/internal/webrtc"
	"github.com/AlexxIT/go2rtc/pkg/core"
	"github.com/AlexxIT/go2rtc/pkg/webtorrent"
	"github.com/rs/zerolog"
)

// Init initializes WebTorrent module.
// Loads configuration, starts tracker, sets up HTTP handlers.
func Init() {
	// Load configuration from go2rtc.yaml
	var cfg struct {
		Mod struct {
			Trackers []string `yaml:"trackers"` // WebTorrent tracker URLs
			Shares   map[string]struct {
				Pwd string `yaml:"pwd"` // Share password
				Src string `yaml:"src"` // Source stream name
			} `yaml:"shares"` // Pre-configured shares
		} `yaml:"webtorrent"`
	}

	// Default tracker: OpenWebTorrent (public)
	cfg.Mod.Trackers = []string{"wss://tracker.openwebtorrent.com"}

	// Load actual configuration
	app.LoadConfig(&cfg)

	// Skip initialization if no trackers configured
	if len(cfg.Mod.Trackers) == 0 {
		return
	}

	log = app.GetLogger("webtorrent")

	// Register stream handler: webtorrent:?share=xyz&pwd=abc
	streams.HandleFunc("webtorrent", streamHandle)

	// Register API handler: GET/POST/DELETE /api/webtorrent
	api.HandleFunc("api/webtorrent", apiHandle)

	// Create WebTorrent server connected to first tracker
	srv = &webtorrent.Server{
		URL: cfg.Mod.Trackers[0],

		// Exchange callback: convert stream SDP to WebRTC answer
		Exchange: func(src, offer string) (answer string, err error) {
			stream := streams.Get(src)
			if stream == nil {
				return "", errors.New(api.StreamNotFound)
			}
			// Use WebRTC SDP exchange (same as WHEP)
			return webrtc.ExchangeSDP(stream, offer, "webtorrent", "")
		},
	}

	// Enable detailed logging if debug enabled
	if log.Debug().Enabled() {
		srv.Listen(func(msg any) {
			switch msg.(type) {
			case string, error:
				log.Debug().Msgf("[webtorrent] %s", msg)
			case *webtorrent.Message:
				log.Trace().Any("msg", msg).Msgf("[webtorrent]")
			}
		})
	}

	// Register pre-configured shares from config
	for name, share := range cfg.Mod.Shares {
		// Validate name (min 8 chars)
		if len(name) < 8 {
			log.Warn().Str("name", name).Msgf("min share name len - 8 symbols")
			continue
		}
		// Validate password (min 4 chars)
		if len(share.Pwd) < 4 {
			log.Warn().Str("name", name).Str("pwd", share.Pwd).Msgf("min share pwd len - 4 symbols")
			continue
		}
		// Validate source stream exists
		if streams.Get(share.Src) == nil {
			log.Warn().Str("stream", share.Src).Msgf("stream not exists")
			continue
		}

		// Register share with WebTorrent server
		srv.AddShare(name, share.Pwd, share.Src)

		// Add to global shares registry (for GET /api/webtorrent)
		shares[name] = name
	}
}

var log zerolog.Logger

var shares = map[string]string{}
var srv *webtorrent.Server

// apiHandle processes WebTorrent API requests.
// GET: List shares or get share info
// POST: Create new share
// DELETE: Remove share
//
// Args:
//
//	w: HTTP response writer
//	r: HTTP request
func apiHandle(w http.ResponseWriter, r *http.Request) {
	src := r.URL.Query().Get("src")
	share, ok := shares[src]

	switch r.Method {
	case "GET":
		// Check if WebSocket upgrade request (act as tracker)
		if r.Header.Get("Connection") == "Upgrade" {
			// Route to tracker implementation (for testing)
			tracker(w, r)
			return
		}

		if src != "" {
			// Response: Get info for specific share
			if ok {
				pwd := srv.GetSharePwd(share)
				data := fmt.Sprintf(`{"share":%q,"pwd":%q}`, share, pwd)
				_, _ = w.Write([]byte(data))
			} else {
				http.Error(w, "", http.StatusNotFound)
			}
		} else {
			// Response: List all shares
			var items []*api.Source
			for src, share := range shares {
				pwd := srv.GetSharePwd(share)
				// Generate magnet-like URL with share ID and password
				source := fmt.Sprintf("webtorrent:?share=%s&pwd=%s", share, pwd)
				items = append(items, &api.Source{ID: src, URL: source})
			}
			api.ResponseSources(w, items)
		}

	case "POST":
		// Create new share

		// Check if share already exists
		if ok {
			http.Error(w, "", http.StatusBadRequest)
			return
		}

		// Check if source stream exists
		if stream := streams.Get(src); stream == nil {
			http.Error(w, "", http.StatusNotFound)
			return
		}

		// Generate random share ID and password
		share = core.RandString(10, 62)
		pwd := core.RandString(10, 62)
		srv.AddShare(share, pwd, src)

		// Register in global shares
		shares[src] = share

		w.WriteHeader(http.StatusCreated)
		data := fmt.Sprintf(`{"share":%q,"pwd":%q}`, share, pwd)
		api.Response(w, data, api.MimeJSON)

	case "DELETE":
		// Delete share

		if ok {
			srv.RemoveShare(share)
			delete(shares, src)
		} else {
			http.Error(w, "", http.StatusNotFound)
		}
	}
}

// streamHandle creates WebTorrent client connection.
// Connects to peer network and gets stream.
//
// URL format: webtorrent:?share=xyz&pwd=abc
//
// Args:
//
//	rawURL: WebTorrent URL
//
// Returns:
//
//	core.Producer: Connected WebTorrent stream
//	error: Invalid URL or connection error
func streamHandle(rawURL string) (core.Producer, error) {
	u, err := url.Parse(rawURL)
	if err != nil {
		return nil, err
	}

	query := u.Query()
	share := query.Get("share")
	pwd := query.Get("pwd")

	// Validate parameters
	if len(share) < 8 || len(pwd) < 4 {
		return nil, errors.New("wrong URL: " + rawURL)
	}

	// Create PeerConnection for WebRTC to peer
	pc, err := webrtc.PeerConnection(true)
	if err != nil {
		return nil, err
	}

	// Create WebTorrent client and connect to network
	return webtorrent.NewClient(srv.URL, share, pwd, pc)
}
