"""YouTube download service (yt-dlp).

Paste-a-link flow: validate the URL, download the video (<=720p mp4) into
the same storage/videos directory the file-upload flow uses, and return the
local path + metadata so the caller can create the usual Video + Job rows
and the existing worker pipeline runs unchanged.

Only videos the user owns or is licensed to use may be downloaded — the
endpoint requires owns_content=true, exactly like file upload.
"""
import logging
import os
import re
import uuid
from pathlib import Path
from urllib.parse import parse_qs, urlparse

logger = logging.getLogger(__name__)

# Free-test guard (seconds): reject videos longer than 15 minutes.
DEFAULT_MAX_DURATION_SECONDS = 900

_VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")


class YoutubeValidationError(ValueError):
    """URL is not an accepted YouTube video URL."""


class YoutubeDownloadError(Exception):
    """Download failed. `status` is the HTTP status the API should return:
    400 = the video itself is unavailable/private/restricted;
    502 = YouTube/network blocked the download."""

    def __init__(self, message: str, status: int = 502):
        super().__init__(message)
        self.status = status


def validate_youtube_url(raw_url: str) -> str:
    """Return the canonical watch URL for an accepted YouTube video URL.

    Accepted: youtube.com/watch?v=<id>, youtu.be/<id>,
    youtube.com/shorts/<id> (www/m/music subdomains allowed).
    Everything else raises YoutubeValidationError.
    """
    if not raw_url or not isinstance(raw_url, str):
        raise YoutubeValidationError("youtube_url is required")
    url = raw_url.strip()
    try:
        parsed = urlparse(url)
    except Exception:
        raise YoutubeValidationError("Invalid YouTube URL")
    if parsed.scheme not in {"http", "https"}:
        raise YoutubeValidationError("YouTube URL must start with http:// or https://")
    host = (parsed.netloc or "").lower().split(":")[0]
    if host.startswith("www."):
        host = host[4:]
    video_id: str | None = None
    if host == "youtu.be":
        video_id = parsed.path.strip("/").split("/")[0] or None
    elif host in {"youtube.com", "m.youtube.com", "music.youtube.com"}:
        path = parsed.path
        if path == "/watch":
            video_id = parse_qs(parsed.query).get("v", [None])[0]
        elif path.startswith("/shorts/"):
            video_id = path.split("/")[2] if len(path.split("/")) > 2 else None
        elif path.startswith("/embed/"):
            video_id = path.split("/")[2] if len(path.split("/")) > 2 else None
    if not video_id or not _VIDEO_ID_RE.match(video_id):
        raise YoutubeValidationError(
            "URL must be a YouTube video link: youtube.com/watch?v=…, "
            "youtu.be/…, or youtube.com/shorts/…"
        )
    return f"https://www.youtube.com/watch?v={video_id}"


def _is_content_error(msg: str) -> bool:
    """True when the video itself cannot be fetched (client-side problem)."""
    low = msg.lower()
    return any(
        phrase in low
        for phrase in (
            "video unavailable", "private video", "this video is private",
            "age", "removed", "deleted", "no longer available",
            "does not exist", "not available", "sign in to confirm your age",
            "login required", "join this channel",
        )
    )


