#!/usr/bin/env python3
"""Step 2: read the contracts and pull out the obligations that cost money.

For each contract we retrieve only the passages that look like renewal /
termination / liability language (via S3 Vectors, scoped to that contract), then
ask Bedrock to extract structured obligations from those passages.

Retrieval matters for more than cost: a 52,000-character contract is mostly
boilerplate, and handing the model just the relevant clauses keeps it honest.

Answers are graded against CUAD's lawyer annotations, so the accuracy numbers are
real rather than vibes.

    python3 extract_obligations.py --limit 25 --out ../results/extracted_slice.json
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
VB, IDX = "contract-intel-vectors", "clauses"
EMBED_MODEL = "amazon.titan-embed-text-v2:0"
# NOTE: newer Claude models on Bedrock are only invocable through a cross-region
# INFERENCE PROFILE — the bare "anthropic.…" id throws ValidationException
# ("on-demand throughput isn't supported"). The "us." prefix is the profile.
CHAT_MODEL = "us.anthropic.claude-haiku-4-5-20251001-v1:0"

# what to go looking for, in the language contracts actually use
PROBES = {
    "renewal": "automatically renew successive renewal terms extend for additional periods",
    "notice": "written notice of non-renewal prior to the end of the term days before expiration",
    "expiry": "term of this agreement shall commence and expire termination date",
    "convenience": "terminate this agreement for convenience without cause upon written notice",
    "liability": "limitation of liability shall not exceed aggregate liability capped",
    "minimum": "minimum purchase commitment shall purchase at least minimum quantity",
}

SYSTEM = """You extract contractual obligations for a finance team. You are precise and \
conservative: if the contract does not clearly state something, you return null. You never \
guess and never infer from silence. Quote the contract verbatim as evidence."""

SCHEMA = """Return ONLY a JSON object, no prose, with exactly these keys:
{
 "auto_renews": true | false | null,          // does the term renew automatically?
 "renewal_term": string | null,               // e.g. "one (1) year"
 "notice_days": integer | null,               // see the NOTICE RULE below
 "notice_quote": string | null,               // verbatim sentence stating that notice
 "expiration": string | null,                 // stated end/expiry of the initial term
 "termination_for_convenience": true|false|null,
 "liability_cap": string | null,              // e.g. "fees paid in the prior 12 months"
 "minimum_commitment": string | null
}

NOTICE RULE — this one is easy to get wrong, so read carefully.
"notice_days" means ONLY: the advance notice a party must give to STOP the term
renewing automatically (i.e. notice of non-renewal, given before the end of the
current term). It is null unless the contract renews automatically.
Do NOT put any of these in notice_days:
  - notice to terminate for cause or for breach
  - notice to terminate for convenience mid-term
  - a cure period, or notice of an alleged default
  - notice for any other purpose (assignment, price change, address)
If the contract does not auto-renew, notice_days MUST be null.

CAP RULE — "liability_cap" is a stated ceiling on liability (a sum, or a formula
such as "fees paid in the preceding 12 months"). A mere disclaimer of
consequential/indirect damages is NOT a cap; return null for that alone.

UNITS — read this literally, it is the most common mistake:
"notice_days" is expressed in DAYS.
  - contract says a number of DAYS   -> use that number UNCHANGED. "60 days" -> 60
  - contract says MONTHS             -> multiply by 30.  "3 months" -> 90
  - contract says YEARS              -> multiply by 365. "1 year"   -> 365
NEVER multiply a value that is already stated in days. "90 days" is 90, not 2700.

Rules: null when absent. Never infer from silence."""


class Ex:
    def __init__(self):
        self.br = boto3.client("bedrock-runtime", region_name=REGION)
        self.sv = boto3.client("s3vectors", region_name=REGION)

    def embed(self, t: str) -> list[float]:
        for i in range(5):
            try:
                r = self.br.invoke_model(modelId=EMBED_MODEL, body=json.dumps(
                    {"inputText": t[:8000], "dimensions": 1024, "normalize": True}))
                return json.loads(r["body"].read())["embedding"]
            except Exception:
                if i == 4:
                    raise
                time.sleep(1.5 * 2 ** i)
        raise RuntimeError

    def retrieve(self, cid: str, k: int = 3) -> list[str]:
        """Pull the passages that matter, scoped to this one contract."""
        seen, out = set(), []
        for probe in PROBES.values():
            r = self.sv.query_vectors(vectorBucketName=VB, indexName=IDX, topK=k,
                                      queryVector={"float32": self.embed(probe)},
                                      filter={"contract": cid}, returnMetadata=True)
            for v in r["vectors"]:
                t = v["metadata"].get("text", "")
                h = hash(t[:200])
                if h not in seen and t:
                    seen.add(h); out.append(t)
        return out

    def ask(self, passages: list[str]) -> dict:
        ctx = "\n\n---\n\n".join(passages[:14])[:36000]
        body = {"anthropic_version": "bedrock-2023-05-31", "max_tokens": 900,
                "temperature": 0, "system": SYSTEM,
                "messages": [{"role": "user", "content":
                              f"Contract excerpts:\n\n{ctx}\n\n{SCHEMA}"}]}
        last = None
        for i in range(5):
            try:
                r = self.br.invoke_model(modelId=CHAT_MODEL, body=json.dumps(body))
                txt = json.loads(r["body"].read())["content"][0]["text"]
                m = re.search(r"\{.*\}", txt, re.S)
                if m:
                    return json.loads(m.group(0))
                last = f"no JSON in reply: {txt[:120]}"
            except Exception as e:
                last = f"{type(e).__name__}: {str(e)[:160]}"
                time.sleep(2 * 2 ** i)
        # surface the failure instead of silently returning an empty result —
        # a silent {} reads as "contract has no obligations", which is a lie
        print(f"    !! extraction failed: {last}", flush=True)
        return {"_error": last}

    def run(self, row) -> dict:
        p = self.retrieve(row["id"])
        got = self.ask(p) if p else {}
        got["_id"] = row["id"]
        got["_passages"] = len(p)
        got["_chars_sent"] = sum(len(x) for x in p)
        got["_chars_full"] = row["chars"]
        return got


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--contracts", default="../data/out/contracts.jsonl")
    ap.add_argument("--limit", type=int, default=25)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--out", default="../results/extracted_slice.json")
    a = ap.parse_args()

    rows = [json.loads(l) for l in Path(a.contracts).read_text().splitlines()]
    if a.limit:
        rows = rows[:a.limit]
    ex = Ex()
    print(f"  extracting obligations from {len(rows)} contracts ...", flush=True)
    t0, done = time.time(), [0]

    def work(r):
        o = ex.run(r)
        done[0] += 1
        if done[0] % 25 == 0:
            print(f"    {done[0]}/{len(rows)}  ({time.time()-t0:.0f}s)", flush=True)
        return o

    with ThreadPoolExecutor(max_workers=a.workers) as p:
        res = list(p.map(work, rows))

    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(res, indent=1))
    sent = sum(r.get("_chars_sent", 0) for r in res)
    full = sum(r.get("_chars_full", 0) for r in res)
    print(f"\n  {len(res)} contracts in {time.time()-t0:.0f}s")
    print(f"  sent {sent:,} chars instead of {full:,} "
          f"({sent/max(1,full)*100:.0f}% — retrieval did the filtering)")
    print(f"  auto-renew found: {sum(1 for r in res if r.get('auto_renews'))}")
    print(f"  notice periods  : {sum(1 for r in res if r.get('notice_days'))}")
    print(f"  -> {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
