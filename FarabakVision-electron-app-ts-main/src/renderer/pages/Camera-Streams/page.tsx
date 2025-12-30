import { useEffect, useRef, useState } from "react";
import { API_BASE } from "@renderer/constants/config";
import { playWebRTC } from "@renderer/lib/go2rtc";

type Camera = {
  id: string;
  name: string;
  rtsp_url: string;
};

const CameraStreamsPage = () => {
  const [cameras, setCameras] = useState<Camera[]>([]);
  const playersRef = useRef<Record<string, { stop: () => void }>>({});
  const videoRefs = useRef<Record<string, HTMLVideoElement | null>>({});

  useEffect(() => {
    fetch(`${API_BASE}/cameras`)
      .then((r) => r.json())
      .then((data) => setCameras(data.cameras || []))
      .catch(() => setCameras([]));
    return () => {
      Object.values(playersRef.current).forEach((p) => p.stop());
    };
  }, []);

  const start = async (camId: string) => {
    const video = videoRefs.current[camId];
    if (!video) return;
    try {
      const player = await playWebRTC(video, camId);
      playersRef.current[camId] = player;
    } catch (e) {
      console.error(e);
    }
  };

  const stop = (camId: string) => {
    const player = playersRef.current[camId];
    if (player) {
      player.stop();
      delete playersRef.current[camId];
    }
  };

  return (
    <div className="p-4 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {cameras.map((cam) => (
        <div key={cam.id} className="bg-white/5 border border-white/10 rounded-lg p-3">
          <div className="flex items-center justify-between mb-2">
            <div className="font-medium">{cam.name}</div>
            <div className="space-x-2">
              <button
                className="px-2 py-1 bg-green-600 hover:bg-green-700 rounded text-sm"
                onClick={() => start(cam.id)}
              >
                Play
              </button>
              <button
                className="px-2 py-1 bg-red-600 hover:bg-red-700 rounded text-sm"
                onClick={() => stop(cam.id)}
              >
                Stop
              </button>
            </div>
          </div>
          <video
            className="w-full h-60 bg-black rounded"
            ref={(el) => (videoRefs.current[cam.id] = el)}
            muted
            playsInline
            autoPlay
          />
        </div>
      ))}
      {cameras.length === 0 && (
        <div className="text-sm opacity-80">No cameras found. Ensure go2rtc is running and configured.</div>
      )}
    </div>
  );
};

export default CameraStreamsPage;
