#!/usr/bin/env python3
"""Assemble the final video locally — SINGLE continuous audio track.

Build the visuals as silent per-segment clips (each held to its narration
length), concatenate them into one silent video, concatenate the narration wavs
into one continuous audio track, and mux ONCE. This avoids per-segment audio
stitching (the boundary glitches / "skipping"), matching how the nscale learning
videos carry a single clean audio stream.

    python3 assemble_local.py   # -> video/out/cache_is_king_demo.mp4
"""

import json
import math
import subprocess
import sys
import tempfile
from pathlib import Path

import render

HERE = Path(__file__).resolve().parent
ASSETS = HERE / "assets"
AUDIO = HERE / "audio"
OUT = HERE / "out"
OUT.mkdir(exist_ok=True)
FPS = 24


def duration(p: Path) -> float:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "default=noprint_wrappers=1:nokey=1", str(p)],
                       capture_output=True, text=True)
    return float(r.stdout.strip())


def silent_static(png: Path, dur: float, out: Path):
    subprocess.run(
        ["ffmpeg", "-y", "-loop", "1", "-i", str(png), "-t", f"{dur:.3f}",
         "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", str(FPS),
         "-vf", f"scale={render.W}:{render.H}", "-an", str(out)],
        check=True, capture_output=True)


def silent_anim(build, dur: float, out: Path, td: Path):
    n = max(2, math.ceil(dur * FPS))
    fdir = td / out.stem
    fdir.mkdir()
    for i in range(n):
        build(i / (n - 1)).save(fdir / f"{i:05d}.png")
    subprocess.run(
        ["ffmpeg", "-y", "-framerate", str(FPS), "-i", str(fdir / "%05d.png"),
         "-t", f"{dur:.3f}", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", str(FPS),
         "-an", str(out)],
        check=True, capture_output=True)


def main() -> int:
    script = json.loads((ASSETS / "script.json").read_text())
    spec = {s["name"]: s for s in render.SEGMENTS}
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        vclips, wavs = [], []
        for i, seg in enumerate(script["segments"]):
            name = seg["name"]
            wav = AUDIO / f"seg_{i:02d}.wav"
            if not wav.exists():
                print(f"  MISSING {wav}"); return 1
            dur = duration(wav)
            vclip = td / f"v_{i:02d}.mp4"
            print(f"  [{i}] {name:12} {dur:5.1f}s ({seg['kind']})")
            if seg["kind"] == "anim":
                silent_anim(spec[name]["build"], dur, vclip, td)
            else:
                silent_static(ASSETS / f"{name}.png", dur, vclip)
            vclips.append(vclip)
            wavs.append(wav)

        # 1) one silent video
        vlist = td / "v.txt"
        vlist.write_text("\n".join(f"file '{c}'" for c in vclips))
        silent = td / "silent.mp4"
        subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(vlist),
                        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", str(FPS), "-an",
                        str(silent)], check=True, capture_output=True)

        # 2) one continuous audio track
        alist = td / "a.txt"
        alist.write_text("\n".join(f"file '{w}'" for w in wavs))
        full_audio = td / "audio.wav"
        subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(alist),
                        "-ar", "44100", "-ac", "2", str(full_audio)],
                       check=True, capture_output=True)

        # 3) mux ONCE
        final = OUT / "contract_intel_demo.mp4"
        subprocess.run(["ffmpeg", "-y", "-i", str(silent), "-i", str(full_audio),
                        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest",
                        str(final)], check=True, capture_output=True)
    total = duration(final)
    print(f"\n  ✅ {final}  ({total:.0f}s, {total/60:.1f} min)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
