#!/usr/bin/env python3
"""Render the static slides + write the narration script (sentence-split, male voice).

Static slides become held frames; animated segments render their frames at assembly
time. Each sentence is its own line — F5-TTS is markedly more stable that way.
"""

import json
from pathlib import Path

import render

ASSETS = Path(__file__).resolve().parent / "assets"
ASSETS.mkdir(parents=True, exist_ok=True)

segments = []
for seg in render.SEGMENTS:
    if seg["kind"] == "static":
        seg["build"]().save(ASSETS / f"{seg['name']}.png")
    segments.append({"name": seg["name"], "kind": seg["kind"],
                     "dialogue": [{"speaker": "expert", "text": s} for s in seg["vo"]]})

(ASSETS / "script.json").write_text(json.dumps({"segments": segments}, indent=2))
n_static = sum(1 for s in render.SEGMENTS if s["kind"] == "static")
words = sum(len(t["text"].split()) for s in segments for t in s["dialogue"])
print(f"  {n_static} static slides + script.json ({len(segments)} segments, "
      f"{words} words ≈ {words/2.6:.0f}s narration)")
