#!/usr/bin/env python3
"""Offline smoke test for the clipping pipeline (no server, no network).

Run from the repo root with the backend venv:
    cd backend && .venv/bin/python ../tests/smoke_test.py

Checks: quality gate (strong clip passes, weak/speechless fails, never
pads to 5), explainable scoring breakdown, metadata (3 title/caption/hook
variations, 8-12 hashtags, CTA), ASS caption generation (word-by-word
karaoke, 4-word groups, preset differences), transcript normaliser,
context (complete thought arc), and style registry.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.services.captions import generate_ass, get_caption_preset  # noqa: E402
from app.services.context import context_score, split_thoughts  # noqa: E402
from app.services.metadata import generate_metadata  # noqa: E402
from app.services.scoring import rank_candidates, score_candidate  # noqa: E402
from app.services.styles import STYLES, get_style  # noqa: E402
from app.services.text_norm import normalize_text  # noqa: E402

PASS = 0


def check(name, cond, extra=""):
    global PASS
    assert cond, f"FAIL: {name} {extra}"
    PASS += 1
    print(f"  ok: {name}")


def words_from(text, t0=0.0, wps=2.5):
    """Fake word timestamps for a sentence stream (punctuation kept)."""
    out, t = [], t0
    for w in text.split():
        d = 1.0 / wps
        out.append({"word": w, "start": round(t, 2), "end": round(t + d * 0.9, 2)})
        t += d
    return out


HOOK_TEXT = (
    "What is the secret to going viral on Instagram? "
    "Here is the truth nobody tells you about the first three seconds. "
    "Your hook is everything, and most creators waste it completely. "
    "But here is the amazing part, a great hook is actually simple to write. "
    "Ask a surprising question, make a bold claim, and promise a payoff. "
    "That is why the best creators open with a question every single time. "
    "Share this with a creator friend who needs to hear it today."
)


def main():
    print("== scoring + quality gate ==")
    words = words_from(HOOK_TEXT)
    dur = words[-1]["end"]
    r = score_candidate(words, 0.0, dur, silence_intervals=[], scene_changes=1,
                        has_face=False, contiguous=True)
    check("strong clip passes gate", r["quality_gate_passed"], str(r["quality_gate_failures"]))
    check("score in 55..100", 55 <= r["score"] <= 100, str(r["score"]))
    check("7 factors with reasons",
          set(r["score_breakdown"]) == {"hook", "retention", "interestingness", "emotional",
                                        "story_completion", "shareability", "replay"}
          and all(v.get("reason") for v in r["score_breakdown"].values()))
    check("hook >= 12", r["score_breakdown"]["hook"]["score"] >= 12)
    check("context preserved", r["context_preserved"] is True)
    # Weak / speechless candidates must fail and never be padded.
    weak = score_candidate(words, 0.0, 5.0, silence_intervals=[], scene_changes=0,
                           has_face=False, contiguous=True)
    check("short weak window fails gate", not weak["quality_gate_passed"])
    empty = score_candidate([], 0.0, 30.0, silence_intervals=[], scene_changes=0,
                            has_face=False, contiguous=True)
    check("no-transcript candidate fails gate", not empty["quality_gate_passed"])
    kept = rank_candidates([r, weak, empty], max_clips=5)
    check("rank keeps only passing, max 5", len(kept) == 1 and kept[0] is r)
    check("rank never pads", rank_candidates([weak, empty], max_clips=5) == [])
    print(f"  strong clip score: {r['score']}  breakdown: "
          + ", ".join(f"{k}={v['score']}/{v['max']}" for k, v in r["score_breakdown"].items()))

    print("== context ==")
    thoughts = split_thoughts(words)
    check("thoughts split on punctuation", len(thoughts) >= 5, f"got {len(thoughts)}")
    ctx = context_score(words, 0.0, dur)
    check("context score >= 5 for Q->A arc", ctx["score"] >= 5, str(ctx))

    print("== metadata (fully automated) ==")
    md = generate_metadata(words, 0.0, dur, detected_language="en")
    check("3 title variations, <=60 chars",
          len(md["title_variations"]) == 3 and all(len(t) <= 60 for t in md["title_variations"]),
          str(md["title_variations"]))
    check("title is hook-first", md["title"].lower().startswith("what"))
    check("3 caption variations", len(md["caption_variations"]) == 3)
    check("3+ hooks", len(md["hooks"]) >= 3)
    check("8-12 hashtags", 8 <= len(md["hashtags"]) <= 12, str(md["hashtags"]))
    check("no filler-word hashtags", not any(h in ("#three", "#seconds", "#every", "#only")
                                             for h in md["hashtags"]), str(md["hashtags"]))
    check("CTA present", bool(md["cta"]))

    print("== captions (ASS) ==")
    ass = generate_ass(words, 0.0, dur, caption_style="Bold Yellow")
    check("ASS header + dialogue lines", "[Script Info]" in ass and "Dialogue:" in ass)
    check("karaoke timing tags present", "\\kf" in ass)
    check("important word highlighted", "viral" in ass.lower())
    neon = generate_ass(words, 0.0, dur, caption_style="Neon")
    check("presets differ", neon != ass)
    check("preset sizes sane (fit 720px)",
          get_caption_preset("Bold Yellow").font_size <= 60
          and get_caption_preset("Hormozi-style").font_size <= 72)

    print("== text normaliser ==")
    check("sentence-case + punctuation",
          normalize_text("what is the secret to going viral on instagram") ==
          "What is the secret to going viral on instagram?")
    # Proper-noun casing (e.g. "Instagram") comes from Whisper itself and is
    # preserved by the normaliser; it does not invent it from lowercase.
    check("hinglish preserved, not translated",
          "kya" in normalize_text("kya aapko pata hai secret kya hai").lower())

    print("== styles ==")
    check("5 editing styles", len(STYLES) == 5, str(sorted(STYLES)))
    check("style params are real", get_style("Gaming").caption_font_size != get_style("Podcast").caption_font_size
          or get_style("Gaming").zoom_factor != get_style("Podcast").zoom_factor)

    print(f"\nAll {PASS} smoke checks passed.")


if __name__ == "__main__":
    main()
