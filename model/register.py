#!/usr/bin/env python3
"""Step 4: turn the extractions into the thing a finance team actually wants.

An obligation register: which agreements renew themselves, how long you have to
stop them, and what you're on the hook for. This is the deliverable — the
extraction is just how we got here.

We deliberately do NOT invent calendar dates. These are historical SEC filings,
so "renews on 12 March" would be theatre. What IS real and what a CFO can act on:
how many agreements renew without anyone doing anything, how much warning each
one gives, and how much of the estate has no ceiling on liability.

    python3 register.py --pred ../results/extracted_full.json --out ../results/register.json
"""

from __future__ import annotations

import argparse
import json
import re
import statistics as st
from pathlib import Path


def to_days(v):
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return int(v)
    m = re.search(r"(\d+)\s*(day|week|month|year)", str(v).lower())
    if m:
        return int(m.group(1)) * {"day": 1, "week": 7, "month": 30, "year": 365}[m.group(2)]
    m = re.fullmatch(r"\s*(\d+)\s*", str(v))
    return int(m.group(1)) if m else None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pred", default="../results/extracted_full.json")
    ap.add_argument("--out", default="../results/register.json")
    a = ap.parse_args()
    rows = json.loads(Path(a.pred).read_text())
    rows = [r for r in rows if not r.get("_error")]
    n = len(rows)

    # A notice period to stop a renewal is realistically days-to-months. Anything
    # over a year is almost certainly a term length the model mistook for a notice
    # period. We don't silently drop those — we flag them for a human, because a
    # system that quietly invents a deadline is worse than one that admits doubt.
    MAX_PLAUSIBLE_NOTICE = 365
    flagged = []

    reg = []
    for r in rows:
        nd = to_days(r.get("notice_days"))
        if nd is not None and nd > MAX_PLAUSIBLE_NOTICE:
            flagged.append({"contract": r["_id"], "value_days": nd,
                            "quote": (r.get("notice_quote") or "")[:200]})
            nd = None
        reg.append({
            "contract": r["_id"],
            "auto_renews": bool(r.get("auto_renews")),
            "renewal_term": r.get("renewal_term"),
            "notice_days": nd,
            "notice_quote": (r.get("notice_quote") or "")[:300],
            "expiration": r.get("expiration"),
            "liability_cap": r.get("liability_cap"),
            "minimum_commitment": r.get("minimum_commitment"),
            "termination_for_convenience": bool(r.get("termination_for_convenience")),
        })

    auto = [x for x in reg if x["auto_renews"]]
    with_notice = [x for x in auto if x["notice_days"]]
    # the dangerous ones: renews itself, and you get little warning
    tight = [x for x in with_notice if x["notice_days"] <= 30]
    # renews automatically and we found no notice requirement at all
    silent = [x for x in auto if not x["notice_days"]]
    no_cap = [x for x in reg if not x["liability_cap"]]
    committed = [x for x in reg if x["minimum_commitment"]]
    windows = sorted(x["notice_days"] for x in with_notice)

    out = {
        "n_contracts": n,
        "auto_renewing": len(auto),
        "auto_renewing_pct": round(len(auto) / n * 100, 1),
        "with_notice_requirement": len(with_notice),
        "tight_window_30d_or_less": len(tight),
        "auto_renew_no_notice_found": len(silent),
        "no_liability_cap": len(no_cap),
        "no_liability_cap_pct": round(len(no_cap) / n * 100, 1),
        "minimum_commitments": len(committed),
        "flagged_for_review": len(flagged),
        "flagged": flagged,
        "notice_window_days": {
            "min": windows[0] if windows else None,
            "median": int(st.median(windows)) if windows else None,
            "max": windows[-1] if windows else None,
        },
        "notice_histogram": {},
        "register": sorted(reg, key=lambda x: (not x["auto_renews"],
                                               x["notice_days"] or 9999)),
    }
    for w in windows:
        b = ("<= 30 days" if w <= 30 else "31-60 days" if w <= 60
             else "61-90 days" if w <= 90 else "> 90 days")
        out["notice_histogram"][b] = out["notice_histogram"].get(b, 0) + 1

    Path(a.out).write_text(json.dumps(out, indent=1))
    print(f"  OBLIGATION REGISTER — {n} contracts\n")
    print(f"  renew themselves            {out['auto_renewing']:>5d}  ({out['auto_renewing_pct']}%)")
    print(f"    ...with a notice window   {out['with_notice_requirement']:>5d}")
    print(f"    ...30 days or less        {out['tight_window_30d_or_less']:>5d}   <- act early or you're locked in")
    print(f"    ...no notice term found   {out['auto_renew_no_notice_found']:>5d}")
    print(f"  no cap on liability         {out['no_liability_cap']:>5d}  ({out['no_liability_cap_pct']}%)")
    print(f"  minimum commitments         {out['minimum_commitments']:>5d}")
    print(f"  flagged for human review    {out['flagged_for_review']:>5d}   <- implausible, not guessed at")
    w = out["notice_window_days"]
    print(f"\n  notice window: min {w['min']}d · median {w['median']}d · max {w['max']}d")
    for k, v in out["notice_histogram"].items():
        print(f"    {k:12s} {v:>4d}")
    print(f"\n  -> {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
