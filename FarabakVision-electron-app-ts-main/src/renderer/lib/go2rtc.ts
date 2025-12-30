import { API_BASE } from "@renderer/constants/config";

export async function playWebRTC(video: HTMLVideoElement, stream: string) {
  const pc = new RTCPeerConnection();
  pc.addTransceiver("video", { direction: "recvonly" });
  pc.addTransceiver("audio", { direction: "recvonly" });

  pc.ontrack = (ev) => {
    const [stream] = ev.streams;
    if (stream) {
      video.srcObject = stream;
      video.play().catch((e) => console.debug(e));
    }
  };

  const base = API_BASE.replace(/\/$/, "");
  const wsBase = base.replace("http://", "ws://").replace("https://", "wss://");
  const ws = new WebSocket(`${wsBase}/webrtc/ws?src=${encodeURIComponent(stream)}`);

  await new Promise<void>((resolve, reject) => {
    ws.onopen = () => resolve();
    ws.onerror = () => reject(new Error("WebSocket connection failed"));
  });

  const offer = await pc.createOffer();
  await pc.setLocalDescription(offer);

  ws.send(JSON.stringify({ type: "webrtc/offer", value: offer.sdp }));

  await new Promise<void>((resolve, reject) => {
    ws.onmessage = async (ev) => {
      try {
        const msg = JSON.parse(ev.data);
        if (msg.type === "webrtc/answer" && typeof msg.value === "string") {
          const answer = { type: "answer", sdp: msg.value } as RTCSessionDescriptionInit;
          await pc.setRemoteDescription(answer);
          resolve();
        }
      } catch {
        reject(new Error("Invalid WebRTC answer"));
      }
    };
    ws.onerror = () => reject(new Error("WebSocket error during signaling"));
  });

  return {
    stop: () => {
      try {
        ws.close();
        pc.close();
        if (video.srcObject) {
          const ms = video.srcObject as MediaStream;
          ms.getTracks().forEach((t) => t.stop());
        }
        video.srcObject = null;
      } catch (e) {
        void e;
      }
    },
  };
}
