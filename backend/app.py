import asyncio
import json
import os
import time
import shutil
from typing import Dict, List

import httpx
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import base64
from websockets.client import connect as ws_connect

from .models import Camera, CamerasResponse, Event, EventsResponse
from .events.aggregator import EventAggregator
from .ai.processor import AIProcessor
from .recording.recorder import RecorderManager
from .media.event_media import save_snapshot, save_event_clip


class Settings(BaseModel):
    go2rtc_api_url: str = "http://127.0.0.1:1984"
    go2rtc_rtsp_url: str = "rtsp://127.0.0.1:8554"
    fps_limit: int = 5
    resolution: str = "640x360"
    ai_backend: str = "auto"
    event_clip_seconds: int = 15
    snapshot_dir: str = "storage/snapshots"
    clips_dir: str = "storage/clips"
    api_login: str | None = None
    api_password: str | None = None


def load_settings() -> Settings:
    return Settings(
        go2rtc_api_url=os.environ.get("GO2RTC_API", "http://127.0.0.1:1984"),
        go2rtc_rtsp_url=os.environ.get("GO2RTC_RTSP", "rtsp://127.0.0.1:8554"),
        fps_limit=int(os.environ.get("AI_FPS", "5")),
        resolution=os.environ.get("AI_RESOLUTION", "640x360"),
        ai_backend=os.environ.get("AI_BACKEND", "auto"),
        event_clip_seconds=int(os.environ.get("EVENT_CLIP_SECONDS", "15")),
        snapshot_dir=os.environ.get("SNAPSHOT_DIR", "storage/snapshots"),
        clips_dir=os.environ.get("CLIPS_DIR", "storage/clips"),
        api_login=os.environ.get("GO2RTC_API_LOGIN") or None,
        api_password=os.environ.get("GO2RTC_API_PASSWORD") or None,
    )


app = FastAPI(title="Farabak Vision Backend", version="1.0.0")
settings = load_settings()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class Connections:
    def __init__(self) -> None:
        self._clients: List[WebSocket] = []

    async def add(self, ws: WebSocket) -> None:
        await ws.accept()
        self._clients.append(ws)

    def remove(self, ws: WebSocket) -> None:
        if ws in self._clients:
            self._clients.remove(ws)

    async def broadcast(self, message: dict) -> None:
        data = json.dumps(message)
        for ws in list(self._clients):
            try:
                await ws.send_text(data)
            except Exception:
                self.remove(ws)


connections = Connections()
events_buffer: List[Event] = []
cameras_cache: List[Camera] = []
aggregator = EventAggregator()
recorder = RecorderManager()
processors: Dict[str, AIProcessor] = {}


async def fetch_cameras_from_go2rtc() -> List[Camera]:
    api = settings.go2rtc_api_url.rstrip("/")
    try:
        auth = None
        if settings.api_login and settings.api_password:
            auth = (settings.api_login, settings.api_password)
        async with httpx.AsyncClient(timeout=5, auth=auth) as client:
            r = await client.get(f"{api}/api/streams")
            data = r.json()
            cams: List[Camera] = []
            for name in data.keys():
                cams.append(
                    Camera(
                        id=name,
                        name=name,
                        rtsp_url=f"{settings.go2rtc_rtsp_url.rstrip('/')}/{name}",
                    )
                )
            return cams
    except Exception:
        return []


@app.on_event("startup")
async def on_startup():
    os.makedirs(settings.snapshot_dir, exist_ok=True)
    os.makedirs(settings.clips_dir, exist_ok=True)
    cams = await fetch_cameras_from_go2rtc()
    global cameras_cache
    cameras_cache = cams
    loop = asyncio.get_event_loop()
    has_ffmpeg = shutil.which("ffmpeg") is not None
    if has_ffmpeg:
        for cam in cameras_cache:
            recorder.start(cam)
            proc = AIProcessor(
                cam,
                fps=settings.fps_limit,
                resolution=settings.resolution,
                backend_pref=settings.ai_backend,
                on_detections=lambda dets, ts, frame: asyncio.create_task(handle_detections(cam, dets, ts, frame)),
            )
            processors[cam.id] = proc
            proc.start(loop)


@app.get("/cameras", response_model=CamerasResponse)
async def get_cameras():
    global cameras_cache
    if not cameras_cache:
        cameras_cache = await fetch_cameras_from_go2rtc()
    return CamerasResponse(cameras=cameras_cache)


@app.get("/events", response_model=EventsResponse)
async def get_events():
    return EventsResponse(events=events_buffer[-200:])


@app.websocket("/events/ws")
async def events_ws(ws: WebSocket):
    await connections.add(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        connections.remove(ws)


async def push_event(event: Event) -> None:
    events_buffer.append(event)
    await connections.broadcast({"type": "event", "data": event.dict()})


async def handle_detections(camera: Camera, dets, ts: float, frame):
    events = aggregator.ingest(camera.id, dets, ts)
    for ev in events:
        snap_dir = os.path.join(settings.snapshot_dir, camera.id)
        os.makedirs(snap_dir, exist_ok=True)
        snap_path = os.path.join(snap_dir, f"{int(ts*1000)}.jpg")
        try:
            from .media.event_media import save_snapshot
            save_snapshot(frame, snap_path)
            ev.snapshot_path = snap_path
        except Exception:
            pass
        clip_path = os.path.join(
            settings.clips_dir, camera.id, f"{int(ts*1000)}.mp4"
        )
        os.makedirs(os.path.dirname(clip_path), exist_ok=True)
        try:
            save_event_clip(camera.rtsp_url, clip_path, settings.event_clip_seconds)
            ev.snapshot_path = None
        except Exception:
            pass
        await push_event(ev)


@app.websocket("/webrtc/ws")
async def webrtc_ws(ws: WebSocket):
    await ws.accept()
    src = ws.query_params.get("src")
    if not src:
        await ws.close()
        return
    api = settings.go2rtc_api_url.rstrip("/")
    ws_url = api.replace("http://", "ws://").replace("https://", "wss://") + f"/api/ws?src={src}"
    headers = None
    if settings.api_login and settings.api_password:
        token = base64.b64encode(f"{settings.api_login}:{settings.api_password}".encode()).decode()
        headers = [("Authorization", f"Basic {token}")]
    try:
        remote = await ws_connect(ws_url, extra_headers=headers)
    except Exception:
        await ws.close()
        return
    async def client_to_remote():
        while True:
            try:
                msg = await ws.receive_text()
            except Exception:
                try:
                    await remote.close()
                except Exception:
                    pass
                break
            try:
                await remote.send(msg)
            except Exception:
                break
    async def remote_to_client():
        try:
            async for msg in remote:
                try:
                    await ws.send_text(msg)
                except Exception:
                    break
        finally:
            try:
                await ws.close()
            except Exception:
                pass
    await asyncio.gather(client_to_remote(), remote_to_client())
