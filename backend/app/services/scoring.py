"""Explainable viral scoring (/100) + quality gate.

Factors (ARCHITECTURE.md §4):
  Hook 25, Retention 20, Interestingness 15, Emotional 15,
  Story completion 10, Shareability 10, Replay 5.

Context-aware: scoring consumes the context module — a candidate is scored
on conversational context (setup->payoff, Q->A, complete thought arc), not
on keywords/loudness/scene changes alone. See services/context.py.

QUALITY GATE (hard requirement, overrides quantity):
  A clip passes only if ALL hold:
  - total score >= 55
  - hook factor >= 12/25
  - story completion >= 5/10
  - strong opening hook in first 3s
  - complete thought/sentence arc (no mid-sentence cuts)
  - speech density high / no unnecessary silence
  - word-level synced subtitles available (words present)
  - face/speaker-centred framing available OR centre fallback is acceptable
    (recorded as a failure only when no face AND no usable framing — here
    centre fallback counts as passable; face presence boosts hook)
  - no misleading splicing: contiguous window only (enforced upstream;
    this module refuses non-contiguous candidates)
  Clips below the gate must NOT be rendered/published as final clips.
"""
import re
from typing import Any, Dict, List

from app.services.context import context_score, thought_completeness, words_to_text

HOOK_WORDS = {"what", "why", "how", "secret", "never", "always", "stop", "mistake",
              "truth", "amazing", "insane", "crazy", "free", "best", "worst", "nobody",
              "everyone", "imagine", "wait", "look", "listen", "here's", "watch"}
EMOTION_WORDS = {"love", "hate", "amazing", "terrible", "incredible", "shocking",
                 "unbelievable", "brilliant", "awful", "beautiful", "scary", "funny",
                 "laugh", "wow", "oh", "damn", "hell"}
SHARE_WORDS = {"share", "send this", "tag", "follow", "subscribe", "comment",
               "you need", "everyone should", "must watch", "save this"}
NOVELTY_WORDS = {"new", "first", "never before", "secret", "hidden", "nobody knows",
                 "actually", "really", "surprising", "different", "change"}

MIN_TOTAL = 55
MIN_HOOK = 12
MIN_STORY = 5


def _density(words, start, end):
    w = [x for x in words if start <= x.get("start", 0) < end]
    dur = max(end - start, 0.1)
    spoken = sum(max(0.0, min(x.get("end", 0), end) - max(x.get("start", 0), start)) for x in w)
    return spoken / dur, len(w)


