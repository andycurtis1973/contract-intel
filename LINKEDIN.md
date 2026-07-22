# LinkedIn post

**Attach:** `video/out/contract_intel_demo.mp4` (~2 min narrated)
**Links:** repo + demo in the FIRST COMMENT (LinkedIn throttles reach on posts with outbound links).

---

Nobody reads a contract twice.

It gets signed, it gets filed, and then it quietly renews itself. Nobody presses a
button. Nobody signs anything. The term rolls over and the invoice arrives.

So I took 510 real commercial contracts — the kind filed with the SEC — and had a
machine read all of them.

Out of 499 it could parse:

📄 **130 renew automatically**
⏳ **27 give you 30 days or less** to stop it
🕳️ **39 renew with no notice period stated at all**
💥 **376 (75%) put no ceiling on liability**

None of that is exotic. It's just nobody's job to know it.

Here's the part I care about though: **how do you know the machine is right?**

This dataset was annotated by lawyers, clause by clause. So I didn't have to trust
the output — I could grade it.

On the notice window — the clause that actually costs money — it finds **92%** of
them. And when it finds one, it reads the day count **exactly right 96.6% of the
time** (84 of 87). That's the difference between a diary entry and a renewal you
didn't choose.

Where it's weak, plainly: liability caps. It's almost never wrong when it flags one
(99% precision) but it only finds **46%** of them. That one still needs a human. This
triages an estate — it does not replace the lawyer reading the one deal that matters.

Three things from the build:

→ **Retrieval before generation.** A contract is 50,000 characters of boilerplate
wrapped around six sentences that matter. Pulling the clauses first meant sending the
model **24%** of the text — cheaper, and it keeps it honest.

→ **The bug was my prompt, not the model.** I wrote "convert months ×30" and it
applied that to values already in days — "90 days" became 2,700. Notice accuracy was
83.7%. Stating the unit rule explicitly took it to 96.6%. Most "AI is unreliable"
stories are a spec problem.

→ **One extraction was implausible, so it got flagged instead of used.** A system that
quietly invents a deadline is worse than one that admits doubt.

I indexed 22,792 clauses in S3 Vectors — no vector database to stand up, secure, or
pay for while it idles. The whole run cost about a dollar.

If you own a contract estate: do you know how many of yours renew next quarter, and
which ones give you 30 days? 👇

#Contracts #CFO #AI #AWS #Bedrock

---

**First comment:**
> Code, data and the accuracy numbers: github.com/andycurtis1973/contract-intel
> Interactive version of the register: <shared artifact link>
