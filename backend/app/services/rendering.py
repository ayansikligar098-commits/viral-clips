"""FFmpeg rendering: 9:16 smart crop, silence trim, loudnorm, burned ASS
captions, cover thumbnail. Enforces Reels limits: <=90s, H.264, <=250MB.

Face/speaker framing goes ONLY through the Tracker interface
(app.services.tracking.base.get_tracker) — never Haar directly.
Style differences are real FFmpeg/ASS parameters via services/styles.py.
"""
import logging
import os
import subprocess
from typing import Any, Dict, List, Optional

import cv2

from app.services.captions import write_ass
from app.services.styles import Style, get_style
from app.services.tracking.base import get_tracker

logger = logging.getLogger(__name__)
MAX_CLIP_SECONDS = 90
MAX_BYTES = 250 * 1024 * 1024


def probe(video_path: str) -> Dict[str, Any]:
    import json as _json
    try:
        proc = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format",
             "-show_streams", video_path],
            capture_output=True, text=True, timeout=120)
        data = _json.loads(proc.stdout or "{}")
        fmt = data.get("format", {})
        video_stream = next((s for s in data.get("streams", []) if s.get("codec_type") == "video"), {})
        fps_raw = video_stream.get("avg_frame_rate", "0/1")
        try:
            num, den = fps_raw.split("/")
            fps = float(num) / float(den) if float(den) else 0.0
        except Exception:
            fps = 0.0
        return {"duration": float(fmt.get("duration") or 0),
                "fps": fps,
                "width": int(video_stream.get("width") or 0),
                "height": int(video_stream.get("height") or 0)}
    except Exception as exc:  # noqa: BLE001
        logger.warning("ffprobe failed: %s", exc)
        return {"duration": 0.0, "fps": 0.0, "width": 0, "height": 0}


def face_centre_x(video_path: str, start: float, end: float, samples: int = 6) -> float:
    """Sample frames in [start, end], track speaker via Tracker interface,
    return smoothed normalised centre-x (0..1). 0.5 = centre fallback."""
    tracker = get_tracker()
    tracker.reset()
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return 0.5
    centres: List[float] = []
    try:
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        for i in range(samples):
            t = start + (end - start) * (i + 0.5) / samples
            cap.set(cv2.CAP_PROP_POS_FRAMES, int(t * fps))
            ok, frame = cap.read()
            if not ok or frame is None:
                continue
            res = tracker.detect_track(frame)
            if res.centre_x is not None:
                centres.append(res.centre_x)
    finally:
        cap.release()
    if not centres:
        return 0.5
    return sum(centres) / len(centres)


def render_clip(video_path: str, out_path: str, start: float, end: float,
                words: List[Dict[str, Any]] = None, style: Style | str | None = None,
                caption_style: Optional[str] = None) -> Dict[str, Any]:
    """Render one 9:16 clip. Returns {"path":..., "duration":..., "size_bytes":...}.
    Raises RuntimeError on ffmpeg failure."""
    words = words or []
    st = get_style(style if isinstance(style, str) else (style.name if isinstance(style, Style) else None))
    # caption_style is NOT an editing style — it selects a subtitle preset
    # in captions.py (Bold Yellow / White Minimal / Neon / Hormozi-style).
    duration = min(end - start, MAX_CLIP_SECONDS)
    end = start + duration
    if duration <= 0:
        raise RuntimeError("clip duration must be > 0")

    meta = probe(video_path)
    w, h = meta.get("width") or 1920, meta.get("height") or 1080
    # Smart crop: face-centred if style wants it, else centre.
    if st.crop_mode == "face":
        cx = face_centre_x(video_path, start, end)
    else:
        cx = 0.5
    # 9:16 crop width = h * 9/16, clamped; x offset from centre, clamped.
    crop_w = int(h * 9 / 16)
    crop_w = min(crop_w, w)
    x = int(cx * w - crop_w / 2)
    x = max(0, min(x, w - crop_w))
    x -= x % 2  # even for yuv420p
    crop_w -= crop_w % 2
    zoom = st.zoom_factor
    vf_parts = [f"crop={crop_w}:{h}:{x}:0"]
    vf_parts.append("scale=720:1280")
    if zoom and zoom != 1.0:
        # Punch-in zoom AFTER reaching 720x1280, so the crop source is
        # always >= 720x1280 (scaling first avoids the invalid-crop bug).
        vf_parts.append(f"scale={int(720 * zoom)}:{int(1280 * zoom)}")
        vf_parts.append("crop=720:1280")
    if st.extra_ffmpeg_vf:
        vf_parts.append(st.extra_ffmpeg_vf)
    vf_parts.append("format=yuv420p")
    # Burned captions via libass (ASS file next to output). Caption preset
    # is separate from the editing style: caption_style selects a subtitle
    # preset (Bold Yellow / White Minimal / Neon / Hormozi-style).
    ass_path = out_path + ".ass"
    write_ass(ass_path, words, start, end, caption_style=caption_style or "Bold Yellow")
    vf_parts.append(f"ass='{ass_path}'")
    vf = ",".join(vf_parts)
    af = f"loudnorm=I={st.loudnorm_target}:TP=-1.5:LRA=11"
    cmd = ["ffmpeg", "-y", "-hide_banner", "-ss", str(start), "-i", video_path,
           "-t", str(duration), "-vf", vf, "-af", af,
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
           "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", out_path]
    logger.info("Rendering clip: %s", " ".join(cmd))
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
    try:
        os.remove(ass_path)
    except OSError:
        pass
    if proc.returncode != 0 or not os.path.exists(out_path):
        raise RuntimeError(f"ffmpeg render failed: {(proc.stderr or '')[-2000:]}")
    size = os.path.getsize(out_path)
    if size > MAX_BYTES:
        raise RuntimeError(f"rendered clip {size} bytes exceeds 250MB Reels limit")
    return {"path": out_path, "duration": duration, "size_bytes": size,
            "crop_centre_x": cx, "style": st.name}


def make_cover(video_path: str, cover_path: str, clip_start: float) -> Optional[str]:
    """Attractive Reel cover: frame ~1s into the clip, scaled/cropped to
    1080x1920 (9:16) so it is a real Reel thumbnail, not a raw frame."""
    t = clip_start + 1.0
    proc = subprocess.run(
        ["ffmpeg", "-y", "-hide_banner", "-ss", str(t), "-i", video_path,
         "-frames:v", "1",
         "-vf", "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920",
         "-q:v", "3", cover_path],
        capture_output=True, text=True, timeout=120)
    if proc.returncode == 0 and os.path.exists(cover_path):
        return cover_path
    logger.warning("cover thumbnail failed: %s", (proc.stderr or "")[-500:])
    return None
