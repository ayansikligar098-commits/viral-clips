"""Word-by-word animated ASS subtitles (karaoke highlight).

Two separate style axes (kept distinct on purpose):
- *Editing* styles (services/styles.py: Podcast/Gaming/...) control crop,
  zoom, cut pace and filters.
- *Caption* presets (here) control subtitle font/size/colour/animation
  only: "Bold Yellow", "White Minimal", "Neon", "Hormozi-style".
  `caption_style` selects a preset; legacy names Bold/Minimal/Neon map
  onto presets.

Important words (keywords / emotion / emphasis words) are highlighted in
a different colour + bold inside the karaoke line, so they pop while the
current word is highlighted.

Language: Hindi, English and Hinglish are supported. Whisper detects the
language; Hinglish (Roman Hindi) is preserved as spoken, never translated.
Devanagari text uses Noto Sans Devanagari (present on this VM), falling
back to DejaVu Sans with a log line when it is not available.
"""
import logging
import re
import subprocess
from dataclasses import dataclass
from typing import Any, Dict, List

from app.services.text_norm import contains_devanagari, normalize_words

logger = logging.getLogger(__name__)

IMPORTANT_WORDS = {
    "secret", "never", "always", "free", "best", "worst", "truth", "amazing",
    "insane", "crazy", "mistake", "nobody", "everyone", "stop", "watch",
    "viral", "money", "success", "fail", "win", "love", "hate", "shocking",
    "unbelievable", "incredible", "brilliant", "important", "key", "first",
    "secret", "hidden", "kya", "matlab", "sabse", "pehle", "zaroor",
}

