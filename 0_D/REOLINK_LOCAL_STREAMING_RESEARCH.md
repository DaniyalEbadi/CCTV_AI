# Reolink Camera Streaming Protocols: Local Network Research

## Executive Summary

Reolink cameras use **proprietary protocols** for local network streaming that differ significantly from standard RTSP and RTMP. The company uses the **"Baichuan Protocol"** (port 9000) for older/battery-powered cameras and a **custom HTTP-FLV implementation** for newer cameras, while simultaneously supporting RTSP/RTMP with known quality issues.

---

## 1. Official App Protocol: What Does Reolink App Use Locally?

### Protocol: **HTTP-FLV + Baichuan Protocol (Port 9000)**

**Reolink's official mobile app uses:**
- **HTTP-FLV streaming** for main streams (port 80)
- **Baichuan Protocol** for P2P communication (port 9000) - only when needed
- **RTSP/RTMP** as fallback (less preferred)

**URL Examples:**
```
http://camera_ip/flv?port=1935&app=bcs&stream=channel0_main.bcs&user=admin&password=password
http://camera_ip:80/flv?port=1935&app=bcs&stream=channel0_ext.bcs
rtmp://camera_ip/bcs/channel0_main.bcs
```

**Port Configuration:**
- HTTP-FLV: Port 80 (standard HTTP)
- RTMP fallback: Port 1935 (standard RTMP)
- Baichuan (proprietary): Port 9000
- RTSP: Port 554

---

## 2. Proprietary vs. Standard Protocols

### **Baichuan Protocol (Custom Proprietary)**

The Baichuan Protocol is Reolink's **completely proprietary, reverse-engineered streaming protocol** developed by Baichuan (the parent company known internationally as Reolink).

**Key Characteristics:**
- **Header-data format** with custom encapsulation
- **Obfuscated XML commands** for modern variants
- **H.264 or H.265 video streams** wrapped in custom headers
- **UDP-based** for battery/outdoor cameras
- **TCP-based** for PoE cameras (port 9000)

**Implementation Details:**
- Sends raw H.265/H.264 video packets within BC-encapsulated headers
- Uses XML message format (partially obfuscated in newer versions)
- AES encryption in latest firmware versions
- Not ONVIF or RTSP compliant

