"""Scene detection (PySceneDetect ContentDetector) + ffmpeg silencedetect.

Fallback: if scenedetect fails, fixed 30s intervals. Never crash.
"""
import logging
import re
import subprocess
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

_SILENCE_RE = re.compile(r"silence_start: ([\d.]+)")
_SILENCE_END_RE = re.compile(r"silence_end: ([\d.]+) \| silence_duration: ([\d.]+)")


def detect_scenes(video_path: str, duration: float) -> List[Dict[str, float]]:
    """Returns [{"start": float, "end": float}] scene list."""
    try:
        from scenedetect import ContentDetector, SceneManager, open_video
        video = open_video(video_path)
        manager = SceneManager()
        manager.add_detector(ContentDetector())
        manager.detect_scenes(video, show_progress=False)
        scenes = manager.get_scene_list()
        out = [{"start": s[0].get_seconds(), "end": s[1].get_seconds()} for s in scenes]
        if out:
            return out
    except Exception as exc:  # noqa: BLE001
        logger.warning("PySceneDetect failed (%s); using fixed intervals", exc)
    # Fallback: fixed 30s intervals.
    out, t = [], 0.0
    while t < duration:
        out.append({"start": t, "end": min(duration, t + 30.0)})
        t += 30.0
    return out or [{"start": 0.0, "end": duration}]


def detect_silence(video_path: str, noise_db: float = -35.0, min_duration: float = 0.5) -> List[Dict[str, float]]:
    """ffmpeg silencedetect -> [{"start": float, "end": float}]. Empty on failure."""
    try:
        proc = subprocess.run(
            ["ffmpeg", "-hide_banner", "-i", video_path, "-af",
             f"silencedetect=noise={noise_db}dB:d={min_duration}", "-f", "null", "-"],
            capture_output=True, text=True, timeout=3600)
        text = proc.stderr or ""
        starts = [float(m.group(1)) for m in _SILENCE_RE.finditer(text)]
        ends = [(float(m.group(1)), float(m.group(2))) for m in _SILENCE_END_RE.finditer(text)]
        out = []
        for i, s in enumerate(starts):
            if i < len(ends):
                out.append({"start": s, "end": ends[i][0]})
        return out
    except Exception as exc:  # noqa: BLE001
        logger.warning("silencedetect failed (%s)", exc)
        return []


def trim_silence_edges(start: float, end: float, silence: List[Dict[str, float]]) -> tuple[float, float]:
    """Trim leading/trailing silence inside a window (silence-trimmed clips)."""
    for s in silence:
        if s["start"] <= start + 0.1 and s["end"] > start and s["end"] < end:
            start = min(s["end"], end - 5)
    for s in reversed(silence):
        if s["end"] >= end - 0.1 and s["start"] < end and s["start"] > start:
            end = max(s["start"], start + 5)
    return start, end
