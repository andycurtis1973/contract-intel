# 130 of these contracts renew themselves

Nobody reads a contract twice. It gets signed, filed, and then quietly renews —
sometimes with 30 days' notice to stop it, sometimes with none at all.

This reads **499 real commercial contracts** filed with the SEC
([CUAD](https://zenodo.org/records/4595826), annotated by lawyers), builds the
obligation register a finance team actually wants, and — because the dataset has
expert labels — **reports honestly how often it's right**.

The whole run costs about **a dollar** of Bedrock.

## What's hiding in the estate

| | |
|---|---|
| Contracts read | **499** |
| Renew themselves | **130 (26%)** |
| …with **30 days' notice or less** | **27** |
| …renew with **no notice period stated** | **39** |
| **No cap on liability** | **376 (75%)** |
| Minimum commitments | 131 |
| Flagged for a human (implausible) | 1 |

Notice windows: min 5 days · **median 90** · and 27 agreements at 30 days or under.

## Can it actually read a contract?

Graded against the lawyers' annotations — not three cherry-picked agreements.

| Clause | in truth | Precision | Recall | F1 |
|---|---|---|---|---|
| Auto-renewal | 160 | **0.92** | 0.75 | 0.83 |
| **Notice to terminate** | 97 | 0.75 | **0.92** | 0.83 |
| Expiration date | 323 | 0.77 | 0.79 | 0.78 |
| Termination for convenience | 180 | 0.73 | 0.91 | 0.81 |
| Cap on liability | 268 | **0.99** | 0.46 | 0.62 |
| Minimum commitment | 165 | 0.66 | 0.53 | 0.59 |

**And the number itself: 84 of 87 notice periods exact — 96.6%.**

That's the metric that matters. Finding the clause but misreading "60 days" as
"30" is worse than not finding it.

### Where it's weak, plainly
- **Liability caps**: almost never wrong when it flags one (0.99 precision) but it
  finds only 46%. It was told to ignore a bare disclaimer of consequential damages,
  so it errs toward silence.
- **Minimum commitments** are the weakest (F1 0.59).
- This **triages an estate**. It does not replace the lawyer reading the one deal
  that matters.

> A bug worth recording: the first prompt said *"convert months ×30"* and the model
> applied it to values already in days — "90 days" became 2,700. Notice-value accuracy
> was 83.7%. Stating the unit rule explicitly took it to **96.6%**. The prompt was
> ambiguous, not the model.

## The loop

| Step | What | AWS |
|---|---|---|
| 1. **The lake** | 499 contracts, 25.7M characters | S3 |
| 2. **Read them** | Obligations extracted from **24.5%** of the text — retrieval throws away the boilerplate | Bedrock (Claude Haiku 4.5) |
| 3. **Ask them** | 22,792 clauses indexed; semantic search in ~0.5s | **S3 Vectors** |
| 4. **The register** | What renews, how long you get, what's uncapped — and what to hand a human | — |

### On S3 Vectors, honestly
The argument isn't speed — it's that there's **no vector database to stand up,
secure, and pay for while idle**. The index lives in object storage next to the
documents. At 499 contracts you could brute-force this in numpy; it earns its keep
at a few thousand, which is where a mid-size company actually is.

### On not inventing deadlines
These are historical SEC filings, so "renews on 12 March" would be theatre. The
register reports what's real: how many agreements renew unattended, how much warning
each gives, and how much of the estate is uncapped. One extraction was implausible
(a term length read as a notice period) and is **flagged for review rather than
silently used** — a system that quietly invents a deadline is worse than one that
admits doubt.

## Layout

```
data/build_dataset.py        CUAD -> contracts.jsonl + lawyer ground truth
extract/index_clauses.py     chunk + embed + index into S3 Vectors
extract/extract_obligations.py  retrieve the clauses, extract with Bedrock
extract/ask.py               semantic search across the whole estate
model/score.py               grade against the annotations (precision/recall)
model/register.py            the obligation register + review flags
web/build_demo.py            -> web/demo.html (interactive; embeds rundata)
video/                       the ~2-min narrated explainer
```

## Reproduce

```bash
curl -L -o data/CUAD_v1.zip \
  "https://zenodo.org/records/4595826/files/CUAD_v1.zip?download=1"   # open, no auth
cd data && unzip -q CUAD_v1.zip && python3 build_dataset.py && cd ..
python3 extract/index_clauses.py --contracts data/out/contracts.jsonl
python3 extract/extract_obligations.py --limit 0 --out results/extracted_full.json
python3 model/score.py --pred results/extracted_full.json
python3 model/register.py --pred results/extracted_full.json
python3 extract/ask.py --canned
python3 web/build_demo.py
```

**Gotcha worth knowing:** newer Claude models on Bedrock are only invocable through a
cross-region **inference profile** — `us.anthropic.claude-haiku-4-5-…`. The bare
`anthropic.…` id throws `ValidationException`.

No standing infrastructure: Bedrock and S3 Vectors are pay-per-call. Delete the
vector bucket and the cost is zero.
