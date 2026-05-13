"""
AI Processor: orchestrates frame acquisition, inference, and callbacks.

Design:
- Frame I/O in background thread (non-blocking)
- Inference in thread pool executor
- Asyncio never blocked
- Graceful error handling with health monitoring
"""
import asyncio
import logging
import time
from typing import Callable, List, Optional

import numpy as np

from ..models import Camera, Detection
from .backends import select_backend
from .backends.base import BaseBackend
from .exceptions import AIProcessorError, FrameSourceError
from .frame_source import FFmpegRawVideoSource, FrameSource
from .health import HealthMonitor, ProcessorMetrics

logger = logging.getLogger("ai.processor")


class AIProcessor:
    """Orchestrates real-time AI inference on live video frames."""

    def __init__(
        self,
        camera: Camera,
        frame_source: Optional[FrameSource] = None,
        backend_pref: str = "auto",
        resolution: str = "640x360",
        target_fps: int = 10,
        on_detections: Optional[
            Callable[[List[Detection], float, np.ndarray], None]
        ] = None,
        health_monitor: Optional[HealthMonitor] = None,
    ):
        """
        Args:
            camera: Camera model with stream metadata
            frame_source: Custom FrameSource (default: FFmpegRawVideoSource)
            backend_pref: AI backend preference ("auto", "cpu", "gpu", "motion")
            resolution: Output resolution "WIDTHxHEIGHT"
            target_fps: Target inference FPS
            on_detections: Callback(detections, timestamp, frame)
            health_monitor: Optional health monitor instance
        """
        self.camera = camera
        self.on_detections = on_detections

        w, h = [int(x) for x in resolution.split("x")]

        # Create frame source
        if frame_source is None:
            try:
                frame_source = FFmpegRawVideoSource(
                    stream_url=camera.rtsp_url,
                    width=w,
                    height=h,
                    fps=target_fps,
                )
            except Exception as e:
                raise FrameSourceError(f"Failed to create frame source: {e}") from e

        self.frame_source = frame_source

        # Select AI backend
        try:
            self.backend: BaseBackend = select_backend(backend_pref)
        except Exception as e:
            raise AIProcessorError(f"Failed to select backend: {e}") from e

        # Health monitoring
        self.health = health_monitor or HealthMonitor()
        self.metrics: ProcessorMetrics = self.health.register_processor(camera.id)

        self._task: Optional[asyncio.Task] = None
        self._running = False

        logger.info(
            "AIProcessor initialized | camera=%s backend=%s resolution=%sx%s fps=%s",
            camera.id,
            self.backend.name,
            w,
            h,
            target_fps,
        )

    async def run(self) -> None:
        """Main async loop: acquire frames → inference → callbacks."""
        self._running = True
        self.metrics.is_running = True

        try:
            self.frame_source.start()
        except Exception as e:
            logger.exception("Failed to start frame source")
            self.metrics.is_running = False
            self.health.report_error(self.camera.id, e)
            return

        loop = asyncio.get_running_loop()

        try:
            while self._running:
                # Get latest frame from async frame source
                frame_obj = await self.frame_source.get_frame()

                if frame_obj is None:
                    await asyncio.sleep(0.01)
                    continue
                
                frame = frame_obj.data

                ts = time.time()

                # Run inference in executor (non-blocking)
                try:
                    dets = await loop.run_in_executor(
                        None,
                        self.backend.process,
                        frame,
                    )
                    latency_ms = (time.time() - ts) * 1000
                    self.health.report_frame_processed(self.camera.id, latency_ms)
                except Exception as e:
                    logger.exception("Backend inference error")
                    self.health.report_error(self.camera.id, e)
                    dets = []

                # Invoke callback if detections found
                if self.on_detections and dets:
                    try:
                        self.on_detections(dets, ts, frame)
                    except Exception as e:
                        logger.exception("Detection callback error")
                        self.health.report_error(self.camera.id, e)

                await asyncio.sleep(0)

        except asyncio.CancelledError:
            logger.info("AIProcessor run cancelled")
        except Exception as e:
            logger.exception("AIProcessor run error")
            self.health.report_error(self.camera.id, e)
        finally:
            self.frame_source.stop()
            self._running = False
            self.metrics.is_running = False
            logger.info(
                "AIProcessor stopped | camera=%s processed=%d dropped=%d",
                self.camera.id,
                self.metrics.frames_processed,
                self.metrics.frames_dropped,
            )

    def _get_latest_frame(self) -> Optional[np.ndarray]:
        """Get latest frame from source (safe for asyncio.to_thread)."""
        try:
            frame = self.frame_source.get_frame()
            if not self.frame_source.is_running:
                logger.warning("Frame source stopped unexpectedly")
                self.health.report_error(
                    self.camera.id,
                    Exception("Frame source stopped"),
                )
            return frame
        except Exception as e:
            logger.exception("Error getting frame")
            self.health.report_error(self.camera.id, e)
            return None

    def start(self, loop: asyncio.AbstractEventLoop) -> None:
        """Create and schedule the processor task."""
        if self._task and not self._task.done():
            logger.warning("AIProcessor already running")
            return

        self._task = loop.create_task(self.run())
        self.health.report_restart(self.camera.id)
        logger.info("AIProcessor task created")

    async def stop(self) -> None:
        """Gracefully stop processor and cleanup."""
        logger.info("Stopping AIProcessor")
        self._running = False

        if self._task:
            try:
                await asyncio.wait_for(self._task, timeout=2)
            except asyncio.TimeoutError:
                logger.warning("AIProcessor stop timeout, cancelling task")
                self._task.cancel()
                try:
                    await self._task
                except asyncio.CancelledError:
                    pass
            except Exception as e:
                logger.exception("AIProcessor stop error")

    @property
    def is_running(self) -> bool:
        """Check if processor is active."""
        return (
            self._running
            and self._task
            and not self._task.done()
            and self.frame_source.is_running
        )

    def get_metrics(self) -> dict:
        """Get current metrics."""
        return self.metrics.to_dict()
