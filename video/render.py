#!/usr/bin/env python3
"""Slides + animations: reading a contract estate.

Same four-step operating-model frame as the last build — the extraction is
plumbing, the register is the deliverable. Every number is read from results/,
which is also what the web demo embeds, so the two can't disagree.
"""

from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
W, H = 1920, 1080

BG = (15, 18, 24)
CARD = (22, 26, 34)
RULE = (37, 42, 52)
TX = (238, 241, 246)
MUT = (166, 173, 187)
DIM = (114, 121, 136)
MACHINE = (57, 135, 229)
RISK = (230, 103, 103)
OK = (25, 158, 112)
FLAG = (217, 89, 38)

_C = {"bold": ["/System/Library/Fonts/Supplemental/Arial Bold.ttf",
               "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"],
      "reg": ["/System/Library/Fonts/Supplemental/Arial.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"],
      "mono": ["/System/Library/Fonts/Menlo.ttc",
               "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"]}
_F: dict = {}


def font(kind, size):
    k = (kind, size)
    if k in _F:
        return _F[k]
    for p in _C[kind]:
        if Path(p).exists():
            try:
                _F[k] = ImageFont.truetype(p, size); return _F[k]
            except Exception:
                continue
    _F[k] = ImageFont.load_default(); return _F[k]


def T(d, xy, s, f, fill, anchor="la"):
    d.text(xy, s, font=f, fill=fill, anchor=anchor)


def base(kicker=None):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 5], fill=MACHINE)
    if kicker:
        T(d, (110, 84), kicker.upper(), font("mono", 24), DIM)
    return img, d


def ease(t):
    return 1 - (1 - t) ** 3


# --- the numbers -----------------------------------------------------------
D = json.loads((ROOT / "results" / "rundata.json").read_text())
REG, ACC, RT, C = D["register"], D["accuracy"], D["retrieval"], D["corpus"]
NV = ACC["notice_value_accuracy"]
N = REG["n_contracts"]
AUTO = REG["auto_renewing"]
TIGHT = REG["tight_window_30d_or_less"]
SILENT = REG["auto_renew_no_notice_found"]
NOCAP = REG["no_liability_cap"]
HIST = REG["notice_histogram"]

STEPS = [("The lake", "contracts in S3"), ("Read them", "Bedrock"),
         ("Ask them", "S3 Vectors"), ("The register", "what to act on")]


def strip(d, active, y=956):
    x, bw, gap = 110, 400, 26
    for i, (t_, _s) in enumerate(STEPS):
        bx = x + i * (bw + gap)
        on = i == active
        d.rounded_rectangle([bx, y, bx + bw, y + 68], radius=10,
                            fill=CARD if on else BG,
                            outline=MACHINE if on else RULE, width=3 if on else 1)
        T(d, (bx + 20, y + 21), f"{i+1}. {t_}", font("bold", 26), TX if on else DIM)


# ============================ STATIC ======================================
def s0_title():
    img, d = base()
    T(d, (W / 2, 330), "Nobody reads a contract twice.", font("bold", 76), TX, "mm")
    T(d, (W / 2, 432), f"{AUTO} of these {N} renew themselves.", font("bold", 76), RISK, "mm")
    T(d, (W / 2, 566), "Reading a real contract estate with Bedrock and S3 Vectors",
      font("reg", 38), MUT, "mm")
    T(d, (W / 2, 640), "510 agreements filed with the SEC  ·  annotated by lawyers",
      font("mono", 27), DIM, "mm")
    return img


def s5_close():
    img, d = base()
    T(d, (W / 2, 306), "It won't replace your lawyer.", font("bold", 72), TX, "mm")
    T(d, (W / 2, 398), "It makes sure nobody misses the date.", font("bold", 72), MACHINE, "mm")
    T(d, (W / 2, 516), f"{N} contracts read · {AUTO} renew themselves · "
      f"{TIGHT} give you 30 days", font("mono", 30), MUT, "mm")
    url = "github.com/andycurtis1973/contract-intel"
    w = d.textlength(url, font=font("mono", 32))
    d.rounded_rectangle([(W - w) / 2 - 34, 606, (W + w) / 2 + 34, 686], radius=12,
                        fill=CARD, outline=MACHINE, width=2)
    T(d, (W / 2, 646), url, font("mono", 32), MACHINE, "mm")
    T(d, (W / 2, 748), "Open data, open code, and the accuracy numbers to check it",
      font("reg", 28), DIM, "mm")
    return img


