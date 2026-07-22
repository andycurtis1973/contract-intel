#!/usr/bin/env python3
"""Step 1+3: land the contracts and make them askable.

Chunks each contract into clause-sized passages, embeds them with Bedrock
(Titan v2), and indexes them in **S3 Vectors** — object storage with a vector
index, so there's no vector database to stand up or pay for while idle.

Metadata carries the contract id so retrieval can be scoped to one agreement
(for extraction) or left open across the corpus (for "ask your contracts").

    python3 index_clauses.py --contracts ../data/out/contracts.jsonl --limit 25
"""

from __future__ import annotations

import argparse
import json
import re
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import boto3

REGION = "us-east-1"
VB = "contract-intel-vectors"
IDX = "clauses"
EMBED_MODEL = "amazon.titan-embed-text-v2:0"
DIM = 1024
CHUNK, OVERLAP = 1600, 200

br = boto3.client("bedrock-runtime", region_name=REGION)
sv = boto3.client("s3vectors", region_name=REGION)


def embed(text: str, retries: int = 5) -> list[float]:
    for i in range(retries):
        try:
            r = br.invoke_model(modelId=EMBED_MODEL, body=json.dumps(
                {"inputText": text[:8000], "dimensions": DIM, "normalize": True}))
            return json.loads(r["body"].read())["embedding"]
        except Exception as e:
            if i == retries - 1:
                raise
            time.sleep(1.5 * (2 ** i))
    raise RuntimeError("unreachable")


def chunk(text: str) -> list[str]:
    """Split on paragraph-ish boundaries, then pack to ~CHUNK chars with overlap."""
    parts = re.split(r"\n\s*\n", text)
    out, cur = [], ""
    for p in parts:
        p = p.strip()
        if not p:
            continue
        if len(cur) + len(p) + 2 <= CHUNK:
            cur = f"{cur}\n\n{p}" if cur else p
        else:
            if cur:
                out.append(cur)
            cur = (cur[-OVERLAP:] + "\n\n" + p) if cur else p
            while len(cur) > CHUNK:                 # a single huge paragraph
                out.append(cur[:CHUNK]); cur = cur[CHUNK - OVERLAP:]
    if cur:
        out.append(cur)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--contracts", default="../data/out/contracts.jsonl")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--workers", type=int, default=16)
    a = ap.parse_args()

    rows = [json.loads(l) for l in Path(a.contracts).read_text().splitlines()]
    if a.limit:
        rows = rows[:a.limit]
    print(f"  {len(rows)} contracts -> chunking", flush=True)

    jobs = []
    for r in rows:
        for i, c in enumerate(chunk(r["text"])):
            jobs.append({"key": f"{abs(hash(r['id'])) % (10**12)}-{i}",
                         "contract": r["id"], "i": i, "text": c})
    print(f"  {len(jobs):,} chunks (avg {len(jobs)/len(rows):.0f}/contract)", flush=True)

    t0 = time.time()
    done = [0]

    def work(j):
        j["vec"] = embed(j["text"])
        done[0] += 1
        if done[0] % 500 == 0:
            print(f"    embedded {done[0]:,}/{len(jobs):,}  ({time.time()-t0:.0f}s)", flush=True)
        return j

    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        jobs = list(ex.map(work, jobs))
    print(f"  embedded in {time.time()-t0:.0f}s", flush=True)

    # S3 Vectors accepts batches; keep them modest so payloads stay small
    B = 100
    for i in range(0, len(jobs), B):
        batch = [{"key": j["key"], "data": {"float32": j["vec"]},
                  "metadata": {"contract": j["contract"], "i": j["i"],
                               "text": j["text"][:2000]}}
                 for j in jobs[i:i + B]]
        sv.put_vectors(vectorBucketName=VB, indexName=IDX, vectors=batch)
        if (i // B) % 10 == 0:
            print(f"    indexed {min(i+B, len(jobs)):,}/{len(jobs):,}", flush=True)

    print(f"\n  indexed {len(jobs):,} chunks from {len(rows)} contracts "
          f"into s3vectors://{VB}/{IDX}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
