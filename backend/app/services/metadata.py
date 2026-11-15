"""Auto-generated titles / captions / hashtags / hooks / CTA.

Everything is generated from the clip transcript — the user never has to
write titles, captions or hashtags by hand; editing is optional and the
saved (edited or auto) version is what gets published.
- Titles: hook-first, <=60 chars, 3 variations.
- Captions: 2-3 lines + CTA, 3 variations.
- Hashtags: transcript keywords + niche tags, 8-12.
- Hooks: opening lines, 3+ variations.
- CTA: chosen by clip type (question -> comment, how-to/tip -> save/share,
  story -> follow, default -> follow).
"""
import re
from collections import Counter
from typing import Any, Dict, List

from app.services.text_norm import normalize_text

STOPWORDS = set("""the a an and or but if then so of to in on for with at by from as is are was were be been
it its this that these those you your he she we they i me my our their his her not no do does did will would can could
should have has had just like get got make made very really much more most what why how when where who which
here there all about into over under out up down every only single just day days time times second seconds minute minutes
thing things way ways one two three four five first last new best good great big small many lot kind sort part point
moment video clip reel reels post posting content creator creators audience people person someone anyone everyone
everything nothing something watch watching listen read follow comment share save going comes come know think look
looks start started stop keep keeps take takes put give gives say says tell tells go goes went come came see saw
need needs want wants feel feels find found use used using work works worked try tried also even still already
yet though although because while during before after once twice again back away around
hai hain hoon ho hoga honge kya kyu kyun ka ki ke ko se mein mai main ye yeh wo woh aur par pe pehle
baad bahut sab kuch nahi nahin tha thi hua hui jo jis jin jab tab abhi phir bhi
mera meri mere tera teri tere apna apni apne hum ham tum aap iska iski uska uski inka unka lekin agar
toh to bhi hi na ne tak liye wala wali wale karna karta karti karte hona hota hoti hote gaya gayi
chahiye chahte rahe raha rahi dekhna sunna bolna kar diya""".split())


def _truncate_words(text: str, max_len: int) -> str:
    """Truncate to <= max_len chars without cutting a word in half."""
    if len(text) <= max_len:
        return text
    cut = text[:max_len].rsplit(" ", 1)[0]
    return cut or text[:max_len]

NICHE_TAGS = ["#reels", "#viralreels", "#explorepage", "#fyp", "#reelsinstagram"]


def _keywords(text: str, n: int = 12) -> List[str]:
    words = re.findall(r"[a-z][a-z\-]{2,}", text.lower())
    counts = Counter(w for w in words if w not in STOPWORDS)
    return [w for w, _ in counts.most_common(n)]


def _sentences(text: str) -> List[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?।])\s+", text) if s.strip()]


def choose_cta(text: str) -> str:
    low = text.lower()
    if "?" in text:
        return "Comment your answer below 👇"
    if any(k in low for k in ("how to", "step", "tip", "trick", "secret", "kaise", "tarika")):
        return "Save this for later & share it with someone who needs it 📌"
    if any(k in low for k in ("story", "when i", "once", "remember")):
        return "Follow for more stories like this ❤️"
    return "Follow for more clips like this ❤️"


def clip_type(text: str) -> str:
    low = text.lower()
    if "?" in text:
        return "question"
    if any(k in low for k in ("how to", "step", "tip", "secret")):
        return "how-to"
    if any(k in low for k in ("story", "when i", "once")):
        return "story"
    return "insight"


def generate_metadata(words: List[Dict[str, Any]], start: float, end: float,
                      detected_language: str = "en") -> Dict[str, Any]:
    window = [w for w in words if w.get("start", 0) >= start - 0.05 and w.get("end", 0) <= end + 0.05]
    raw = " ".join(w.get("word", "") for w in window).strip()
    text = normalize_text(raw)  # proper punctuation/capitalisation
    keywords = _keywords(raw)
    sentences = _sentences(text)
    first = sentences[0] if sentences else (text[:57].strip() or "Watch this moment")
    base = _truncate_words(first, 57).strip()
    cta = choose_cta(text)
    ctype = clip_type(text)

    # --- Titles: 3 variations, hook-first, <=60 chars ---
    # v3 uses the clip's second sentence (a real line from the clip), never a
    # bare keyword jammed into a template ("Why three changes everything").
    third = _truncate_words(sentences[1], 57).strip() if len(sentences) > 1 else ""
    if not third or third == base:
        third = _truncate_words(base + " — watch till the end", 60).strip()
    title_variations = []
    for t in [base,
              f"{_truncate_words(base, 38)} — you need to hear this",
              third]:
        t = t[:60].strip()
        if t and t not in title_variations:
            title_variations.append(t)
    while len(title_variations) < 3:
        title_variations.append((f"{base} (part {len(title_variations) + 1})")[:60])

    # --- Captions: 3 variations, 2-3 lines + CTA ---
    hook_line = sentences[0] if sentences else base
    second = sentences[1] if len(sentences) > 1 else "This one hits different."
    caption_variations = [
        f"{hook_line}\n{second}\n{cta}",
        f"{hook_line}\n\n{cta}",
        f"POV: {hook_line.lower()}\n{second}\n{cta}",
    ]

    # --- Hashtags: keywords + niche, 8-12 ---
    tags = [f"#{k.replace('-', '')}" for k in keywords[:8]]
    for t in NICHE_TAGS:
        if len(tags) >= 10:
            break
        if t not in tags:
            tags.append(t)
    tags = tags[:12]
    while len(tags) < 8:
        tags.append(f"#clip{len(tags)}")

    # --- Hooks: 3+ variations (opening lines / questions) ---
    hooks: List[str] = []
    for s in sentences[:3]:
        if s not in hooks:
            hooks.append(s)
    if "?" not in text and first:
        hooks.append(f"What if {first[0].lower() + first[1:]}" if first else "")
    hooks = [h for h in hooks if h][:3]
    while len(hooks) < 3:
        hooks.append(first)

    return {"titles": title_variations, "title": title_variations[0],
            "title_variations": title_variations,
            "caption": caption_variations[0],
            "caption_variations": caption_variations,
            "hashtags": tags, "hooks": hooks,
            "cta": cta, "clip_type": ctype, "keywords": keywords,
            "detected_language": detected_language,
            "normalized_text": text}