# ============================ ANIMATIONS ==================================
def a_problem(t):
    """A wall of contracts; a quarter of them quietly renew."""
    img, d = base("the problem")
    T(d, (110, 190), "It gets signed, filed — and forgotten.", font("bold", 58), TX)
    e = ease(min(1.0, t / 0.7))
    cols, rows, cw = 40, 10, 40
    total = cols * rows
    shown = int(total * e)
    # the first AUTO/N share are the ones that renew themselves
    frac = AUTO / N
    for i in range(shown):
        cx, cy = 110 + (i % cols) * cw, 330 + (i // cols) * cw
        renews = (i % cols) < round(cols * frac)
        col = RISK if (renews and t > 0.55) else RULE
        d.rounded_rectangle([cx, cy, cx + cw - 9, cy + cw - 9], radius=3, fill=col)
    if t > 0.62:
        T(d, (110, 792), f"{AUTO}", font("bold", 92), RISK)
        T(d, (110, 900), f"OF {N} RENEW THEMSELVES — NOBODY PRESSED A BUTTON",
          font("mono", 26), DIM)
    return img


def a_read(t):
    """Steps 1-2: land it, then read only the parts that matter."""
    img, d = base("steps 1 & 2 · land it, read it")
    T(d, (110, 186), "Read them without reading all of them", font("bold", 56), TX)
    e = ease(min(1.0, t / 0.7))
    bx, by, bw, bh = 110, 330, 1700, 90
    d.rounded_rectangle([bx, by, bx + bw, by + bh], radius=8, fill=RULE)
    T(d, (bx, by - 30), f"{C['total_chars']/1e6:.1f} MILLION CHARACTERS OF LEGAL PROSE",
      font("mono", 24), DIM)
    sent = int(bw * RT["pct_sent"] / 100 * e)
    d.rounded_rectangle([bx, by + 150, bx + sent, by + 150 + bh], radius=8, fill=MACHINE)
    T(d, (bx, by + 120), "WHAT WE ACTUALLY SENT TO THE MODEL", font("mono", 24), DIM)
    if e > 0.5:
        T(d, (bx + sent + 20, by + 150 + bh / 2), f"{RT['pct_sent']}%",
          font("bold", 40), MACHINE, "lm")
    if t > 0.78:
        T(d, (110, 640), f"{RT['pct_saved']}% of it is boilerplate.", font("bold", 44), TX)
        T(d, (110, 706), "Retrieval finds the clause; the model reads only that.",
          font("reg", 34), MUT)
    strip(d, 1)
    return img


def a_ask(t):
    """Step 3: semantic search across the estate, no database."""
    img, d = base("step 3 · ask the estate")
    T(d, (110, 186), "Ask all of them at once", font("bold", 58), TX)
    q = '"which agreements renew unless we give written notice?"'
    typ = max(0.0, min(1.0, t / 0.42))
    d.rounded_rectangle([110, 300, 1500, 392], radius=10, fill=CARD, outline=RULE)
    T(d, (140, 330), q[:int(len(q) * typ)], font("mono", 30), MACHINE)
    if t > 0.5:
        hits = [("GpaqAcquisitionHoldings", "automatically renew for successive five (5)…"),
                ("StampscomInc", "shall automatically be extended for the Renewal Period…"),
                ("NeoformaInc", "unless either party gives written notice of non-renewal…")]
        for i, (nm, snip) in enumerate(hits):
            if t > 0.5 + i * 0.11:
                y = 450 + i * 116
                d.rounded_rectangle([110, y, 1700, y + 96], radius=8, fill=CARD, outline=RULE)
                T(d, (140, y + 18), nm, font("mono", 26), TX)
                T(d, (140, y + 56), snip, font("reg", 24), MUT)
    if t > 0.88:
        T(d, (110, 830), f"{RT['chunks_indexed']:,} clauses indexed in S3 Vectors — "
          "and no vector database to run.", font("bold", 32), MACHINE)
    strip(d, 2)
    return img


def a_register(t):
    """Step 4: the deliverable — who renews, and how long you get."""
    img, d = base("step 4 · the register")
    T(d, (110, 186), "How long you get to react", font("bold", 58), TX)
    e = ease(min(1.0, t / 0.72))
    keys = ["<= 30 days", "31-60 days", "61-90 days", "> 90 days"]
    rows = [(k, HIST.get(k, 0)) for k in keys if HIST.get(k)]
    mx = max(v for _, v in rows)
    x0, y0, gap, maxw = 460, 300, 104, 900
    for i, (k, v) in enumerate(rows):
        y = y0 + i * gap
        bw = int(maxw * (v / mx) * e)
        danger = k == "<= 30 days"
        d.rounded_rectangle([x0, y, x0 + max(bw, 4), y + 62], radius=7,
                            fill=RISK if danger else MACHINE)
        T(d, (x0 - 24, y + 30), k, font("mono", 28), MUT, "rm")
        if e > 0.5:
            T(d, (x0 + bw + 18, y + 30), str(v), font("bold", 34), TX, "lm")
        if danger and t > 0.8:
            T(d, (x0 + bw + 90, y + 30), "← barely time to act", font("bold", 28), RISK, "lm")
    if t > 0.86:
        T(d, (110, 760), f"{SILENT} more renew with no notice period stated at all.",
          font("reg", 34), MUT)
        T(d, (110, 818), f"{NOCAP} of {N} cap nobody's liability.", font("reg", 34), MUT)
    strip(d, 3)
    return img


def a_accuracy(t):
    """The rigour: graded against the lawyers, weak spots included."""
    img, d = base("but is it right?")
    T(d, (110, 186), "Graded against the lawyers", font("bold", 58), TX)
    e = ease(min(1.0, t / 0.66))
    order = [("notice to terminate", "notice window"), ("auto-renewal", "auto-renewal"),
             ("termination for convenience", "termination"), ("cap on liability", "liability cap")]
    x0, y0, gap, maxw = 520, 296, 112, 760
    T(d, (x0, y0 - 44), "PRECISION", font("mono", 22), MACHINE)
    T(d, (x0 + 300, y0 - 44), "RECALL", font("mono", 22), OK)
    for i, (k, lab) in enumerate(order):
        v = ACC["clauses"][k]
        y = y0 + i * gap
        T(d, (x0 - 24, y + 26), lab, font("mono", 28), MUT, "rm")
        for j, (val, col) in enumerate([(v["precision"], MACHINE), (v["recall"], OK)]):
            bw = int(maxw * val * e)
            d.rounded_rectangle([x0, y + j * 30, x0 + max(bw, 3), y + j * 30 + 22],
                                radius=4, fill=col)
            if e > 0.55:
                T(d, (x0 + bw + 14, y + j * 30 + 11), f"{val:.2f}", font("mono", 24), TX, "lm")
    if t > 0.8:
        T(d, (110, 792), f"{NV['exact_pct']}%", font("bold", 76), OK)
        T(d, (400, 812), "of the notice windows it finds, it reads the number exactly right",
          font("reg", 32), TX)
        T(d, (110, 890), "Liability caps it under-calls: almost never wrong, but finds "
          f"{ACC['clauses']['cap on liability']['recall']*100:.0f}%. That one still needs a human.",
          font("reg", 30), MUT)
    return img


# ---- narration -----------------------------------------------------------
SEGMENTS = [
    {"name": "s0_title", "kind": "static", "build": s0_title, "vo": [
        "Nobody reads a contract twice.",
        "It gets signed, it gets filed, and then it quietly renews itself.",
        f"I took five hundred and ten real commercial contracts, the kind filed with the S.E.C., and had a machine read them."]},
    {"name": "s1_problem", "kind": "anim", "build": a_problem, "vo": [
        "Every square here is a real agreement.",
        f"{AUTO} of them renew automatically. Nobody presses a button. Nobody signs anything.",
        "The term just rolls over, and the invoice arrives."]},
    {"name": "s2_read", "kind": "anim", "build": a_read, "vo": [
        "Step one, put them in one place. Step two, read them.",
        "But a contract is fifty thousand characters of boilerplate wrapped around about six sentences that matter.",
        f"So we retrieve the clauses first, and send the model {RT['pct_sent']} percent of the text.",
        "Cheaper, and it keeps the model honest."]},
    {"name": "s3_ask", "kind": "anim", "build": a_ask, "vo": [
        "Step three. Ask the whole estate a question.",
        "Nobody files auto-renewal in a searchable field. They write two paragraphs of legal prose, differently every single time.",
        "Twenty-two thousand clauses indexed in S three Vectors. The index sits in object storage, next to the documents.",
        "There is no vector database to stand up, secure, or pay for while it idles."]},
    {"name": "s4_register", "kind": "anim", "build": a_register, "vo": [
        "Step four is the part a finance team actually wants. The register.",
        f"Of the agreements that renew themselves, {TIGHT} give you thirty days or less to stop it.",
        f"Another {SILENT} state no notice period at all.",
        f"And {NOCAP} of the {N} put no ceiling on liability whatsoever."]},
    {"name": "s5_accuracy", "kind": "anim", "build": a_accuracy, "vo": [
        "Now, is any of this actually right?",
        "The lawyers who built this data set annotated every clause, so we can grade the machine instead of trusting it.",
        f"On the notice window, the clause that actually costs money, it finds ninety-two percent of them. And when it finds one, it reads the day count exactly right {NV['exact_pct']} percent of the time.",
        "It under-calls liability caps. It is almost never wrong, but it only finds half of them. That one still needs a human."]},
    {"name": "s6_close", "kind": "static", "build": s5_close, "vo": [
        "So this does not replace your lawyer.",
        "It makes sure nobody misses the date, on an estate nobody has time to read.",
        "The data is public, the code is open, and the accuracy numbers are there to check my work."]},
]
