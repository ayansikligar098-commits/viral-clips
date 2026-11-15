"""Tracker interface — swappable face/person tracking.

The renderer (rendering.py) calls ONLY this interface, never Haar/YOLO/
MediaPipe directly. To swap implementations, register a new Tracker and
point TRACKER_NAME at it (env TRACKER_NAME, or pass tracker= to the renderer).

v1: HaarTracker (OpenCV Haar cascade) — see implementations/haar_tracker.py.
Planned: YOLO / MediaPipe person-detection tracker — same interface,
returns the largest person bbox per frame with temporal smoothing.
"""
from dataclasses import dataclass
from typing import Optional

TRACKER_NAME = "haar"  # env TRACKER_NAME can override at runtime


@dataclass
class TrackResult:
    """One frame's tracking result. bbox is (x, y, w, h) in frame pixels,
    or None when no face/person was found in this frame."""
    bbox: Optional[tuple] = None
    confidence: float = 0.0
    centre_x: Optional[float] = None  # normalised 0..1, x-centre of subject
    centre_y: Optional[float] = None


class Tracker:
    """Interface every tracker must implement."""

    name: str = "base"

    def detect_track(self, frame) -> TrackResult:
        """Detect/track the speaker in one BGR frame. Must never raise on
        a bad frame — return TrackResult(bbox=None) instead."""
        raise NotImplementedError

    def reset(self) -> None:
        """Clear temporal state (call at the start of a new clip)."""
        pass


def get_tracker(name: Optional[str] = None) -> Tracker:
    """Registry lookup. Unknown names fall back to Haar."""
    import os

    wanted = (name or os.getenv("TRACKER_NAME") or TRACKER_NAME).lower()
    if wanted in ("haar", "opencv-haar"):
        from app.services.tracking.implementations.haar_tracker import HaarTracker
        return HaarTracker()
    if wanted in ("yolo", "mediapipe", "person"):
        # Planned tracker — not implemented yet; fall back loudly but safely.
        import logging
        logging.getLogger(__name__).warning(
            "Tracker '%s' is planned, not implemented yet — falling back to Haar. "
            "See app/services/tracking/implementations/README.md", wanted)
        from app.services.tracking.implementations.haar_tracker import HaarTracker
        return HaarTracker()
    from app.services.tracking.implementations.haar_tracker import HaarTracker
    return HaarTracker()