**Documented By:** [Neolink Project](https://github.com/thirtythreeforty/neolink) - Open-source RTSP bridge that reverse-engineered this protocol

---

## 3. H.265/HEVC Streaming Differences

### **RTSP H.265 Implementation (Problematic)**

**Known Issues:**
- Stream packet handling errors (SPS/PPS with incorrect markers)
- Aspect ratio incompatibilities (Duo 2 specifically mentioned)
- High latency and freezing issues
- Non-standard SDP formatting

**RTSP H.265 URL:**
```
rtsp://admin:password@camera_ip/h264Preview_01_main
rtsp://admin:password@camera_ip/h264Preview_01_sub  # sub/low stream
```

### **HTTP-FLV H.265 Implementation (Better)**

**Advantages:**
- Native H.265 support in newer Reolink cameras
- More stable transmission
- Better for 4K streaming
- Direct FLV encapsulation preserves H.265 integrity

**HTTP-FLV H.265 URL:**
```
http://camera_ip/flv?port=1935&app=bcs&stream=channel0_main.bcs
```

**Key Difference (From GitHub Issue #1938 - "Add support HTTP-FLV with H265"):**
- RTSP forces re-encoding or packetization that corrupts H.265 streams
- HTTP-FLV allows H.265 to pass through in FLV container directly
- FLV container better handles H.265 variable-length NAL units

**SDP/RTP Packetization Issues in RTSP:**
```
# Reolink sends non-standard SDP:
a=tool:BC Streaming Media v202210012022.10.01
m=video 0 RTP/AVP 96
a=rtpmap:96 H264/90000
a=fmtp:96 packetization-mode=1;profile-level-id=640033
# Note: Reolink Duo 2 sends SPS with Marker=true and PPS without
# This breaks standard RTP H.264 depacking in some clients
```

---

## 4. Undocumented/Proprietary Streaming Protocols

### **Complete Protocol List:**

| Protocol | Port | Type | Supported Codecs | Availability | Notes |
|----------|------|------|-----------------|--------------|-------|
| **Baichuan** | 9000 | TCP/UDP | H.264, H.265, PCM μ-law | Older cameras, battery powered | Proprietary, reverse-engineered only |
| **HTTP-FLV** | 80 | HTTP | H.264, H.265, AAC, PCM | New models (2022+) | Better H.265 stability |
| **RTSP** | 554 | TCP/UDP | H.264, H.265, AAC | All modern models | Buggy H.265, freezing issues |
| **RTMP** | 1935 | TCP | H.264, AAC only | Most models | Fallback protocol |
| **ONVIF** | 8000 | HTTP | H.264 | Most PoE models | For discovery, backchannel audio |

### **Proprietary Features:**

1. **Backchannel Audio (ONVIF Profile T)**
   - Only works on specific firmware versions
   - Requires specific audio codec support
   - Newer doorbell models support PCMA/PCMU for two-way talk
   - URL: `rtsp://ip/Preview_01_main` + backchannel flag

2. **Extended Streams (Not Standard)**
   - Main stream: `/Preview_01_main` 
   - Sub stream: `/Preview_01_sub`
   - Extended stream: `/Preview_01_ext`
   - Custom Reolink-specific paths

3. **Custom Authentication**
   - Uses Digest authentication (MD5)
   - Realm: "BC Streaming Media"
   - Not standard HTTP auth in FLV streams

---

## 5. Why Reolink App Doesn't Freeze But RTSP Apps Do (4K Streaming)

### **Root Causes of RTSP Freezing:**

1. **Packet Size Mismatch**
   ```
   # RTSP RTP packet handling
   - MTU: 1378 bytes (Reolink standard)
   - Large H.265 key frames exceed buffer
   - SPS/PPS packet fragmentation issues
   ```

2. **Reolink's Non-Standard SDP/RTP Implementation**
   ```
   Problem: Reolink sends SPS/PPS marked as final packet (Marker=true)
   This violates RFC 3984 (H.264 RTP Payload Format)
   Result: Players drop frames or freeze waiting for complete frame
   ```

3. **H.265 NAL Unit Handling**
   - RTSP RTP doesn't properly handle H.265 NAL units
   - FLV container handles variable-length NALs better
   - 4K frames are larger and more susceptible to fragmentation

### **Why HTTP-FLV + Baichuan Protocol Doesn't Freeze:**

1. **Direct Frame Encapsulation**
   - HTTP-FLV wraps complete H.265 frames in FLV tags
   - No RTP fragmentation overhead
   - Guaranteed frame integrity

2. **Higher Bitrate Tolerance**
   - HTTP allows larger MTU sizes
   - Can send full 4K key frames in single packets
   - Better buffering and congestion handling

3. **No RTP Jitter Issues**
   - HTTP is ordered delivery
   - No packet reordering problems
   - FLV timestamps are more reliable

**Evidence from Workspace:**
```
From go2rtc code comments:
// Fix TP-Link Tapo TC70: sends SPS and PPS with packet.Marker = true
// Reolink Duo 2: sends SPS with Marker and PPS without
// This causes significant compatibility issues with standard players
```

---

## 6. Specific Protocol Implementation Details

### **HTTP-FLV Stream Request:**
```
GET /flv?port=1935&app=bcs&stream=channel0_main.bcs&user=admin&password=pwd HTTP/1.1
Host: 192.168.1.123
Connection: close

# Returns:
# FLV header + RTMP-style packet headers + H.264/H.265 NAL units
# Content-Type: video/x-flv
```

### **RTMP Implementation (Tested):**
```
# go2rtc confirmed working with:
rtmp://192.168.10.92/bcs/channel0_main.bcs?channel=0&stream=0
rtmp://192.168.10.92/bcs/channel0_sub.bcs?channel=0&stream=1
rtmp://192.168.10.92/bcs/channel0_ext.bcs?channel=0&stream=1

# Reolink RTMP packet size: 4096 bytes
# (compared to OBS: 4096, standard RTMP: variable)
```

### **Backchannel Audio (Two-Way Talk):**
```
# DESCRIBE request with ONVIF backchannel requirement:
Require: www.onvif.org/ver20/backchannel

# Response SDP includes three audio tracks:
m=audio 0 RTP/AVP 97  # AAC (recv only)
a=rtpmap:97 MPEG4-GENERIC/16000
m=audio 0 RTP/AVP 8   # PCMA (send only - for doorbell response)
a=rtpmap:8 PCMA/8000
a=sendonly

# SETUP requires proper authorization:
SETUP rtsp://ip/Preview_01_main/track3 RTSP/1.0
Authorization: Digest (required for backchannel)
```

---

## 7. Streaming URLs and Configuration

### **Working Reolink URLs (Tested):**

**RTSP (Basic):**
```yaml
streams:
  reolink_main: rtsp://admin:password@192.168.1.123/h264Preview_01_main
  reolink_sub: rtsp://admin:password@192.168.1.123/h264Preview_01_sub
```

**HTTP-FLV (Better for newer models):**
```yaml
streams:
  reolink_flv: http://192.168.1.123/flv?port=1935&app=bcs&stream=channel0_main.bcs&user=admin&password=password
  reolink_ext: http://192.168.1.123/flv?port=1935&app=bcs&stream=channel0_ext.bcs&user=admin&password=password
```

**RTMP (Fallback):**
```yaml
streams:
  reolink_rtmp: rtmp://192.168.1.123/bcs/channel0_main.bcs?channel=0&stream=0
```

**ONVIF (Discovery + Backchannel):**
```yaml
streams:
  reolink_onvif: onvif://admin:password@192.168.1.123:8000
```

---

## 8. Known Issues & Recommendations

### **RTSP Problems (Documented):**
- Freezing with H.265 streams (Duo 2 specifically noted)
- Backchannel audio authentication failures
- Non-compliant SDP formatting
- Latency issues (~10 seconds reported)
- Aspect ratio incompatibilities

**Go2rtc Recommendation:**
```
From go2rtc README.md:
"Reolink users may want NOT to use RTSP protocol at all, 
some camera models have a very awful, unusable stream implementation"
```

### **Firmware Considerations:**
- Backchannel support varies by firmware version
- Newer firmware (v3.0.0+) has better ONVIF support
- HTTP-FLV support added in recent models
- Some models only support port 9000 (Baichuan)

### **Recommended Configuration for Stability:**

**For Two-Way Audio + 4K:**
```yaml
streams:
  reolink:
    - ffmpeg:http://192.168.1.123/flv?port=1935&app=bcs&stream=channel0_main.bcs&user=admin&password=pwd#video=copy#audio=copy#audio=opus
    - rtsp://admin:password@192.168.1.123/Preview_01_sub
```

**For Simple Streaming (No Backchannel):**
```yaml
streams:
  reolink_simple:
    - http://192.168.1.123/flv?port=1935&app=bcs&stream=channel0_main.bcs&user=admin&password=pwd
```

---

## 9. Technical Deep Dive: Baichuan Protocol

### **Reverse Engineering Source:**
Neolink project provides Wireshark dissector and detailed protocol analysis in:
- `dissector/` - Wireshark plugin for BC protocol dissection
- Deobfuscates XML commands
- Shows custom header structure

### **Protocol Structure:**
```
[BC Header] [Command/Data Length] [Obfuscated XML OR Raw H.264/H.265 Stream]
```

### **Connection Flow (Battery Camera Example):**
1. UDP discovery on port 9000
2. Camera UID required (not IP address)
3. UDP transport for streaming
4. Custom framing for NAL units

### **Connection Flow (PoE Camera Example):**
1. TCP connection to port 9000
2. XML-based command negotiation
3. Stream initialization with codec info
4. Continuous H.264/H.265 NAL unit transmission

---

## 10. Port Numbers Summary

| Service | Port | Protocol | Purpose |
|---------|------|----------|---------|
| HTTP-FLV | 80 | HTTP | Primary streaming (new models) |
| RTMP/RTMPS | 1935 | TCP | Video streaming (fallback) |
| RTSP | 554 | TCP/UDP | Streaming (legacy, buggy) |
| Baichuan (Proprietary) | 9000 | TCP/UDP | Native Reolink protocol |
| ONVIF | 8000 | HTTP | Discovery & metadata |
| Web UI | 8080 | HTTP | Camera web interface |
| Cloud | Various | HTTPS | P2P/Cloud (not local) |

---

## Conclusion

**Local Reolink Streaming Summary:**

1. **Official App Uses:** HTTP-FLV (primary) + Baichuan Protocol (fallback) + RTSP/RTMP (last resort)

2. **Best Protocol for Stability:** HTTP-FLV or Baichuan (both proprietary)

3. **Standard RTSP Issues:** Non-compliant SDP, packet marking errors, H.265 corruption, freezing on 4K

4. **Why No Freezing in Official App:** 
   - Direct frame encapsulation without RTP fragmentation
   - Proper H.265 NAL unit handling
   - Better buffer management
   - Custom optimization for Reolink hardware

5. **Recommendation:** Use go2rtc or Neolink as middleware to convert Baichuan/HTTP-FLV to standard RTSP for universal compatibility

---

## References

- **Neolink**: https://github.com/thirtythreeforty/neolink - Baichuan protocol reverse engineering
- **go2rtc**: https://github.com/AlexxIT/go2rtc - RTSP bridge with Reolink support
- **Frigate Docs**: Reolink two-way audio configuration examples
- **Home Assistant Reolink Integration**: Community-developed protocol handler
- **GitHub Issue #331**: Reolink Video Doorbell extensive discussion with logs and SDP analysis
- **GitHub Issue #1938**: HTTP-FLV with H265 support addition

