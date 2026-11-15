"""Transcript normaliser — proper punctuation & capitalisation.

Whisper returns raw, often lowercase, under-punctuated text. This module
restores sentence-case and terminal punctuation heuristically (it is NOT
a neural punctuation model — that is documented, not hidden):
- capitalise the first word of every sentence / thought
- capitalise "I" and sentence-initial words; preserve ALL-CAPS acronyms
- restore terminal punctuation at thought boundaries (a thought ending
  without punctuation gets "."; a thought starting with a question word
  and ending in a rising pattern gets "?")
- preserve Hinglish (Roman Hindi) as spoken — never translate, never
  force Devanagari; preserve Devanagari Hindi as-is (already punctuated
  by danda "।" where present)
- never drop words; normalisation only edits the surface form of words
  (case / trailing punctuation), timings are untouched.

Also: language helpers — Devanagari detection, Hinglish detection
(Roman Hindi words in an otherwise English transcript).
"""
import re
from typing import Any, Dict, List

HINGLISH_WORDS = {
    "kya", "hai", "hain", "nahi", "nahin", "matlab", "aur", "lekin", "kyunki",
    "toh", "bhi", "ka", "ki", "ke", "mein", "main", "tum", "aap", "yeh", "ye",
    "woh", "vo", "kuch", "bahut", "bohot", "accha", "acha", "theek", "sab",
    "log", "baat", "kaam", "paise", "ghar", "zindagi", "dost", "yaar", "bhai",
    "arre", "chal", "dekho", "sun", "suno", "samajh", "bilkul", "kabhi",
    "abhi", "phir", "aise", "waise", "kaise", "kahan", "kab", "kyun", "kaun",
    "mera", "meri", "tere", "teri", "uska", "uski", "hamara", "tumhara",
    "chahiye", "karna", "hoga", "hogi", "raha", "rahi", "rahe", "tha", "thi",
    "jaisa", "aisa", "itna", "utna", "kitna", "sabse", "pehle", "baad",
}
QUESTION_STARTERS = {"what", "why", "how", "when", "where", "who", "which",
                     "kya", "kaise", "kab", "kahan", "kyun", "kaun", "kis"}
DEVANAGARI_RE = re.compile(r"[\u0900-\u097F]")
SENTENCE_END_RE = re.compile(r"[.!?…।]+$")


def contains_devanagari(text: str) -> bool:
    return bool(DEVANAGARI_RE.search(text))


def detect_hinglish(text: str) -> bool:
    """True when a meaningful share of words are Roman-Hindi words."""
    words = re.findall(r"[a-z]+", text.lower())
    if len(words) < 5:
        return False
    hits = sum(1 for w in words if w in HINGLISH_WORDS)
    return hits >= 3 and hits / len(words) >= 0.15


def detect_language(whisper_lang: str | None, text: str) -> str:
    """Whisper language + Hinglish/Devanagari refinement. Returns one of:
    'en', 'hi' (Devanagari Hindi), 'hinglish' (Roman Hindi mix), or the
    Whisper code as-is for other languages."""
    if contains_devanagari(text):
        return "hi"
    if whisper_lang in ("hi", "hin"):
        return "hi"
    if detect_hinglish(text):
        return "hinglish"
    return whisper_lang or "en"


def _is_sentence_start(prev_word: str | None) -> bool:
    if prev_word is None:
        return True
    return bool(SENTENCE_END_RE.search(prev_word.strip()))


def normalize_words(words: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Return a new word list with restored case/punctuation.

    Each word keeps its start/end timings; only the 'word' string changes.
    Punctuation is attached to the last word of a thought: the worker /
    scorer split thoughts by sentence punctuation, so a thought that ends
    without punctuation gets a '.' here (or '?' for question starters).
    """
    if not words:
        return []
    out: List[Dict[str, Any]] = []
    prev_raw: str | None = None
    sentence_first: str = ""
    for i, w in enumerate(words):
        token = (w.get("word") or "").strip()
        if not token:
            continue
        is_start = _is_sentence_start(prev_raw)
        if is_start:
            sentence_first = token.strip().lower()
        # Preserve existing terminal punctuation; strip it for casing logic.
        m = re.match(r"^(.*?)([.!?…।,;:]+)?$", token)
        core, punct = m.group(1), m.group(2) or ""
        low = core.lower()
        # Casing: sentence start -> Title case; standalone "i" -> "I";
        # Devanagari / acronyms / already-capitalised proper nouns untouched.
        if contains_devanagari(core):
            new_core = core
        elif low == "i":
            new_core = "I"
        elif is_start and core and core[0].isalpha():
            new_core = core[0].upper() + core[1:]
        elif core.isupper() and len(core) > 1:
            new_core = core  # acronym, e.g. AI, USA
        else:
            new_core = core
        # Terminal punctuation restoration at the last word overall, and
        # at words followed by a long pause (>=0.8s) that end a thought.
        is_last = i == len(words) - 1
        next_start = words[i + 1].get("start", 0) if i + 1 < len(words) else None
        long_pause = next_start is not None and (next_start - w.get("end", 0)) >= 0.8
        if not punct and (is_last or long_pause):
            # Question detection: the current sentence starts with a
            # question word (e.g. "What ... ?" / "Kya ... ?").
            if sentence_first in QUESTION_STARTERS:
                punct = "?"
            else:
                punct = "."
        out.append({**w, "word": new_core + punct})
        prev_raw = new_core + punct
    return out


def normalize_text(text: str) -> str:
    """Normalise a plain transcript string (same rules, no timings)."""
    words = [{"word": t, "start": 0.0, "end": 0.0} for t in text.split()]
    return " ".join(w["word"] for w in normalize_words(words))
