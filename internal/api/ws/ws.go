package ws

import (
	"encoding/json"
	"io"
	"net/http"
	"net/url"
	"strings"
	"sync"
	"time"

	"github.com/AlexxIT/go2rtc/internal/api"
	"github.com/AlexxIT/go2rtc/internal/app"
	"github.com/AlexxIT/go2rtc/pkg/core"
	"github.com/gorilla/websocket"
	"github.com/rs/zerolog"
)

func Init() {
	var cfg struct {
		Mod struct {
			Origin string `yaml:"origin"`
		} `yaml:"api"`
	}

	app.LoadConfig(&cfg)

	log = app.GetLogger("api")

	initWS(cfg.Mod.Origin)

	api.HandleFunc("api/ws", apiWS)
}

var log zerolog.Logger

// Message - struct for data exchange in Web API
type Message struct {
	Type  string `json:"type"`
	Value any    `json:"value,omitempty"`
}

func (m *Message) String() (value string) {
	if s, ok := m.Value.(string); ok {
		return s
	}
	return
}

func (m *Message) Unmarshal(v any) error {
	b, err := json.Marshal(m.Value)
	if err != nil {
		return err
	}
	return json.Unmarshal(b, v)
}

type WSHandler func(tr *Transport, msg *Message) error

func HandleFunc(msgType string, handler WSHandler) {
	wsHandlers[msgType] = handler
}

var wsHandlers = make(map[string]WSHandler)

func initWS(origin string) {
	wsUp = &websocket.Upgrader{
		ReadBufferSize:  4096,       // for SDP
		WriteBufferSize: 512 * 1024, // 512K
	}

	switch origin {
	case "":
		// same origin + ignore port
		wsUp.CheckOrigin = func(r *http.Request) bool {
			origin := r.Header["Origin"]
			if len(origin) == 0 {
				return true
			}
			o, err := url.Parse(origin[0])
			if err != nil {
				return false
			}
			if o.Host == r.Host {
				return true
			}
			log.Trace().Msgf("[api] ws origin=%s, host=%s", o.Host, r.Host)
			// https://github.com/AlexxIT/go2rtc/issues/118
			if i := strings.IndexByte(o.Host, ':'); i > 0 {
				return o.Host[:i] == r.Host
			}
			return false
		}
	case "*":
		// any origin
		wsUp.CheckOrigin = func(r *http.Request) bool {
			return true
		}
	}
}

const (
	// writeWait is the time allowed to write a message to the peer.
	// Increased from short default to be safe for long-running streams.
	writeWait = 10 * time.Second

	// pongWait is the time allowed to read the next pong message from the peer.
	// Keepalive interval should be smaller than this.
	pongWait = 60 * time.Second

	// pingPeriod is how often server sends pings to peer. Must be < pongWait.
	pingPeriod = 30 * time.Second

	// maxMessageSize limits the size of a single incoming message (json/sdp).
	maxMessageSize = 512 * 1024 // 512KB
)