ASS_HEADER = """[Script Info]
ScriptType: v4.00+
PlayResX: 720
PlayResY: 1280
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
{style_line}

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


@dataclass
class CaptionPreset:
    """A real ASS style preset. Colours are ASS BGR hex (&HBBGGRR)."""
    name: str
    font: str
    font_size: int
    bold: bool
    primary_colour: str    # normal words
    highlight_colour: str  # karaoke (current) word
    important_colour: str  # important/keyword words
    outline_colour: str = "&H00000000"
    outline: int = 3
    shadow: int = 2
    alignment: int = 2
    margin_v: int = 120
    # Animation: libass \fad / \move applied per line via override tag.
    animation: str = "fade"  # fade | pop | slide-up | none

    def ass_style_line(self, style_name: str = "Clip") -> str:
        bold = -1 if self.bold else 0
        return (
            f"Style: {style_name},{self.font},{self.font_size},"
            f"{self.primary_colour},{self.highlight_colour},{self.outline_colour},"
            f"{self.outline_colour},{bold},0,0,0,100,100,0,0,1,{self.outline},"
            f"{self.shadow},{self.alignment},10,10,{self.margin_v},1"
        )

    def animation_tag(self) -> str:
        if self.animation == "fade":
            return r"{\fad(120,120)}"
        if self.animation == "pop":
            return r"{\fad(60,60)\fscx110\fscy110}"
        if self.animation == "slide-up":
            return r"{\fad(100,100)\move(360,700,360,640)}"
        return ""


CAPTION_PRESETS: Dict[str, CaptionPreset] = {
    "Bold Yellow": CaptionPreset(
        name="Bold Yellow", font="DejaVu Sans", font_size=56, bold=True,
        primary_colour="&H00FFFFFF", highlight_colour="&H0000FFFF",
        important_colour="&H0000A5FF", outline=3, shadow=2, margin_v=120,
        animation="pop"),
    "White Minimal": CaptionPreset(
        name="White Minimal", font="DejaVu Sans", font_size=48, bold=False,
        primary_colour="&H00E8E8E8", highlight_colour="&H00FFFFFF",
        important_colour="&H00FFFFFF", outline=1, shadow=0, margin_v=90,
        animation="fade"),
    "Neon": CaptionPreset(
        name="Neon", font="DejaVu Sans", font_size=60, bold=True,
        primary_colour="&H00FFFFFF", highlight_colour="&H0000FF00",
        important_colour="&H00FF00FF", outline=4, shadow=3, margin_v=140,
        animation="pop"),
    "Hormozi-style": CaptionPreset(
        name="Hormozi-style", font="DejaVu Sans", font_size=72, bold=True,
        primary_colour="&H00FFFFFF", highlight_colour="&H0000FFFF",
        important_colour="&H0000A5FF", outline=5, shadow=3, margin_v=150,
        animation="slide-up"),
}

# Legacy / alias names -> preset names.
CAPTION_STYLE_ALIASES = {
    "Bold": "Bold Yellow", "Minimal": "White Minimal", "Neon": "Neon",
    "Hormozi": "Hormozi-style", "bold yellow": "Bold Yellow",
    "white minimal": "White Minimal", "neon": "Neon",
    "hormozi-style": "Hormozi-style",
}


def get_caption_preset(name: str | None) -> CaptionPreset:
    if not name:
        return CAPTION_PRESETS["Bold Yellow"]
    if name in CAPTION_PRESETS:
        return CAPTION_PRESETS[name]
    if name in CAPTION_STYLE_ALIASES:
        return CAPTION_PRESETS[CAPTION_STYLE_ALIASES[name]]
    for key, preset in CAPTION_PRESETS.items():
        if key.lower() == name.lower():
            return preset
    return CAPTION_PRESETS["Bold Yellow"]


def list_caption_presets() -> list[dict]:
    return [{"name": p.name, "font": p.font, "font_size": p.font_size,
             "animation": p.animation} for p in CAPTION_PRESETS.values()]


def _font_for_text(text: str, preset: CaptionPreset) -> str:
    """Devanagari -> Noto Sans Devanagari if installed, else DejaVu Sans
    (glyphs may be missing) with a warning logged once per call."""
    if not contains_devanagari(text):
        return preset.font
    try:
        out = subprocess.run(["fc-list", ":family", "Noto Sans Devanagari"],
                             capture_output=True, text=True, timeout=10)
        if "Noto Sans Devanagari" in (out.stdout or ""):
            return "Noto Sans Devanagari"
    except Exception:
        pass
    logger.warning("Noto Sans Devanagari not found — Devanagari subtitles "
                   "will fall back to %s and may show missing glyphs", preset.font)
    return preset.font


def _ass_time(t: float) -> str:
    t = max(0.0, t)
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = int(t % 60)
    cs = int(round((t - int(t)) * 100))
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def _clean(text: str) -> str:
    return re.sub(r"[{}\\]", "", text)


def _is_important(word: str) -> bool:
    core = re.sub(r"[^a-zA-Z]", "", word).lower()
    return core in IMPORTANT_WORDS


def generate_ass(words: List[Dict[str, Any]], start: float, end: float,
                 caption_style: str | CaptionPreset | None = None,
                 style=None) -> str:
    """One Dialogue line per word-group (<=4 words / 2.5s).

    Each word gets a \\kf karaoke duration (current word = highlight
    colour); important words additionally get their important colour +
    bold via an override tag, so they stand out even when not current.
    Words are first run through the transcript normaliser so subtitles
    show proper punctuation/capitalisation, not raw Whisper lowercase.
    `style` (legacy) accepts an editing Style — its caption params are
    ignored in favour of the caption preset.
    """
    preset = caption_style if isinstance(caption_style, CaptionPreset) else get_caption_preset(
        caption_style if isinstance(caption_style, str) else None)
    words = normalize_words(words)
    window = [w for w in words if w.get("end", 0) > start and w.get("start", 0) < end]
    font = _font_for_text(" ".join(w.get("word", "") for w in window), preset)
    preset_for_line = CaptionPreset(**{**preset.__dict__, "font": font})
    lines = [ASS_HEADER.format(style_line=preset_for_line.ass_style_line("Clip"))]
    if not window:
        return "".join(lines)
    groups: List[List[Dict[str, Any]]] = []
    cur: List[Dict[str, Any]] = []
    for w in window:
        cur.append(w)
        if len(cur) >= 4 or (cur and w.get("end", 0) - cur[0].get("start", 0) >= 2.5):
            groups.append(cur)
            cur = []
    if cur:
        groups.append(cur)
    for group in groups:
        g_start = max(0.0, group[0]["start"] - start)
        g_end = max(g_start + 0.2, group[-1]["end"] - start)
        parts = [preset.animation_tag()]
        for w in group:
            dur_cs = max(1, int(round((w.get("end", w.get("start", 0) + 0.3) - w.get("start", 0)) * 100)))
            word = _clean(w.get("word", ""))
            if _is_important(word):
                # Important word: karaoke timing + important colour + bold.
                parts.append(f"{{\\kf{dur_cs}\\c{preset.important_colour}&\\b1}}{word}{{\\r}}")
            else:
                parts.append(f"{{\\kf{dur_cs}}}{word}")
        text = " ".join(parts)
        lines.append(f"Dialogue: 0,{_ass_time(g_start)},{_ass_time(g_end)},Clip,,0,0,0,,{text}\n")
    return "".join(lines)


def write_ass(path: str, words, start, end, caption_style=None, style=None) -> str:
    content = generate_ass(words, start, end, caption_style=caption_style, style=style)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path
