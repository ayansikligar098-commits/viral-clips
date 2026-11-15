"""v1 tracker: OpenCV Haar cascade face detection + centroid smoothing.

Largest face wins; centre is exponentially smoothed so the 9:16 crop does
not jitter frame-to-frame. When no face is found, returns the last known
centre (for a short grace period) then bbox=None so the renderer falls
back to centre-crop. Never raises.
"""
import logging
from typing import Optional

import cv2

from app.services.tracking.base import Tracker, TrackResult

logger = logging.getLogger(__name__)


class HaarTracker(Tracker):
    name = "haar"

    def __init__(self, cascade_path: Optional[str] = None, smoothing: float = 0.35):
        path = cascade_path or (cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
        self._cascade = cv2.CascadeClassifier(path)
        self._loaded = not self._cascade.empty()
        if not self._loaded:
            logger.warning("Haar cascade failed to load from %s", path)
        self._smoothing = smoothing
        self._last_cx: Optional[float] = None
        self._last_cy: Optional[float] = None
        self._misses = 0

    def reset(self) -> None:
        self._last_cx = None
        self._last_cy = None
        self._misses = 0

    def detect_track(self, frame) -> TrackResult:
        try:
            if not self._loaded or frame is None:
                return TrackResult()
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = self._cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5,
                                                   minSize=(40, 40))
            if len(faces) == 0:
                self._misses += 1
                if self._last_cx is not None and self._misses <= 15:
                    return TrackResult(bbox=None, confidence=0.3,
                                       centre_x=self._last_cx, centre_y=self._last_cy)
                return TrackResult()
            self._misses = 0
            # Largest face = main speaker.
            x, y, w, h = max(faces, key=lambda b: b[2] * b[3])
            h_frame, w_frame = frame.shape[:2]
            cx = (x + w / 2) / w_frame
            cy = (y + h / 2) / h_frame
            if self._last_cx is not None:
                cx = self._smoothing * cx + (1 - self._smoothing) * self._last_cx
                cy = self._smoothing * cy + (1 - self._smoothing) * self._last_cy
            self._last_cx, self._last_cy = cx, cy
            return TrackResult(bbox=(int(x), int(y), int(w), int(h)), confidence=0.8,
                               centre_x=cx, centre_y=cy)
        except Exception:
            logger.exception("HaarTracker.detect_track failed; returning no-track")
            return TrackResult()