func apiWS(w http.ResponseWriter, r *http.Request) {
	ws, err := wsUp.Upgrade(w, r, nil)
	if err != nil {
		origin := r.Header.Get("Origin")
		log.Error().Err(err).Caller().Msgf("host=%s origin=%s", r.Host, origin)
		return
	}

	// set limits and handlers for long-running connections
		ws.SetReadLimit(maxMessageSize)
		_ = ws.SetReadDeadline(time.Now().Add(pongWait))
		ws.SetPongHandler(func(string) error {
			_ = ws.SetReadDeadline(time.Now().Add(pongWait))
			return nil
		})
	// optional: log close events
	ws.SetCloseHandler(func(code int, text string) error {
		log.Debug().Int("code", code).Str("text", text).Msg("[api] ws close")
		return nil
	})

	tr := &Transport{Request: r}

	// on write, increase deadline to writeWait (safer for slow networks)
	tr.OnWrite(func(msg any) error {
		_ = ws.SetWriteDeadline(time.Now().Add(writeWait))

		if data, ok := msg.([]byte); ok {
			return ws.WriteMessage(websocket.BinaryMessage, data)
		} else {
			return ws.WriteJSON(msg)
		}
	})

	// stop channel for background goroutines (ping loop)
	stop := make(chan struct{})
	// ensure transport cleanup will stop goroutines
	tr.OnClose(func() {
		close(stop)
	})

	// start ping goroutine to keep NAT mappings alive and detect broken peers
	go func() {
		ticker := time.NewTicker(pingPeriod)
		defer ticker.Stop()
		for {
			select {
			case <-stop:
				return
			case <-ticker.C:
				// send a ping control frame
				_ = ws.SetWriteDeadline(time.Now().Add(writeWait))
				if err := ws.WriteControl(websocket.PingMessage, nil, time.Now().Add(writeWait)); err != nil {
					// if ping fails, close transport which triggers cleanup
					log.Debug().Err(err).Msg("[api] ws ping failed, closing")
					_ = ws.Close()
					tr.Close()
					return
				}
			}
		}
	}()

	// read loop
	for {
		msg := new(Message)
		if err = ws.ReadJSON(msg); err != nil {
			// Non-nil error: handle close/EOF vs other errors
			// treat unexpected close as trace (not noisy)
			if websocket.IsUnexpectedCloseError(err, websocket.CloseNormalClosure, websocket.CloseGoingAway) {
				log.Trace().Err(err).Caller().Msg("[api] ws read unexpected close")
			} else if err == io.EOF {
				log.Trace().Err(err).Caller().Msg("[api] ws read EOF")
			} else if websocket.IsCloseError(err, websocket.CloseNoStatusReceived) {
				// common in browsers, treat as trace
				log.Trace().Err(err).Caller().Msg("[api] ws close no status")
			} else {
				// other errors we still trace for debugging long runs
				log.Trace().Err(err).Caller().Send()
			}
			_ = ws.Close()
			break
		}

		log.Trace().Str("type", msg.Type).Msg("[api] ws msg")

		// dispatch handler in a goroutine; protect msg copy to avoid races
		if handler := wsHandlers[msg.Type]; handler != nil {
			// copy message to avoid aliasing issues
			msgCopy := *msg
			go func(m Message) {
				if err := handler(tr, &m); err != nil {
					errMsg := core.StripUserinfo(err.Error())
					tr.Write(&Message{Type: "error", Value: m.Type + ": " + errMsg})
				}
			}(msgCopy)
		}
	}

	// ensure cleanup handlers are called and background goroutines stop
	tr.Close()
	// close websocket if still open
	_ = ws.Close()
}

var wsUp *websocket.Upgrader

type Transport struct {
	Request *http.Request

	ctx map[any]any

	closed bool
	mx     sync.Mutex
	wrmx   sync.Mutex

	onChange func()
	onWrite  func(msg any) error
	onClose  []func()
}

func (t *Transport) OnWrite(f func(msg any) error) {
	t.mx.Lock()
	if t.onChange != nil {
		t.onChange()
	}
	t.onWrite = f
	t.mx.Unlock()
}

func (t *Transport) Write(msg any) {
	t.wrmx.Lock()
	_ = t.onWrite(msg)
	t.wrmx.Unlock()
}

func (t *Transport) Close() {
	t.mx.Lock()
	for _, f := range t.onClose {
		f()
	}
	t.closed = true
	t.mx.Unlock()
}

func (t *Transport) OnChange(f func()) {
	t.mx.Lock()
	t.onChange = f
	t.mx.Unlock()
}

func (t *Transport) OnClose(f func()) {
	t.mx.Lock()
	if t.closed {
		f()
	} else {
		t.onClose = append(t.onClose, f)
	}
	t.mx.Unlock()
}

// WithContext - run function with Context variable
func (t *Transport) WithContext(f func(ctx map[any]any)) {
	t.mx.Lock()
	if t.ctx == nil {
		t.ctx = map[any]any{}
	}
	f(t.ctx)
	t.mx.Unlock()
}

func (t *Transport) Writer() io.Writer {
	return &writer{t: t}
}

type writer struct {
	t *Transport
}

func (w *writer) Write(p []byte) (n int, err error) {
	w.t.wrmx.Lock()
	if err = w.t.onWrite(p); err == nil {
		n = len(p)
	}
	w.t.wrmx.Unlock()
	return
}
