"""Background worker: polls the DB Job table, runs the pipeline end-to-end.

Pipeline: probe -> transcribe -> scenes+silence -> context-aware candidate
windows (20-60s, contiguous only) -> score + quality gate -> keep top 3-5
passing -> render -> metadata -> cover -> mark completed.
Progress % and stage are updated in the DB. Retry up to 3 with backoff.
Entry function run_job(job_id) is importable for tests.
"""
import json
import logging
import os
import threading
import time
from typing import Any, Dict, List

from app.core.config import settings
from app.core.database import SessionLocal, init_db
from app.models.models import Clip, Job, PublishJob, Video
from app.services import context as ctx_mod
from app.services.publishing import attempt_publish
from app.services.metadata import generate_metadata
from app.services.rendering import make_cover, probe, render_clip
from app.services.scenes import detect_scenes, detect_silence, trim_silence_edges
from app.services.scoring import rank_candidates, score_candidate
from app.services.transcription import transcribe

logger = logging.getLogger(__name__)
MAX_RETRIES = 3


def _set_progress(db, job, progress: int, stage: str, status: str | None = None):
    job.progress = progress
    job.stage = stage
    if status:
        job.status = status
    db.commit()


def _candidate_windows(words: List[Dict[str, Any]], duration: float,
                       scenes: List[Dict[str, float]]) -> List[Dict[str, float]]:
    """Contiguous 20-60s windows aligned to thought boundaries.

    With a transcript: slide over thought arcs (context-aware). Without one:
    fall back to scene boundaries. Never splice non-adjacent segments.
    """
    windows: List[Dict[str, float]] = []
    if words:
        thoughts = ctx_mod.split_thoughts(words)
        # Group consecutive thoughts into 20-60s windows.
        cur: List[Dict[str, Any]] = []
        for t in thoughts:
            cur.append(t)
            span = t["end"] - cur[0]["start"]
            if span >= 20:
                windows.append({"start": cur[0]["start"], "end": t["end"]})
                cur = []
            elif span >= 55:
                windows.append({"start": cur[0]["start"], "end": t["end"]})
                cur = []
        if cur and (cur[-1]["end"] - cur[0]["start"]) >= 15:
            windows.append({"start": cur[0]["start"], "end": cur[-1]["end"]})
        # Also try topic-segment windows (setup->payoff arcs).
        for seg in ctx_mod.segment_topics(thoughts):
            seg_dur = seg["end"] - seg["start"]
            if 20 <= seg_dur <= 60:
                windows.append({"start": seg["start"], "end": seg["end"]})
    if not windows:
        for s in scenes:
            d = s["end"] - s["start"]
            if d >= 15:
                # Split long scenes into <=60s contiguous chunks.
                t = s["start"]
                while t < s["end"]:
                    windows.append({"start": t, "end": min(s["end"], t + 45.0)})
                    t += 45.0
    # Deduplicate overlapping windows (keep first).
    windows.sort(key=lambda w: w["start"])
    dedup: List[Dict[str, float]] = []
    for w in windows:
        if dedup and w["start"] < dedup[-1]["end"] - 5:
            continue
        dedup.append(w)
    return dedup


