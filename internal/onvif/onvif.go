/*
Package onvif implements ONVIF protocol support.

ONVIF (Open Network Video Interface Forum) is an industry standard for:
- IP camera management
- Media configuration
- PTZ (pan/tilt/zoom) control
- Event/alarm handling

This module:
- Implements ONVIF server (responds to client requests)
- Provides ONVIF client (discovers cameras)
- Converts ONVIF profiles to streams
- Handles camera autodiscovery via WS-Discovery
*/

package onvif

import (
	"io"
	"net"
	"net/http"
	"net/url"
	"os"
	"strconv"
	"time"

	"github.com/AlexxIT/go2rtc/internal/api"
	"github.com/AlexxIT/go2rtc/internal/app"
	"github.com/AlexxIT/go2rtc/internal/rtsp"
	"github.com/AlexxIT/go2rtc/internal/streams"
	"github.com/AlexxIT/go2rtc/pkg/core"
	"github.com/AlexxIT/go2rtc/pkg/onvif"
	"github.com/rs/zerolog"
)

// Init initializes ONVIF module.
// Sets up client/server handlers and autodiscovery.
func Init() {
	log = app.GetLogger("onvif")

	// Register ONVIF stream handler: onvif://user:pass@host
	streams.HandleFunc("onvif", streamOnvif)

	// Register ONVIF server: handles all /onvif/* requests
	api.HandleFunc("/onvif/", onvifDeviceService)

	// Register ONVIF discovery API: GET /api/onvif
	api.HandleFunc("api/onvif", apiOnvif)
}

var log zerolog.Logger

// streamOnvif creates ONVIF client connection to camera.
// Queries camera for available streams and returns producer.
//
// Args:
//
//	rawURL: ONVIF URL (onvif://user:pass@host)
//
// Returns:
//
//	core.Producer: RTSP stream from camera
//	error: ONVIF query or RTSP connection error
func streamOnvif(rawURL string) (core.Producer, error) {
	// Create ONVIF client
	client, err := onvif.NewClient(rawURL)
	if err != nil {
		return nil, err
	}

	// Query camera for stream URI
	uri, err := client.GetURI()
	if err != nil {
		return nil, err
	}

	log.Debug().Msgf("[onvif] new uri=%s", uri)

	// Validate URI is valid stream format
	if err = streams.Validate(uri); err != nil {
		return nil, err
	}

	// Get producer for the stream (typically RTSP)
	return streams.GetProducer(uri)
}

// onvifDeviceService implements ONVIF server.
// Responds to ONVIF SOAP requests from clients (typically Home Assistant).
//
// Args:
//
//	w: HTTP response writer
//	r: HTTP request with ONVIF SOAP body
func onvifDeviceService(w http.ResponseWriter, r *http.Request) {
	// Read request body (SOAP XML)
	b, err := io.ReadAll(r.Body)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	// Parse ONVIF operation from request
	operation := onvif.GetRequestAction(b)
	if operation == "" {
		http.Error(w, "malformed request body", http.StatusBadRequest)
		return
	}

	log.Trace().Msgf("[onvif] server request %s %s:\n%s", r.Method, r.RequestURI, b)

	// Route request to handler based on operation
	switch operation {
	// ============================================
	// Device Info (required by Home Assistant)
	// ============================================
	case onvif.DeviceGetNetworkInterfaces,
		onvif.DeviceGetSystemDateAndTime, // Critical for Hass
		onvif.DeviceGetDiscoveryMode,
		onvif.DeviceGetDNS,
		onvif.DeviceGetHostname,
		onvif.DeviceGetNetworkDefaultGateway,
		onvif.DeviceGetNetworkProtocols,
		onvif.DeviceGetNTP,
		onvif.DeviceGetScopes,
		onvif.MediaGetVideoEncoderConfigurations,
		onvif.MediaGetAudioEncoderConfigurations,
		onvif.MediaGetAudioSources,
		onvif.MediaGetAudioSourceConfigurations:
		// Return static response
		b = onvif.StaticResponse(operation)

	case onvif.DeviceGetCapabilities:
		// Return capabilities (Media section important for Hass)
		b = onvif.GetCapabilitiesResponse(r.Host)

	case onvif.DeviceGetServices:
		// List available services
		b = onvif.GetServicesResponse(r.Host)

	case onvif.DeviceGetDeviceInformation:
		// Device info (SerialNumber = unique server ID for Hass)
		b = onvif.GetDeviceInformationResponse("", "go2rtc", app.Version, r.Host)

	case onvif.ServiceGetServiceCapabilities:
		// Media service capabilities (important for Hass)
		b = onvif.GetMediaServiceCapabilitiesResponse()

	case onvif.DeviceSystemReboot:
		// Reboot server
		b = onvif.StaticResponse(operation)

		// Exit process after 1 second
		time.AfterFunc(time.Second, func() {
			os.Exit(0)
		})

	case onvif.MediaGetVideoSources:
		// List video sources (all streams in go2rtc)
		b = onvif.GetVideoSourcesResponse(streams.GetAllNames())

	case onvif.MediaGetProfiles:
		// Get stream profiles (required by Hass for H264 codec, width, height)
		b = onvif.GetProfilesResponse(streams.GetAllNames())

	case onvif.MediaGetProfile:
		// Get specific profile details
		token := onvif.FindTagValue(b, "ProfileToken")
		b = onvif.GetProfileResponse(token)

	case onvif.MediaGetVideoSourceConfigurations:
		// Video source configurations (important for Happytime Onvif Client)
		b = onvif.GetVideoSourceConfigurationsResponse(streams.GetAllNames())

	case onvif.MediaGetVideoSourceConfiguration:
		// Get specific video source configuration
		token := onvif.FindTagValue(b, "ConfigurationToken")
		b = onvif.GetVideoSourceConfigurationResponse(token)

	case onvif.MediaGetStreamUri:
		// Get RTSP stream URI
		// Parse request for profile token
		host, _, err := net.SplitHostPort(r.Host)
		if err != nil {
			http.Error(w, err.Error(), http.StatusInternalServerError)
			return
		}

		// Build RTSP URI: rtsp://host:port/stream_name
		uri := "rtsp://" + host + ":" + rtsp.Port + "/" + onvif.FindTagValue(b, "ProfileToken")
		b = onvif.GetStreamUriResponse(uri)

	case onvif.MediaGetSnapshotUri:
		// Get snapshot (JPEG) URI
		uri := "http://" + r.Host + "/api/frame.jpeg?src=" + onvif.FindTagValue(b, "ProfileToken")
		b = onvif.GetSnapshotUriResponse(uri)

	default:
		http.Error(w, "unsupported operation", http.StatusBadRequest)
		log.Warn().Msgf("[onvif] unsupported operation: %s", operation)
		log.Debug().Msgf("[onvif] unsupported request:\n%s", b)
		return
	}

	log.Trace().Msgf("[onvif] server response:\n%s", b)

	// Send SOAP response
	w.Header().Set("Content-Type", "application/soap+xml; charset=utf-8")
	if _, err = w.Write(b); err != nil {
		log.Error().Err(err).Caller().Send()
	}
}

