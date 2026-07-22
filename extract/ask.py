#!/usr/bin/env python3
"""Step 3: ask the whole contract estate a question.

This is the part that needs a vector index rather than a spreadsheet: nobody
writes "auto-renewal" in a searchable field, they write two paragraphs of legal
prose, and the words differ in every agreement. Semantic search finds the clause
by meaning.

The point about S3 Vectors is not that it is faster — it is that there is no
vector database to stand up, secure, and pay for while idle. The index lives in
object storage next to the documents.

    python3 ask.py "which contracts renew themselves with barely any warning?"
    python3 ask.py --canned   # run the questions used in the demo
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import boto3

REGION = "us-east-1"
VB, IDX = "contract-intel-vectors", "clauses"
EMBED = "amazon.titan-embed-text-v2:0"

CANNED = [
    "the agreement renews automatically unless we give written notice",
    "liability is capped at the fees paid in the previous twelve months",
    "we must purchase a minimum quantity every year whether we need it or not",
    "we can walk away for convenience on short notice",
    "exclusive supply — we are barred from buying elsewhere",
]

br = boto3.client("bedrock-runtime", region_name=REGION)
sv = boto3.client("s3vectors", region_name=REGION)


def embed(t: str) -> list[float]:
    r = br.invoke_model(modelId=EMBED, body=json.dumps(
        {"inputText": t[:8000], "dimensions": 1024, "normalize": True}))
    return json.loads(r["body"].read())["embedding"]


def ask(q: str, k: int = 5) -> dict:
    t0 = time.time()
    r = sv.query_vectors(vectorBucketName=VB, indexName=IDX, topK=k,
                         queryVector={"float32": embed(q)},
                         returnMetadata=True, returnDistance=True)
    ms = (time.time() - t0) * 1000
    hits = [{"contract": v["metadata"]["contract"],
             "distance": round(v["distance"], 4),
             "text": " ".join(v["metadata"].get("text", "").split())[:280]}
            for v in r["vectors"]]
    return {"question": q, "latency_ms": round(ms), "hits": hits}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("q", nargs="*")
    ap.add_argument("--canned", action="store_true")
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--out", default="../results/search_examples.json")
    a = ap.parse_args()

    qs = CANNED if a.canned or not a.q else [" ".join(a.q)]
    out = []
    for q in qs:
        r = ask(q, a.k)
        out.append(r)
        print(f"\n  Q: {q}")
        print(f"     ({r['latency_ms']} ms across the whole estate)")
        for h in r["hits"][:3]:
            print(f"     · {h['contract'][:46]:48s} d={h['distance']}")
            print(f"       \"{h['text'][:150]}...\"")
    if a.canned:
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        Path(a.out).write_text(json.dumps(out, indent=1))
        print(f"\n  -> {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
