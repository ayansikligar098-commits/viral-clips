import json
import os
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.models.models import Clip, User, Video
from app.schemas import ClipOut, ClipPatch, RenderRequest
from app.services.captions import get_caption_preset, list_caption_presets
from app.services.styles import list_styles

router = APIRouter(prefix="/api/clips", tags=["clips"])


def _out(c: Clip) -> ClipOut:
    return ClipOut(id=c.id, video_id=c.video_id, start_time=c.start_time, end_time=c.end_time,
                   score=c.score, score_breakdown=c.breakdown(),
                   quality_gate_passed=c.quality_gate_passed,
                   quality_gate_failures=c.gate_failures(),
                   context_preserved=c.context_preserved, context_reason=c.context_reason,
                   title=c.title, title_variations=c.title_variation_list(),
                   caption=c.caption, caption_variations=c.caption_variation_list(),
                   hashtags=c.hashtag_list(),
                   hooks=c.hook_list(), hook_variations=c.hook_variation_list(),
                   selected_caption=c.selected_caption,
                   selected_hook=c.selected_hook, cta=c.cta,
                   detected_language=c.detected_language,
                   file_path=c.file_path, cover_path=c.cover_path,
                   caption_style=c.caption_style, edit_style=c.edit_style,
                   style=c.edit_style, status=c.status)


@router.get("/styles")
def get_styles():
    return {"styles": list_styles()}


@router.get("/caption-presets")
def get_caption_presets():
    """Subtitle font/colour/animation presets (distinct from editing styles)."""
    return {"caption_presets": list_caption_presets()}


@router.get("", response_model=list[ClipOut])
def list_clips(video_id: Optional[int] = None, db: Session = Depends(get_db),
               user: User = Depends(get_current_user)):
    q = db.query(Clip).filter(Clip.user_id == user.id)
    if video_id:
        q = q.filter(Clip.video_id == video_id)
    return [_out(c) for c in q.order_by(Clip.score.desc()).all()]


@router.get("/{clip_id}", response_model=ClipOut)
def get_clip(clip_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    c = db.query(Clip).filter(Clip.id == clip_id, Clip.user_id == user.id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Clip not found")
    return _out(c)


@router.patch("/{clip_id}", response_model=ClipOut)
def patch_clip(clip_id: int, payload: ClipPatch,
               db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Editor update — auto-generated text is pre-filled; the user edits
    optionally. The saved version is what publish uses."""
    c = db.query(Clip).filter(Clip.id == clip_id, Clip.user_id == user.id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Clip not found")
    if payload.title is not None:
        c.title = payload.title
    if payload.title_variations is not None:
        c.title_variations = json.dumps(payload.title_variations[:3])
    if payload.caption is not None:
        c.caption = payload.caption
        c.selected_caption = payload.caption
    if payload.caption_variations is not None:
        c.caption_variations = json.dumps(payload.caption_variations[:3])
    if payload.hashtags is not None:
        c.hashtags = json.dumps(payload.hashtags[:12])
    hooks = payload.hooks if payload.hooks is not None else payload.hook_variations
    if hooks is not None:
        c.hooks = json.dumps(hooks[:5])
    if payload.selected_caption is not None:
        c.selected_caption = payload.selected_caption
    if payload.selected_hook is not None:
        c.selected_hook = payload.selected_hook
    if payload.cta is not None:
        c.cta = payload.cta
    if payload.caption_style is not None:
        c.caption_style = get_caption_preset(payload.caption_style).name
    edit_style = payload.edit_style if payload.edit_style is not None else payload.style
    if edit_style is not None:
        from app.services.styles import get_style
        c.edit_style = get_style(edit_style).name
    db.commit()
    db.refresh(c)
    return _out(c)


@router.post("/{clip_id}/render", response_model=ClipOut)
def render_clip_endpoint(clip_id: int, payload: RenderRequest,
                         db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    from app.services.rendering import render_clip, make_cover
    from app.services.styles import get_style

    c = db.query(Clip).filter(Clip.id == clip_id, Clip.user_id == user.id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Clip not found")
    if not c.quality_gate_passed:
        raise HTTPException(status_code=400,
                            detail=f"Clip failed quality gate: {c.gate_failures()} — cannot render")
    video = db.query(Video).filter(Video.id == c.video_id).first()
    if not video or not os.path.exists(video.path):
        raise HTTPException(status_code=404, detail="Source video file not found")
    # Accept BOTH trim_start/trim_end AND start_time/end_time aliases;
    # trim_* wins when both are sent. Same for edit_style / style.
    start = payload.trim_start
    if start is None:
        start = payload.start_time
    if start is None:
        start = c.start_time
    end = payload.trim_end
    if end is None:
        end = payload.end_time
    if end is None:
        end = c.end_time
    if end - start > 90 or end - start <= 0:
        raise HTTPException(status_code=400, detail="Trimmed clip must be 1-90s")
    style_name = payload.edit_style or payload.style or c.edit_style or "Podcast"
    caption_style = get_caption_preset(payload.caption_style or c.caption_style or "Bold Yellow").name
    # Words for captions: re-read from stored breakdown? We stored no words;
    # render without word captions if unavailable (ASS will be empty header).
    # In the worker path words are passed directly; here we render from the
    # source video range with no transcript words unless re-transcribed.
    from app.services.transcription import transcribe
    words = transcribe(video.path, settings.WHISPER_MODEL).get("words", [])
    out_path = str(settings.clips_dir / f"clip_{c.id}_{style_name.replace(' ', '_')}.mp4")
    c.status = "rendering"
    db.commit()
    try:
        result = render_clip(video.path, out_path, start, end, words=words,
                             style=style_name, caption_style=caption_style)
    except Exception as exc:
        c.status = "failed"
        db.commit()
        raise HTTPException(status_code=500, detail=str(exc))
    c.file_path = result["path"]
    c.start_time, c.end_time = start, end
    c.edit_style = get_style(style_name).name
    c.caption_style = caption_style
    c.status = "ready"
    cover = make_cover(video.path, str(settings.covers_dir / f"clip_{c.id}.jpg"), start)
    if cover:
        c.cover_path = cover
    db.commit()
    db.refresh(c)
    return _out(c)


@router.get("/{clip_id}/file")
def get_clip_file(clip_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    c = db.query(Clip).filter(Clip.id == clip_id, Clip.user_id == user.id).first()
    if not c or not c.file_path or not os.path.exists(c.file_path):
        raise HTTPException(status_code=404, detail="Clip file not found")
    return FileResponse(c.file_path, media_type="video/mp4", filename=os.path.basename(c.file_path))


@router.get("/{clip_id}/cover")
def get_clip_cover(clip_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    c = db.query(Clip).filter(Clip.id == clip_id, Clip.user_id == user.id).first()
    if not c or not c.cover_path or not os.path.exists(c.cover_path):
        raise HTTPException(status_code=404, detail="Cover not found")
    return FileResponse(c.cover_path, media_type="image/jpeg")
