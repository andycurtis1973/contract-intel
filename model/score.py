#!/usr/bin/env python3
"""Grade the extraction against CUAD's lawyer annotations.

Two things are measured, and they are not the same:

  DID IT FIND THE CLAUSE   precision / recall on presence. A miss means an
                           obligation nobody is tracking; a false positive means
                           a planner chases a clause that isn't there.
  DID IT GET THE NUMBER    for notice periods, is the day count actually right?
                           Finding the clause but misreading "60 days" as "30"
                           is worse than not finding it.

    python3 score.py --pred ../results/extracted_slice.json --out ../results/accuracy.json
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

# prediction key -> ground-truth clause
PAIRS = [
    ("auto_renews", "renewal_term", "auto-renewal"),
    ("notice_days", "notice_to_terminate_renewal", "notice to terminate"),
    ("expiration", "expiration_date", "expiration date"),
    ("termination_for_convenience", "termination_for_convenience", "termination for convenience"),
    ("liability_cap", "cap_on_liability", "cap on liability"),
    ("minimum_commitment", "minimum_commitment", "minimum commitment"),
]


def present(v) -> bool:
    if v is None or v is False:
        return False
    s = str(v).strip().lower()
    return s not in ("", "none", "null", "no", "[]", "false")


def to_days(s: str):
    """'60 days' / '6 months' / '2 years' -> day count."""
    if s is None:
        return None
    s = str(s).lower()
    m = re.search(r"(\d+)\s*(day|week|month|year)", s)
    if m:
        n, unit = int(m.group(1)), m.group(2)
        return n * {"day": 1, "week": 7, "month": 30, "year": 365}[unit]
    m = re.fullmatch(r"\s*(\d+)\s*", s)
    return int(m.group(1)) if m else None


def prf(tp, fp, fn):
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    f = 2 * p * r / (p + r) if p + r else 0.0
    return round(p, 4), round(r, 4), round(f, 4)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pred", default="../results/extracted_slice.json")
    ap.add_argument("--truth", default="../data/out/truth.json")
    ap.add_argument("--out", default="../results/accuracy.json")
    a = ap.parse_args()

    preds = {p["_id"]: p for p in json.loads(Path(a.pred).read_text())}
    truth = json.loads(Path(a.truth).read_text())
    ids = [i for i in preds if i in truth]
    errs = sum(1 for p in preds.values() if p.get("_error"))
    print(f"  scoring {len(ids)} contracts ({errs} extraction errors)\n")

    out = {"n_contracts": len(ids), "extraction_errors": errs, "clauses": {}}
    for pk, tk, label in PAIRS:
        tp = fp = fn = tn = 0
        for i in ids:
            gp = present(truth[i][tk]["answer"])
            pp = present(preds[i].get(pk))
            tp += gp and pp
            fp += (not gp) and pp
            fn += gp and (not pp)
            tn += (not gp) and (not pp)
        p, r, f = prf(tp, fp, fn)
        out["clauses"][label] = {"tp": tp, "fp": fp, "fn": fn, "tn": tn,
                                 "precision": p, "recall": r, "f1": f,
                                 "truth_present": tp + fn}

    # the number, not just the clause: notice-period day counts
    ok = near = bad = 0
    for i in ids:
        g = to_days(truth[i]["notice_to_terminate_renewal"]["answer"])
        pv = preds[i].get("notice_days")
        p = to_days(pv) if not isinstance(pv, (int, float)) else int(pv)
        if g is None or p is None:
            continue
        if p == g:
            ok += 1
        elif abs(p - g) <= max(2, 0.1 * g):
            near += 1
        else:
            bad += 1
    tot = ok + near + bad
    out["notice_value_accuracy"] = {
        "exact": ok, "within_10pct": near, "wrong": bad, "n": tot,
        "exact_pct": round(ok / tot * 100, 1) if tot else None,
        "acceptable_pct": round((ok + near) / tot * 100, 1) if tot else None}

    Path(a.out).write_text(json.dumps(out, indent=2))
    print(f"  {'clause':30s} {'in truth':>9s} {'prec':>7s} {'recall':>7s} {'F1':>7s}")
    print("  " + "-" * 64)
    for k, v in out["clauses"].items():
        print(f"  {k:30s} {v['truth_present']:>9d} {v['precision']:>7.3f} "
              f"{v['recall']:>7.3f} {v['f1']:>7.3f}")
    nv = out["notice_value_accuracy"]
    if nv["n"]:
        print(f"\n  notice-period VALUE: {nv['exact']}/{nv['n']} exact "
              f"({nv['exact_pct']}%), {nv['acceptable_pct']}% within 10%")
    print(f"\n  -> {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
