#!/usr/bin/env python3
"""Turn CUAD into a working set: contract text + the obligations a CFO cares about.

CUAD (Contract Understanding Atticus Dataset) is 510 real commercial contracts
filed with the SEC, annotated by lawyers across 41 clause types. We keep the six
that cost money when nobody is tracking them:

    Renewal Term                        does it auto-renew?
    Notice Period To Terminate Renewal  how long before you're locked in again
    Expiration Date                     when the term ends
    Termination For Convenience         can you walk away at all
    Cap On Liability                    what you're exposed to
    Minimum Commitment                  what you must buy regardless

Outputs:
    out/contracts.jsonl    {id, title, category, text}          (full text, for extraction)
    out/truth.json         {id: {clause: answer}}               (expert ground truth)
    out/summary.json       corpus-level counts for the story

    python3 build_dataset.py --cuad CUAD_v1 --out out
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import pandas as pd

# clause -> the master_clauses.csv column prefix
CLAUSES = {
    "renewal_term": "Renewal Term",
    "notice_to_terminate_renewal": "Notice Period To Terminate Renewal",
    "expiration_date": "Expiration Date",
    "termination_for_convenience": "Termination For Convenience",
    "cap_on_liability": "Cap On Liability",
    "minimum_commitment": "Minimum Commitment",
}
EMPTY = {"", "nan", "[]", "none", "no"}


def clean(v) -> str:
    if v is None:
        return ""
    s = re.sub(r"\s+", " ", str(v)).strip()
    return "" if s.lower() in EMPTY else s


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cuad", default="CUAD_v1")
    ap.add_argument("--out", default="out")
    a = ap.parse_args()
    C, out = Path(a.cuad), Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    # ---- full contract text (SQuAD-style json) -----------------------------
    doc = json.loads((C / "CUAD_v1.json").read_text())["data"]
    texts = {}
    for d in doc:
        texts[d["title"]] = d["paragraphs"][0]["context"]
    print(f"  {len(texts)} contracts with full text")

    # ---- expert ground truth ----------------------------------------------
    df = pd.read_csv(C / "master_clauses.csv")
    df["key"] = df["Filename"].astype(str).str.replace(r"\.pdf$", "", regex=True)

    # match csv rows to json titles (titles are the filename stem)
    by_title = {}
    for _, r in df.iterrows():
        by_title[r["key"]] = r

    truth, rows, matched = {}, [], 0
    for title, text in texts.items():
        r = by_title.get(title)
        if r is None:
            # fall back to a loose match on the leading company/------ token
            cand = [k for k in by_title if k[:40] == title[:40]]
            r = by_title[cand[0]] if cand else None
        if r is None:
            continue
        matched += 1
        t = {}
        for name, col in CLAUSES.items():
            ansc = [c for c in df.columns if c.startswith(col) and "Answer" in c]
            txtc = [c for c in df.columns if c == col]
            t[name] = {"answer": clean(r[ansc[0]]) if ansc else "",
                       "evidence": clean(r[txtc[0]]) if txtc else ""}
        truth[title] = t
        cat = "unknown"
        rows.append({"id": title, "title": title, "category": cat,
                     "chars": len(text), "text": text})

    print(f"  matched {matched} contracts to ground truth")

    with (out / "contracts.jsonl").open("w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    (out / "truth.json").write_text(json.dumps(truth, indent=1))

    # ---- the corpus story --------------------------------------------------
    summary = {"n_contracts": len(rows),
               "total_chars": sum(r["chars"] for r in rows),
               "avg_chars": sum(r["chars"] for r in rows) // max(1, len(rows)),
               "clauses": {}}
    for name in CLAUSES:
        present = sum(1 for t in truth.values() if t[name]["answer"])
        summary["clauses"][name] = {"present": present,
                                    "pct": round(present / max(1, len(truth)) * 100, 1)}
    # notice windows are the money clause — bucket the actual values
    windows: dict[str, int] = {}
    for t in truth.values():
        v = t["notice_to_terminate_renewal"]["answer"].lower()
        if not v:
            continue
        m = re.search(r"(\d+)\s*(day|month|week|year)", v)
        if m:
            k = f"{m.group(1)} {m.group(2)}s"
            windows[k] = windows.get(k, 0) + 1
    summary["notice_windows"] = dict(sorted(windows.items(), key=lambda kv: -kv[1])[:10])
    (out / "summary.json").write_text(json.dumps(summary, indent=2))

    print(f"\n  {'clause':36s} {'present':>8s} {'%':>7s}")
    print("  " + "-" * 54)
    for k, v in summary["clauses"].items():
        print(f"  {k:36s} {v['present']:>8d} {v['pct']:>6.1f}%")
    print(f"\n  notice windows: {summary['notice_windows']}")
    print(f"  corpus: {summary['total_chars']:,} chars (avg {summary['avg_chars']:,}/contract)")
    print(f"  -> {out}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