def score_candidate(words: List[Dict[str, Any]], start: float, end: float,
                    silence_intervals: List[Dict[str, float]] = None,
                    scene_changes: int = 0, has_face: bool = False,
                    contiguous: bool = True) -> Dict[str, Any]:
    """Score one contiguous candidate window. Returns dict with total,
    breakdown {factor: {score, max, reason}}, quality_gate_passed,
    quality_gate_failures, context info."""
    silence_intervals = silence_intervals or []
    window_words = [w for w in words if w.get("start", 0) >= start - 0.05 and w.get("end", 0) <= end + 0.05]
    text = words_to_text(window_words)
    low = text.lower()
    first3 = words_to_text([w for w in window_words if w.get("start", 0) < start + 3.0])
    first3_low = first3.lower()
    density, n_words = _density(words, start, end)
    dur = end - start
    silence_in = sum(max(0.0, min(s.get("end", 0), end) - max(s.get("start", 0), start))
                     for s in silence_intervals)
    silence_ratio = silence_in / max(dur, 0.1)
    ctx = context_score(words, start, end)
    complete, complete_why = thought_completeness(words, start, end)

    breakdown: Dict[str, Dict[str, Any]] = {}

    # Hook (25): question/surprise/strong claim/emotion word in first 3s + face.
    hook = 8.0
    hook_reasons = []
    if any(k in first3_low for k in HOOK_WORDS):
        hook += 7; hook_reasons.append("hook word/question in first 3s")
    if "?" in first3:
        hook += 4; hook_reasons.append("opens with a question")
    if any(k in first3_low for k in EMOTION_WORDS):
        hook += 3; hook_reasons.append("emotion word in first 3s")
    if has_face:
        hook += 3; hook_reasons.append("face on screen at open")
    hook = min(25.0, hook)
    breakdown["hook"] = {"score": round(hook, 1), "max": 25,
                         "reason": "; ".join(hook_reasons) or "weak opening — no hook word, question or face in first 3s"}

    # Retention (20): speech density, no long silence, scene changes, continuity.
    retention = 6.0 + min(8.0, density * 8.0)
    if silence_ratio < 0.1:
        retention += 3
    elif silence_ratio > 0.3:
        retention -= 4
    retention += min(3.0, scene_changes * 0.5)
    retention = max(0.0, min(20.0, retention))
    breakdown["retention"] = {"score": round(retention, 1), "max": 20,
                              "reason": f"speech density {density:.2f}, silence {silence_ratio:.0%}, {scene_changes} scene changes"}

    # Interestingness (15): novelty keywords, named entities (capitalised), contrast.
    interesting = 6.0
    if any(k in low for k in NOVELTY_WORDS):
        interesting += 4
    caps = len(re.findall(r"\b[A-Z][a-z]{2,}\b", text))
    if caps >= 2:
        interesting += 3
    if " but " in low or " however " in low:
        interesting += 2
    breakdown["interestingness"] = {"score": round(min(15.0, interesting), 1), "max": 15,
                                    "reason": "novelty/contrast/named-entity signals in transcript"}

    # Emotional (15): sentiment lexicon, exclamation, laughter.
    emotional = 5.0
    hits = sum(1 for k in EMOTION_WORDS if k in low)
    emotional += min(6.0, hits * 2.0)
    if "!" in text:
        emotional += 2
    if "ha" in low or "laugh" in low:
        emotional += 2
    breakdown["emotional"] = {"score": round(min(15.0, emotional), 1), "max": 15,
                              "reason": f"{hits} emotion words, exclamation={'yes' if '!' in text else 'no'}"}

    # Story completion (10): context-aware — complete thought arc.
    story = ctx["score"]  # 0-10 from context module
    breakdown["story_completion"] = {"score": round(story, 1), "max": 10,
                                     "reason": "; ".join(ctx["reasons"]) or complete_why}

    # Shareability (10): quotable line, relatable, CTA language.
    share = 4.0
    if any(k in low for k in SHARE_WORDS):
        share += 3
    if 8 <= len(text.split()) <= 60 and any(k in low for k in ("you", "your")):
        share += 3
    breakdown["shareability"] = {"score": round(min(10.0, share), 1), "max": 10,
                                 "reason": "quotable / relatable / CTA language" if share > 4 else "no clear quotable or share trigger"}

    # Replay (5): dense punchline, fast payoff, loop-friendly ending.
    replay = 2.0
    if text.strip().endswith(("!", "?", ".")) and n_words >= 20:
        replay += 2
    if density > 0.7:
        replay += 1
    breakdown["replay"] = {"score": round(min(5.0, replay), 1), "max": 5,
                           "reason": "dense payoff / loop-friendly ending" if replay >= 4 else "moderate replay value"}

    total = round(sum(v["score"] for v in breakdown.values()), 1)

    failures: List[str] = []
    if total < MIN_TOTAL:
        failures.append(f"total score {total} < {MIN_TOTAL}")
    if hook < MIN_HOOK:
        failures.append(f"hook {hook}/25 < {MIN_HOOK}")
    if story < MIN_STORY:
        failures.append(f"story completion {story}/10 < {MIN_STORY}")
    if not complete:
        failures.append(f"incomplete thought arc: {complete_why}")
    if density < 0.4:
        failures.append(f"speech density {density:.2f} too low (silence-heavy)")
    if silence_ratio > 0.35:
        failures.append(f"too much silence in window ({silence_ratio:.0%})")
    if not window_words:
        failures.append("no word-level subtitles available (no transcript words)")
    if not contiguous:
        failures.append("non-contiguous / spliced window — misleading cut")
    if dur > 90:
        failures.append("clip longer than 90s Reels limit")
    if dur < 15:
        failures.append("clip shorter than 15s")

    return {
        "score": total,
        "score_breakdown": breakdown,
        "quality_gate_passed": len(failures) == 0,
        "quality_gate_failures": failures,
        "context_preserved": ctx["context_preserved"],
        "context_reason": "; ".join(ctx["reasons"]) or complete_why,
        "speech_density": round(density, 2),
        "silence_ratio": round(silence_ratio, 2),
    }


def rank_candidates(candidates: List[Dict[str, Any]], max_clips: int = 5) -> List[Dict[str, Any]]:
    """Keep only gate-passing candidates, ranked by score, max `max_clips`.
    Quality over quantity: returns 0..max_clips, never pads with weak clips."""
    passing = [c for c in candidates if c.get("quality_gate_passed")]
    passing.sort(key=lambda c: c.get("score", 0), reverse=True)
    return passing[:max(1, min(max_clips, 5))]
