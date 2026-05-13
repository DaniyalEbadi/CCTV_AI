When to use FFmpeg in go2rtc:
Camera codec unsupported by client
Need bitrate adaptation
Quality scaling
Audio transcoding
NOT for lowest latency - it adds overhead.


PRACTICAL COMPARISON FOR go2rtc:
Setup 1: Direct RTSP Stream (No FFmpeg)
streams:
  camera: rtsp://192.168.1.100/stream


Setup 2: WebRTC Stream (No FFmpeg)
streams:
  camera: rtsp://192.168.1.100/stream

Latency: 50-300ms | CPU: Minimal | Quality: Camera native | Access: Internet OK



Setup 3: MSE/MP4 Stream (No FFmpeg)
streams:
  camera: rtsp://192.168.1.100/stream

# View via:
# - Browser MSE (all browsers, any network) (2-5s)
Latency: 2-5s | CPU: Minimal | Quality: Camera native | Compatibility: Best



Setup 4: FFmpeg Transcoding (adds latency!)

streams:
  camera:
    - rtsp://192.168.1.100/stream
    - ffmpeg:rtsp://192.168.1.100/stream#video=h264#audio=aac

# View via:
# - Browser WebRTC with FFmpeg source (150-400ms)




SPEED RANKING (Fastest to Slowest):
RTSP (UDP) - 50-200ms ⚡
WebRTC - 50-300ms ⚡
FFmpeg Real-time - 100-300ms (+ encoding overhead)
MSE/MP4 - 2-5 seconds 📺
HLS - 5-10 seconds 📺
HTTP Progressive - 10-30 seconds 📺



QUALITY RANKING (Best Codec Handling):

WebRTC - Native codec support best ⭐⭐⭐
MSE/MP4 - Good codec support ⭐⭐
RTSP - Depends on player ⭐⭐
FFmpeg - Transcodes to any format ⭐⭐⭐⭐
HLS - Limited to TS format ⭐



Best setup:
- Primary: HLS (most stable, 5-10s latency)
- Fallback: MSE/MP4 (more stable than WebRTC)
- Advanced: WebRTC (if network is good)

Why? Because your issue is FREEZING, not speed.
A 5-second HLS stream never freezes.
A 100ms WebRTC stream freezing every 30s is useless.