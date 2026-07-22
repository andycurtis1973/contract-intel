#!/usr/bin/env python3
"""Runs ON the GPU worker — narration via the EXACT nscale learning-video path.

No post-processing: this calls worker.generate_segment_audio unchanged
(F5-TTS, remove_silence=True, stock male reference via speaker="expert"). Same
function that produces the clean learning videos. Visual assembly + a single
continuous audio mux happen locally (assemble_local.py).
"""

import json
import os
import sys
import tempfile
from pathlib import Path

import boto3

sys.path.insert(0, "/home/ubuntu")
os.environ.setdefault("F5_VOICE_DIR", "/opt/voices")
from worker import generate_segment_audio  # nscale-exact F5-TTS

INP = Path(os.environ.get("CK_INPUTS", "/home/ubuntu/ck_inputs"))
BUCKET = os.environ["CK_BUCKET"]
PREFIX = os.environ.get("CK_PREFIX", "cache-is-king")
s3 = boto3.client("s3")

script = json.loads((INP / "script.json").read_text())
for i, seg in enumerate(script["segments"]):
    with tempfile.TemporaryDirectory() as td:
        print(f"=== segment {i} ({seg['name']}) ===", flush=True)
        wav = generate_segment_audio(seg["dialogue"], Path(td), i)
        key = f"{PREFIX}/audio/seg_{i:02d}.wav"
        s3.upload_file(wav, BUCKET, key)
        print(f"  uploaded {key}", flush=True)
print("AUDIO DONE", flush=True)
