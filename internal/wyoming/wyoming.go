/*
Package wyoming implements Wyoming protocol support for voice AI.

Wyoming is an open protocol for voice AI systems, used by:
- Rhasspy (open-source voice assistant)
- Home Assistant (voice handling)
- Wyoming Hub (voice processing server)

Features:
- Audio I/O (microphone input, speaker output)
- Wake word detection
- Voice activity detection (VAD)
- Speech-to-text / text-to-speech

This integration allows:
- Stream audio FROM cameras TO Wyoming services
- Stream audio FROM Wyoming services back TO cameras
- Process voice commands in real-time
*/

package wyoming

import (
	"net"

	"github.com/AlexxIT/go2rtc/internal/app"
	"github.com/AlexxIT/go2rtc/internal/streams"
	"github.com/AlexxIT/go2rtc/pkg/core"
	"github.com/AlexxIT/go2rtc/pkg/wyoming"
	"github.com/rs/zerolog"
)

// Init initializes the Wyoming module.
// Sets up client connections and server listeners.
func Init() {
	// Register Wyoming as a stream handler
	// Allows: wyoming:tcp://localhost:10700
	streams.HandleFunc("wyoming", wyoming.Dial)

	// Load configuration from go2rtc.yaml
	var cfg struct {
		Mod map[string]struct {
			Listen       string            `yaml:"listen"`        // TCP listen address (e.g., :10700)
			Name         string            `yaml:"name"`          // Instance name (for logging)
			Mode         string            `yaml:"mode"`          // "mic", "snd", or "dual" (default)
			Event        map[string]string `yaml:"event"`         // Event routing configuration
			WakeURI      string            `yaml:"wake_uri"`      // Wake word detector URI
			VADThreshold float32           `yaml:"vad_threshold"` // Voice activity detection threshold (0-1)
		} `yaml:"wyoming"`
	}
	app.LoadConfig(&cfg)

	log = app.GetLogger("wyoming")

	// Start Wyoming servers for each configured instance
	for name, cfg := range cfg.Mod {
		// Get stream associated with this Wyoming instance
		stream := streams.Get(name)
		if stream == nil {
			log.Warn().Msgf("[wyoming] missing stream: %s", name)
			continue
		}

		// Use config name or fall back to stream name
		if cfg.Name == "" {
			cfg.Name = name
		}

		// Create Wyoming server instance
		srv := &wyoming.Server{
			Name:         cfg.Name,
			Event:        cfg.Event,
			VADThreshold: int16(1000 * cfg.VADThreshold), // Convert 0.0-1.0 to 0-1000
			WakeURI:      cfg.WakeURI,

			// Handle incoming microphone audio (from client)
			MicHandler: func(cons core.Consumer) error {
				if err := stream.AddConsumer(cons); err != nil {
					return err
				}
				// Cleanup when client disconnects
				if i, ok := cons.(interface{ OnClose(func()) }); ok {
					i.OnClose(func() {
						stream.RemoveConsumer(cons)
					})
				}
				return nil
			},

			// Handle outgoing speaker audio (to client)
			SndHandler: func(prod core.Producer) error {
				return stream.Play(prod)
			},

			// Logging callbacks
			Trace: func(format string, v ...any) {
				log.Trace().Msgf("[wyoming] "+format, v...)
			},
			Error: func(format string, v ...any) {
				log.Error().Msgf("[wyoming] "+format, v...)
			},
		}

		// Start server in background
		go serve(srv, cfg.Mode, cfg.Listen)
	}
}

var log zerolog.Logger

// serve runs a Wyoming server listening on address.
// Accepts incoming client connections and handles them.
//
// Args:
//
//	srv: Wyoming server instance
//	mode: "mic" (input only), "snd" (output only), or "" (bidirectional)
//	address: TCP listen address (e.g., :10700)
func serve(srv *wyoming.Server, mode, address string) {
	// Listen on TCP port
	ln, err := net.Listen("tcp", address)
	if err != nil {
		log.Warn().Err(err).Msgf("[wyoming] listen")
		return
	}

	// Accept connections in loop
	for {
		conn, err := ln.Accept()
		if err != nil {
			return
		}

		// Handle each client in separate goroutine
		go handle(srv, mode, conn)
	}
}

// handle processes a single Wyoming client connection.
//
// Args:
//
//	srv: Wyoming server instance
//	mode: "mic", "snd", or "" (default = bidirectional)
//	conn: TCP connection from client
func handle(srv *wyoming.Server, mode string, conn net.Conn) {
	addr := conn.RemoteAddr()

	log.Trace().Msgf("[wyoming] %s connected", addr)

	// Route based on mode
	switch mode {
	case "mic":
		// Microphone only: client sends audio
		srv.HandleMic(conn)
	case "snd":
		// Speaker only: server sends audio
		srv.HandleSnd(conn)
	default:
		// Bidirectional: full protocol
		srv.Handle(conn)
	}

	log.Trace().Msgf("[wyoming] %s disconnected", addr)
}