// apiOnvif handles ONVIF discovery API.
// GET /api/onvif - List discovered ONVIF cameras
// GET /api/onvif?src=onvif://... - Get profiles for specific camera
//
// Args:
//
//	w: HTTP response writer
//	r: HTTP request
func apiOnvif(w http.ResponseWriter, r *http.Request) {
	src := r.URL.Query().Get("src")

	var items []*api.Source

	if src == "" {
		// Discovery: scan network for ONVIF cameras
		urls, err := onvif.DiscoveryStreamingURLs()
		if err != nil {
			http.Error(w, err.Error(), http.StatusInternalServerError)
			return
		}

		// Parse discovered cameras
		for _, rawURL := range urls {
			u, err := url.Parse(rawURL)
			if err != nil {
				log.Warn().Str("url", rawURL).Msg("[onvif] broken")
				continue
			}

			// Only support HTTP (convert to ONVIF)
			if u.Scheme != "http" {
				log.Warn().Str("url", rawURL).Msg("[onvif] unsupported")
				continue
			}

			u.Scheme = "onvif"
			u.User = url.UserPassword("user", "pass")

			// Remove path if it's the default device path
			if u.Path == onvif.PathDevice {
				u.Path = ""
			}

			items = append(items, &api.Source{Name: u.Host, URL: u.String()})
		}
	} else {
		// Get profiles for specific camera
		client, err := onvif.NewClient(src)
		if err != nil {
			http.Error(w, err.Error(), http.StatusInternalServerError)
			return
		}

		// Log profiles for debugging
		if l := log.Trace(); l.Enabled() {
			b, _ := client.MediaRequest(onvif.MediaGetProfiles)
			l.Msgf("[onvif] src=%s profiles:\n%s", src, b)
		}

		// Get camera name
		name, err := client.GetName()
		if err != nil {
			http.Error(w, err.Error(), http.StatusInternalServerError)
			return
		}

		// Get available stream profiles
		tokens, err := client.GetProfilesTokens()
		if err != nil {
			http.Error(w, err.Error(), http.StatusInternalServerError)
			return
		}

		// Return each profile as separate stream
		for i, token := range tokens {
			items = append(items, &api.Source{
				Name: name + " stream" + strconv.Itoa(i),
				URL:  src + "?subtype=" + token,
			})
		}

		// Add snapshot if available
		if len(tokens) > 0 && client.HasSnapshots() {
			items = append(items, &api.Source{
				Name: name + " snapshot",
				URL:  src + "?subtype=" + tokens[0] + "&snapshot",
			})
		}
	}

	api.ResponseSources(w, items)
}
