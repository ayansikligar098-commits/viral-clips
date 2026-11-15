# Tracking implementations

## v1 — Haar (`haar_tracker.py`)
OpenCV Haar cascade, largest face + centroid smoothing. CPU-only, no model
download. Good for talking-head / podcast.

## Planned — YOLO / MediaPipe person detection
Same `Tracker` interface (`app/services/tracking/base.py`):
`detect_track(frame) -> TrackResult` with `bbox` / `centre_x` / `centre_y`.
A future tracker would:
1. Subclass `Tracker` in a new file here, e.g. `yolo_tracker.py`.
2. Return the largest *person* bbox (not just face) — better for gaming /
   full-body shots.
3. Register it in `base.get_tracker()` under its name and set
   `TRACKER_NAME=yolo` (env) — no change needed in `rendering.py`, which
   only calls the interface.

Swap rule: the renderer must never import Haar/YOLO/MediaPipe directly.
