"""Context-aware highlight detection.

NOT keyword/loudness/scene-change-only selection. Uses the full transcript:
- segment by topic shifts / speaker turns / complete thought arcs
- score a candidate by conversational context (setup -> payoff,
  question -> answer, story arc)
- expand the window 2-5s before the hook where needed so the setup is kept
- never splice non-adjacent segments: candidates are always contiguous windows

Inputs are word dicts: {"word": str, "start": float, "end": float}.
A "thought" is a run of words ending at sentence punctuation (. ! ? ...)
or a long pause (>= 0.8s) that also ends a clause.
"""
import re
from typing import Any, Dict, List, Tuple

SENTENCE_END = re.compile(r"[.!?…]+$")
QUESTION = re.compile(r"\?\s*$")
SETUP_MARKERS = {
    "so", "basically", "here's", "here is", "the thing is", "look", "listen",
    "imagine", "for example", "the problem", "the reason", "because",
    "what if", "remember", "let me tell", "let me explain",
}
PAYOFF_MARKERS = {
    "that's why", "that's how", "the answer", "turns out", "in the end",
    "so we", "that's the", "the secret", "here's the", "the key",
}
QUESTION_WORDS = {"what", "why", "how", "when", "where", "who", "which", "can", "should", "is", "do", "does"}


def words_to_text(words: List[Dict[str, Any]]) -> str:
    return " ".join(w.get("word", "") for w in words).strip()


def split_thoughts(words: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Split word stream into complete thought arcs.

    Each thought: {"words": [...], "start": float, "end": float, "text": str,
    "complete": bool} — complete = ends on sentence punctuation.
    """
    thoughts: List[Dict[str, Any]] = []
    cur: List[Dict[str, Any]] = []
    for i, w in enumerate(words):
        cur.append(w)
        is_last = i == len(words) - 1
        ends_sentence = bool(SENTENCE_END.search(w.get("word", "").strip()))
        long_pause = False
        if not is_last:
            nxt = words[i + 1]
            long_pause = (nxt.get("start", 0) - w.get("end", 0)) >= 0.8
        if ends_sentence or is_last or (long_pause and len(cur) >= 4):
            thoughts.append({
                "words": list(cur),
                "start": cur[0].get("start", 0.0),
                "end": cur[-1].get("end", 0.0),
                "text": words_to_text(cur),
                "complete": ends_sentence or is_last,
            })
            cur = []
    if cur:
        thoughts.append({
            "words": list(cur),
            "start": cur[0].get("start", 0.0),
            "end": cur[-1].get("end", 0.0),
            "text": words_to_text(cur),
            "complete": False,
        })
    return thoughts


def segment_topics(thoughts: List[Dict[str, Any]], max_gap_s: float = 6.0) -> List[Dict[str, Any]]:
    """Group thoughts into topic segments.

    A new topic starts on a long inter-thought gap, an explicit setup marker
    after a completed arc, or a question that opens a new Q->A exchange.
    This is a lightweight lexical heuristic (v1); a later embedding-based
    segmenter can replace this function behind the same return shape.
    """
    segments: List[Dict[str, Any]] = []
    cur: List[Dict[str, Any]] = []
    for t in thoughts:
        start_new = False
        if cur:
            prev = cur[-1]
            gap = t["start"] - prev["end"]
            low = t["text"].lower()
            if gap >= max_gap_s:
                start_new = True
            elif any(low.startswith(m) or f" {m} " in f" {low} " for m in SETUP_MARKERS) and prev["complete"]:
                start_new = True
            elif t["text"].strip().endswith("?") and prev["complete"]:
                start_new = True
        if start_new:
            segments.append({"thoughts": cur, "start": cur[0]["start"], "end": cur[-1]["end"]})
            cur = []
        cur.append(t)
    if cur:
        segments.append({"thoughts": cur, "start": cur[0]["start"], "end": cur[-1]["end"]})
    return segments


def thought_completeness(words: List[Dict[str, Any]], start: float, end: float) -> Tuple[bool, str]:
    """Does the window [start, end] begin/end on thought boundaries?"""
    window = [w for w in words if w.get("start", 0) >= start - 0.05 and w.get("end", 0) <= end + 0.05]
    if not window:
        return False, "no speech in window"
    thoughts = split_thoughts(window)
    first, last = thoughts[0], thoughts[-1]
    starts_clean = first["start"] <= start + 0.3
    ends_complete = last["complete"]
    if starts_clean and ends_complete:
        return True, "starts and ends on complete thought boundaries"
    if not ends_complete:
        return False, "ends mid-sentence / mid-thought"
    return False, "starts mid-thought"


def expand_for_context(words: List[Dict[str, Any]], start: float, end: float,
                       max_pre_s: float = 5.0) -> Tuple[float, float, str]:
    """Prepend 2-5s of setup context before the hook when the hook's thought
    began earlier (e.g. a question/setup sentence immediately before it).
    Returns (new_start, end, reason). Never moves start backwards past 0 or
    into a previous unrelated topic by more than max_pre_s.
    """
    thoughts = split_thoughts(words)
    # thought containing (or just before) start
    idx = None
    for i, t in enumerate(thoughts):
        if t["start"] <= start + 0.3 <= t["end"] + 0.5 or (t["end"] <= start + 0.3 and (idx is None or t["end"] > thoughts[idx]["end"])):
            idx = i
    if idx is None:
        return start, end, "no preceding thought found"
    t = thoughts[idx]
    # If hook starts mid-thought, pull start back to that thought's start.
    if t["start"] < start - 0.3:
        back = min(start - t["start"], max_pre_s)
        new_start = max(0.0, start - back)
        return new_start, end, f"expanded {back:.1f}s back to include setup: '{t['text'][:80]}'"
    # If the previous thought is a question/setup for this one, include it too.
    if idx > 0:
        prev = thoughts[idx - 1]
        low = prev["text"].lower()
        is_setup = prev["text"].strip().endswith("?") or any(m in low for m in SETUP_MARKERS)
        gap = t["start"] - prev["end"]
        if is_setup and gap <= 3.0 and (start - prev["start"]) <= max_pre_s + 2.0:
            new_start = max(0.0, prev["start"])
            return new_start, end, f"expanded to include setup/question: '{prev['text'][:80]}'"
    return start, end, "hook already starts on a thought boundary"


def context_score(words: List[Dict[str, Any]], start: float, end: float) -> Dict[str, Any]:
    """0-10 context score + reason. Rewards setup->payoff / Q->A / complete arc
    inside one contiguous window; penalises mid-thought cuts."""
    window = [w for w in words if w.get("start", 0) >= start - 0.05 and w.get("end", 0) <= end + 0.05]
    text = words_to_text(window).lower()
    thoughts = split_thoughts(window)
    complete, why = thought_completeness(words, start, end)
    score = 5.0
    reasons = []
    if complete:
        score += 2.0
        reasons.append("complete thought arc inside window")
    else:
        score -= 3.0
        reasons.append(f"incomplete arc: {why}")
    has_q = "?" in text
    has_a = any(m in text for m in PAYOFF_MARKERS)
    if has_q and len(thoughts) >= 2:
        score += 1.5
        reasons.append("question -> answer structure")
    if has_a:
        score += 1.0
        reasons.append("payoff / answer present")
    if any(m in text for m in SETUP_MARKERS):
        score += 0.5
        reasons.append("setup context present")
    if len(thoughts) >= 3:
        score += 0.5
        reasons.append("multi-thought story arc")
    score = max(0.0, min(10.0, score))
    return {"score": round(score, 1), "complete": complete, "reasons": reasons,
            "thoughts": len(thoughts), "context_preserved": complete}
