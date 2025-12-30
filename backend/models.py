from typing import List, Optional, Tuple
from pydantic import BaseModel, Field


class Camera(BaseModel):
    id: str
    name: str
    rtsp_url: str


class Detection(BaseModel):
    label: str
    bounding_box: Tuple[int, int, int, int]
    confidence: float = Field(ge=0.0, le=1.0)


class Event(BaseModel):
    camera_id: str
    timestamp: float
    label: str
    bounding_box: Tuple[int, int, int, int]
    confidence: float
    snapshot_path: Optional[str] = None


class CamerasResponse(BaseModel):
    cameras: List[Camera]


class EventsResponse(BaseModel):
    events: List[Event]

