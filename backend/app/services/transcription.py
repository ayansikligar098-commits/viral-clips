"""Transcription via faster-whisper (CPU, tiny default).

If the model cannot be downloaded/imported, log clearly and fall back to
silence/scene-only segmentation with words=[] and transcribed=False —
never crash, never fake a transcript.
"""
import logging
from typing import Any, Dict, List

from app.services.text_norm import detect_language, normalize_words

logger = logging.getLogger(__name__)


def _patch_av_open_for_faster_whisper() -> None:
    """Compatibility shim (verified 2026-11-15): faster-whisper <=1.2.1 calls
    ``av.open(path, mode="r", metadata_errors="ignore")``, but PyAV >= 15
    removed the ``metadata_errors`` kwarg, so every transcribe() call raised
    ``TypeError: open() got an unexpected keyword argument 'metadata_errors'``
    and the pipeline silently fell back to no-transcript mode. Dropping the
    kwarg is safe: it only controlled whether corrupt metadata raised.
    faster-whisper looks up ``av.open`` at call time, so patching the
    module attribute here fixes decode_audio without touching the library.
    """
    try:
        import av
    except Exception:
        return
    orig_open = av.open

    def _open(*args, **kwargs):
        kwargs.pop("metadata_errors", None)
        return orig_open(*args, **kwargs)

    if getattr(av.open, "_viral_clips_patched", False):
        return
    _open._viral_clips_patched = True  # type: ignore[attr-defined]
    av.open = _open  # type: ignore[method-assign]


def transcribe(video_path: str, model_name: str = "tiny") -> Dict[str, Any]:
    """Returns {"words": [...], "segments": [...], "language": str|None,
    "transcribed": bool, "error": str|None}.
    Word: {"word": str, "start": float, "end": float}."""
    _patch_av_open_for_faster_whisper()
    try:
        from faster_whisper import WhisperModel
    except Exception as exc:  # noqa: BLE001
        logger.warning("faster-whisper unavailable, falling back to no-transcript mode: %s", exc)
        return {"words": [], "segments": [], "language": None, "detected_language": None,
                "transcribed": False,
                "error": f"faster-whisper import failed: {exc}"}
    try:
        model = WhisperModel(model_name, device="cpu", compute_type="int8")
        segments, info = model.transcribe(video_path, word_timestamps=True)
        words: List[Dict[str, Any]] = []
        out_segments: List[Dict[str, Any]] = []
        for seg in segments:
            out_segments.append({"start": seg.start, "end": seg.end, "text": seg.text})
            for w in (seg.words or []):
                words.append({"word": w.word.strip(), "start": float(w.start), "end": float(w.end)})
        # Normalise punctuation/capitalisation; preserve Hinglish as spoken.
        words = normalize_words(words)
        full_text = " ".join(w["word"] for w in words)
        detected = detect_language(info.language, full_text)
        logger.info("Transcribed %s: %d words, whisper_lang=%s detected=%s",
                    video_path, len(words), info.language, detected)
        return {"words": words, "segments": out_segments, "language": info.language,
                "detected_language": detected,
                "transcribed": True, "error": None}
    except Exception as exc:  # noqa: BLE001
        logger.warning("Whisper transcription failed (%s); continuing without transcript", exc)
        return {"words": [], "segments": [], "language": None, "detected_language": None,
                "transcribed": False, "error": str(exc)}