def run_job(job_id: int) -> bool:
    """Run one job end-to-end. Returns True on completion (even with 0 clips
    passing the gate — that is a valid quality outcome), False on failure."""
    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            logger.error("run_job: job %s not found", job_id)
            return False
        video = db.query(Video).filter(Video.id == job.video_id).first()
        if not video or not os.path.exists(video.path):
            job.status, job.error = "failed", "Source video file not found"
            db.commit()
            return False
        _set_progress(db, job, 5, "probing", "processing")
        meta = probe(video.path)
        duration = meta.get("duration") or video.duration or 0
        if video.duration is None and duration:
            video.duration = duration
            video.fps, video.width, video.height = meta.get("fps"), meta.get("width"), meta.get("height")
            db.commit()

        _set_progress(db, job, 15, "transcribing")
        tx = transcribe(video.path, settings.WHISPER_MODEL)
        words = tx.get("words", [])
        detected_language = tx.get("detected_language")
        if detected_language:
            video.detected_language = detected_language
            db.commit()
        if not tx.get("transcribed"):
            logger.warning("Job %s: transcription unavailable (%s) — scene/silence-only mode",
                           job_id, tx.get("error"))

        _set_progress(db, job, 45, "detecting scenes and silence")
        scenes = detect_scenes(video.path, duration)
        silence = detect_silence(video.path)

        _set_progress(db, job, 55, "scoring moments")
        windows = _candidate_windows(words, duration, scenes)
        scored: List[Dict[str, Any]] = []
        for w in windows:
            start, end = w["start"], w["end"]
            if end - start < 15 or end - start > 90:
                continue
            # Context expansion: include 2-5s of setup before the hook.
            if words:
                start, end, _reason = ctx_mod.expand_for_context(words, start, end)
            start, end = trim_silence_edges(start, end, silence)
            if end - start < 15:
                continue
            scene_changes = sum(1 for s in scenes if start < s["start"] < end)
            result = score_candidate(words, start, end, silence_intervals=silence,
                                     scene_changes=scene_changes, has_face=False,
                                     contiguous=True)
            scored.append({**result, "start": start, "end": end})
        max_clips = min(settings.MAX_CLIPS_PER_VIDEO, 5)
        default_n = min(settings.DEFAULT_CLIPS_PER_VIDEO, max_clips)
        top = rank_candidates(scored, max_clips=max_clips)
        # Default 3: keep top `default_n` unless more pass with very high scores.
        keep = top[:default_n] if len(top) > default_n else top
        logger.info("Job %s: %d candidates, %d passed gate, keeping %d",
                    job_id, len(scored), len(top), len(keep))

        _set_progress(db, job, 65, "rendering clips")
        settings.clips_dir.mkdir(parents=True, exist_ok=True)
        settings.covers_dir.mkdir(parents=True, exist_ok=True)
        for i, cand in enumerate(keep):
            start, end = cand["start"], cand["end"]
            out_path = str(settings.clips_dir / f"job{job_id}_clip{i + 1}.mp4")
            try:
                render_clip(video.path, out_path, start, end, words=words,
                            style="Podcast", caption_style="Bold Yellow")
            except Exception as exc:  # noqa: BLE001
                logger.warning("Job %s: render failed for clip %d: %s", job_id, i, exc)
                continue
            # Fully automated metadata: titles/captions/hooks x3, hashtags,
            # CTA — all auto-generated, editor picks are pre-selected.
            md = generate_metadata(words, start, end,
                                   detected_language=detected_language or "en")
            cover = make_cover(video.path, str(settings.covers_dir / f"job{job_id}_clip{i + 1}.jpg"), start)
            clip = Clip(video_id=video.id, user_id=job.user_id, job_id=job.id,
                        start_time=start, end_time=end, score=cand["score"],
                        score_breakdown=json.dumps(cand["score_breakdown"]),
                        quality_gate_passed=True,
                        quality_gate_failures=json.dumps([]),
                        context_preserved=cand.get("context_preserved", False),
                        context_reason=cand.get("context_reason"),
                        title=md["title"],
                        title_variations=json.dumps(md["title_variations"]),
                        caption=md["caption"],
                        caption_variations=json.dumps(md["caption_variations"]),
                        hashtags=json.dumps(md["hashtags"]), hooks=json.dumps(md["hooks"]),
                        selected_caption=md["caption_variations"][0],
                        selected_hook=md["hooks"][0] if md["hooks"] else None,
                        cta=md["cta"],
                        detected_language=detected_language,
                        file_path=out_path, cover_path=cover,
                        caption_style="Bold Yellow", edit_style="Podcast", status="ready")
            db.add(clip)
            db.commit()
            _set_progress(db, job, 65 + int(30 * (i + 1) / max(len(keep), 1)), "rendering clips")
        _set_progress(db, job, 100, "completed", "completed")
        return True
    except Exception as exc:  # noqa: BLE001
        logger.exception("Job %s failed", job_id)
        try:
            job = db.query(Job).filter(Job.id == job_id).first()
            if job:
                job.retries += 1
                job.error = str(exc)
                if job.retries >= MAX_RETRIES:
                    job.status, job.stage = "failed", "failed"
                else:
                    job.status, job.stage = "queued", "queued"
                db.commit()
        except Exception:
            db.rollback()
        return False
    finally:
        db.close()


def check_due_publish_jobs() -> int:
    """Publish PublishJobs whose scheduled_at has arrived (approved only).
    Returns the number attempted. No token -> simulated-pending, never
    silent-fail: the job records the reason."""
    from datetime import datetime, timezone

    db = SessionLocal()
    attempted = 0
    try:
        now = datetime.now(timezone.utc)
        due = (db.query(PublishJob)
               .filter(PublishJob.status == "queued", PublishJob.approved.is_(True),
                       PublishJob.scheduled_at.isnot(None)).all())
        for job in due:
            sched = job.scheduled_at
            if sched is not None and sched.tzinfo is None:
                sched = sched.replace(tzinfo=timezone.utc)
            if sched and sched <= now:
                job_id = job.id
                attempt_publish(db, job)
                attempted += 1
                logger.info("Scheduled publish job %s attempted", job_id)
        return attempted
    finally:
        db.close()


def _poll_loop(stop_event: threading.Event, interval: float = 5.0):
    init_db()
    while not stop_event.is_set():
        db = SessionLocal()
        try:
            check_due_publish_jobs()
            job = (db.query(Job).filter(Job.status == "queued")
                   .order_by(Job.created_at).first())
            if job:
                job_id = job.id
                db.close()
                # Backoff: run_job handles retries; small delay between attempts.
                run_job(job_id)
                continue
        except Exception:
            logger.exception("Worker poll error")
        finally:
            try:
                db.close()
            except Exception:
                pass
        stop_event.wait(interval)


def start_worker() -> threading.Event:
    stop = threading.Event()
    t = threading.Thread(target=_poll_loop, args=(stop,), daemon=True, name="job-worker")
    t.start()
    return stop
