"""Editing styles — real FFmpeg/ASS parameters, not labels.

A Style is a preset object: caption font/size/colour/position, zoom/cut
pace, crop behaviour, music bed on/off. New styles are added by adding one
entry to STYLES (or registering via register_style); the core pipeline and
renderer never need to change — they consume a Style via get_style().
"""
from dataclasses import dataclass, field
from typing import Dict


@dataclass
class Style:
    name: str
    description: str
    # ASS caption parameters
    caption_font: str = "DejaVu Sans"
    caption_font_size: int = 64
    caption_bold: bool = True
    primary_colour: str = "&H00FFFFFF"   # ASS BGR hex
    highlight_colour: str = "&H0000FFFF"  # yellow highlight (karaoke word)
    outline_colour: str = "&H00000000"
    outline: int = 3
    shadow: int = 2
    alignment: int = 2  # 2=bottom-centre, 8=top-centre
    margin_v: int = 120
    # Render pace
    zoom_factor: float = 1.0      # 1.0 = no punch-in; >1 = zoom punch-in
    cut_every_s: float = 0.0      # 0 = no forced cuts; else cut cadence
    crop_mode: str = "face"       # face | centre | wide
    music_bed: bool = False
    loudnorm_target: str = "-14"  # LUFS
    extra_ffmpeg_vf: str = ""     # e.g. eq/saturation tweaks

    def ass_style_line(self, style_name: str = "Clip") -> str:
        bold = -1 if self.caption_bold else 0
        return (
            f"Style: {style_name},{self.caption_font},{self.caption_font_size},"
            f"{self.primary_colour},{self.highlight_colour},{self.outline_colour},"
            f"{self.outline_colour},{bold},0,0,0,100,100,0,0,1,{self.outline},"
            f"{self.shadow},{self.alignment},10,10,{self.margin_v},1"
        )


STYLES: Dict[str, Style] = {
    "Podcast": Style(
        name="Podcast",
        description="Calm talking-head: large bold captions, face-centred crop, no zoom.",
        caption_font_size=64, primary_colour="&H00FFFFFF", highlight_colour="&H0000FFFF",
        outline=3, shadow=2, alignment=2, margin_v=120,
        zoom_factor=1.0, cut_every_s=0.0, crop_mode="face", music_bed=False,
    ),
    "Gaming": Style(
        name="Gaming",
        description="High-energy: bigger neon-ish captions, faster cuts, punchy saturation.",
        caption_font_size=72, primary_colour="&H00FFFFFF", highlight_colour="&H0000FF00",
        outline=4, shadow=2, alignment=2, margin_v=140,
        zoom_factor=1.08, cut_every_s=4.0, crop_mode="centre", music_bed=False,
        extra_ffmpeg_vf="eq=saturation=1.25:contrast=1.08",
    ),
    "Cinematic": Style(
        name="Cinematic",
        description="Slow, filmic: smaller elegant captions, gentle zoom, letterbox feel.",
        caption_font="DejaVu Serif", caption_font_size=52, caption_bold=False,
        primary_colour="&H00FFFFFF", highlight_colour="&H00D8E8FF",
        outline=2, shadow=1, alignment=2, margin_v=100,
        zoom_factor=1.05, cut_every_s=0.0, crop_mode="centre", music_bed=False,
        extra_ffmpeg_vf="eq=saturation=0.95:contrast=1.05",
    ),
    "Hormozi-inspired": Style(
        name="Hormozi-inspired",
        description="Direct-to-camera business: huge bold captions, strong punch-in zoom.",
        caption_font_size=84, primary_colour="&H00FFFFFF", highlight_colour="&H0000FFFF",
        outline=5, shadow=3, alignment=2, margin_v=150,
        zoom_factor=1.15, cut_every_s=3.0, crop_mode="face", music_bed=False,
        extra_ffmpeg_vf="eq=contrast=1.12:saturation=1.1",
    ),
    "Minimal Captions": Style(
        name="Minimal Captions",
        description="Subtle captions: small, low outline, no zoom, no cuts.",
        caption_font_size=44, caption_bold=False,
        primary_colour="&H00E8E8E8", highlight_colour="&H00FFFFFF",
        outline=1, shadow=0, alignment=2, margin_v=90,
        zoom_factor=1.0, cut_every_s=0.0, crop_mode="face", music_bed=False,
    ),
}

# Caption-style presets (ASS) map onto styles for backwards compat.
CAPTION_STYLES = {"Bold": "Podcast", "Minimal": "Minimal Captions", "Neon": "Gaming"}


def get_style(name: str | None) -> Style:
    if not name:
        return STYLES["Podcast"]
    if name in STYLES:
        return STYLES[name]
    # case-insensitive / caption-style alias lookup
    for key, style in STYLES.items():
        if key.lower() == name.lower():
            return style
    if name in CAPTION_STYLES:
        return STYLES[CAPTION_STYLES[name]]
    return STYLES["Podcast"]


def register_style(style: Style) -> None:
    STYLES[style.name] = style


def list_styles() -> list[dict]:
    return [{"name": s.name, "description": s.description} for s in STYLES.values()]