def download_youtube_video(
    youtube_url: str,
    dest_dir: str | Path,
    max_duration_seconds: int = DEFAULT_MAX_DURATION_SECONDS,
    timeout: int = 120,
) -> tuple[str, dict]:
    """Download a YouTube video to dest_dir.

    Returns (local_path, info) where info has title/duration/video_id.
    Raises YoutubeValidationError / YoutubeDownloadError.
    """
    canonical = validate_youtube_url(youtube_url)
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    try:
        import yt_dlp
    except ImportError as exc:  # pragma: no cover - missing dependency
        raise YoutubeDownloadError(
            "YouTube downloads are not available on this server (yt-dlp is not installed).",
            status=502,
        ) from exc

    tmp_base = dest_dir / f"yt-{uuid.uuid4().hex}"
    # Format: combined mp4 first (android client serves itag 18/22, which
    # need no merge and no PO token). DASH video-only streams are avoided:
    # from shared IPs YouTube forces SABR / bot-checks the web client.
    ydl_opts = {
        "format": "best[height<=720][ext=mp4]/best[height<=720]/best",
        "merge_output_format": "mp4",
        "outtmpl": str(tmp_base) + ".%(ext)s",
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "socket_timeout": timeout,
        # Generous retries: YouTube/proxy connections drop mid-chunk and
        # each retry resumes the chunk; giving up too early fails downloads
        # that would otherwise complete (seen repeatedly on flaky links).
        "retries": 30,
        "fragment_retries": 30,
        # 1 MB Range chunks: the egress proxy cuts long transfers, and
        # small chunks + retries get through where one big GET stalls.
        "http_chunk_size": 1048576,
        # Android player client: the web client is bot-checked
        # ("Sign in to confirm you're not a bot") from shared IPs, while
        # the android client still returns working combined-mp4 formats.
        "extractor_args": {"youtube": {"player_client": ["android"]}},
        # Avoid yt-dlp picking up a stray browser/cookies setup; anonymous fetch.
        "no_cookies": True,
    }
    # TLS-intercepting egress proxy (this dev VM only): yt-dlp defaults to
    # the certifi bundle, which does not contain the proxy's local CA.
    # `no-certifi` makes it use the system cert store instead, which honours
    # SSL_CERT_FILE / REQUESTS_CA_BUNDLE — verification stays ON.
    # On normal hosts (e.g. Render) those env vars are absent, so the
    # defaults (certifi, no proxy) apply unchanged.
    ca_bundle = os.environ.get("SSL_CERT_FILE") or os.environ.get("REQUESTS_CA_BUNDLE")
    if ca_bundle and os.path.exists(ca_bundle):
        ydl_opts["compat_opts"] = {"no-certifi"}
    proxy = (os.environ.get("https_proxy") or os.environ.get("HTTPS_PROXY")
             or os.environ.get("http_proxy") or os.environ.get("HTTP_PROXY"))
    if proxy:
        ydl_opts["proxy"] = proxy
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(canonical, download=False)
            if not info:
                raise YoutubeDownloadError("Could not read this YouTube video.", status=502)
            duration = info.get("duration")
            if duration and duration > max_duration_seconds:
                raise YoutubeDownloadError(
                    f"This video is {int(duration // 60)} minutes long — "
                    f"the free test only accepts YouTube videos up to "
                    f"{max_duration_seconds // 60} minutes.",
                    status=400,
                )
            info = ydl.extract_info(canonical, download=True)
    except YoutubeDownloadError:
        raise
    except Exception as exc:  # noqa: BLE001 - yt-dlp raises DownloadError etc.
        msg = str(exc)
        logger.warning("yt-dlp download failed for %s: %s", canonical, msg)
        if _is_content_error(msg):
            raise YoutubeDownloadError(
                "This YouTube video is unavailable, private, or restricted.",
                status=400,
            ) from exc
        if "sign in to confirm" in msg.lower() or "bot" in msg.lower():
            raise YoutubeDownloadError(
                "YouTube blocked this download (bot check / sign-in required). "
                "Try downloading the video file yourself and uploading it instead.",
                status=502,
            ) from exc
        raise YoutubeDownloadError(
            f"YouTube download failed: {msg[:200]}",
            status=502,
        ) from exc

    # yt-dlp wrote <tmp_base>.mp4 (merge) or .webm fallback.
    candidates = sorted(dest_dir.glob(f"{tmp_base.name}.*"))
    if not candidates:
        raise YoutubeDownloadError("YouTube download finished but no file was created.", status=502)
    downloaded = candidates[0]
    final_name = f"{uuid.uuid4().hex}.mp4"
    final_path = dest_dir / final_name
    os.replace(downloaded, final_path)
    for extra in candidates[1:]:
        try:
            os.remove(extra)
        except OSError:
            pass
    return str(final_path), {
        "title": (info or {}).get("title"),
        "duration": (info or {}).get("duration"),
        "video_id": (info or {}).get("id"),
        "uploader": (info or {}).get("uploader"),
    }
