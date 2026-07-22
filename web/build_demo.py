#!/usr/bin/env python3
"""Build web/demo.html from results/rundata.json.

CFO-first: what's hiding in the contract estate, then how well the machine
actually reads it (graded against lawyers), then the honest limits.

Run data is embedded as <script id="rundata">; video/render.py reads the same
results/, so the demo and the video can't drift.

    python3 web/build_demo.py
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = json.loads((ROOT / "results" / "rundata.json").read_text())

HTML = """<title>130 of these contracts renew themselves</title>
<style>
  :root {
    color-scheme: light;
    --bg:#f7f8fa; --card:#ffffff; --rule:#e3e6ec;
    --ink:#12141a; --ink2:#555c6b; --ink3:#858c9a;
    --machine:#2a78d6; --risk:#e34948; --ok:#1baf7a; --flag:#eb6834; --muted:#9aa1b1;
    --mono: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace;
    --sans: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  }
  @media (prefers-color-scheme: dark) {
    :root:where(:not([data-theme="light"])) {
      color-scheme: dark;
      --bg:#0f1218; --card:#161a22; --rule:#252a34;
      --ink:#eef1f6; --ink2:#a6adbb; --ink3:#727988;
      --machine:#3987e5; --risk:#e66767; --ok:#199e70; --flag:#d95926; --muted:#6d7484;
    }
  }
  :root[data-theme="dark"] {
    color-scheme: dark;
    --bg:#0f1218; --card:#161a22; --rule:#252a34;
    --ink:#eef1f6; --ink2:#a6adbb; --ink3:#727988;
    --machine:#3987e5; --risk:#e66767; --ok:#199e70; --flag:#d95926; --muted:#6d7484;
  }
  * { box-sizing:border-box; }
  body { margin:0; background:var(--bg); color:var(--ink); font-family:var(--sans);
         line-height:1.55; -webkit-font-smoothing:antialiased; }
  .wrap { max-width:1060px; margin:0 auto; padding:48px 24px 96px; }
  .eyebrow { font-family:var(--mono); font-size:11.5px; letter-spacing:.14em;
             text-transform:uppercase; color:var(--ink3); margin:0 0 14px; }
  h1 { font-size:clamp(29px,4.4vw,46px); line-height:1.1; letter-spacing:-.022em;
       margin:0 0 16px; text-wrap:balance; font-weight:640; max-width:19ch; }
  h1 em { font-style:normal; color:var(--risk); }
  .lede { font-size:18px; color:var(--ink2); margin:0; max-width:64ch; }
  h2 { font-size:20px; letter-spacing:-.012em; margin:0 0 6px; font-weight:620; }
  .sub { color:var(--ink2); font-size:14.5px; margin:0 0 20px; max-width:74ch; }
  section { margin-top:56px; }
  .card { background:var(--card); border:1px solid var(--rule); border-radius:10px; padding:22px; }
  .facts { display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); gap:1px;
           background:var(--rule); border:1px solid var(--rule); border-radius:10px;
           overflow:hidden; margin-top:28px; }
  .fact { background:var(--card); padding:15px 16px; }
  .fact b { display:block; font-family:var(--mono); font-size:20px;
            font-variant-numeric:tabular-nums; letter-spacing:-.02em; }
  .fact b.risk { color:var(--risk); }
  .fact span { font-size:11.5px; color:var(--ink3); font-family:var(--mono);
               letter-spacing:.05em; text-transform:uppercase; }
  .steps { display:grid; grid-template-columns:repeat(auto-fit,minmax(212px,1fr)); gap:12px; }
  .step { background:var(--card); border:1px solid var(--rule);
          border-left:3px solid var(--machine); border-radius:8px; padding:16px 18px; }
  .step b { display:block; font-size:15px; margin-bottom:4px; }
  .step span { font-size:13px; color:var(--ink2); }
  .step i { font-family:var(--mono); font-size:11px; color:var(--ink3); font-style:normal;
            letter-spacing:.08em; }
  figure { margin:0; } .plot { position:relative; overflow-x:auto; }
  svg { display:block; width:100%; height:auto; }
  .legend { display:flex; flex-wrap:wrap; gap:8px 18px; margin:0 0 14px;
            font-size:12.5px; font-family:var(--mono); color:var(--ink2); }
  .legend i { width:16px; height:10px; border-radius:2px; display:inline-block;
              vertical-align:middle; margin-right:7px; }
  table { width:100%; border-collapse:collapse; font-family:var(--mono); font-size:13px;
          font-variant-numeric:tabular-nums; }
  th, td { text-align:right; padding:9px 10px; border-bottom:1px solid var(--rule); }
  th:first-child, td:first-child { text-align:left; }
  th { font-size:11px; letter-spacing:.07em; text-transform:uppercase; color:var(--ink3);
       font-weight:500; }
  td.q { font-family:var(--sans); font-size:12.5px; color:var(--ink2); text-align:left;
         max-width:520px; }
  .win { color:var(--ok); font-weight:600; } .bad { color:var(--risk); font-weight:600; }
  .callout { border-left:3px solid var(--machine); padding:12px 0 12px 16px; margin:22px 0 0;
             color:var(--ink2); font-size:14.5px; max-width:76ch; }
  .callout.warn { border-left-color:var(--risk); }
  .callout.flag { border-left-color:var(--flag); }
  .callout b { color:var(--ink); }
  .qa { border:1px solid var(--rule); border-radius:8px; padding:14px 16px; margin-bottom:10px;
        background:var(--card); }
  .qa .q { font-size:14.5px; margin-bottom:4px; }
  .qa .m { font-family:var(--mono); font-size:11.5px; color:var(--ink3); margin-bottom:8px; }
  .qa .h { font-family:var(--mono); font-size:12px; color:var(--ink2); padding:6px 0;
           border-top:1px dashed var(--rule); }
  .qa .h b { color:var(--ink); font-weight:600; }
  footer { margin-top:64px; padding-top:22px; border-top:1px solid var(--rule);
           color:var(--ink3); font-size:12.5px; font-family:var(--mono); line-height:1.9; }
  @media (prefers-reduced-motion:reduce){ *{transition:none!important;animation:none!important;} }
</style>

<div class="wrap">
  <header>
    <p class="eyebrow">510 real contracts · filed with the SEC · annotated by lawyers</p>
    <h1><span id="h1n">130</span> of these contracts <em>renew themselves</em>.</h1>
    <p class="lede">Nobody reads a contract twice. It gets signed, filed, and then quietly
      renews — sometimes with 30 days' notice to stop it, sometimes with none at all. Here's
      a machine reading 499 of them, and an honest account of what it got right and wrong.</p>
    <div class="facts" id="facts"></div>
  </header>

  <section>
    <h2>The loop</h2>
    <p class="sub">Four steps. Extraction is not the product — the register is.</p>
    <div class="steps" id="steps"></div>
  </section>

  <section>
    <h2>How long you get to react</h2>
    <p class="sub">Of the agreements that renew themselves, this is the notice you must give
      to stop it. Miss the window and you own another term.</p>
    <div class="card">
      <figure class="plot" id="plotNotice"></figure>
    </div>
    <p class="callout warn"><b id="tight">27</b> agreements give you <b>30 days or less</b> —
      and <b id="silent">39</b> renew with no notice period stated at all. Those are the ones
      that quietly become somebody's problem in Q4.</p>
  </section>

  <section>
    <h2>Can it actually read a contract?</h2>
    <p class="sub">Graded against the lawyers' annotations — not a demo on three cherry-picked
      agreements. Precision = when it flags a clause, is it really there. Recall = of the
      clauses that exist, how many it found.</p>
    <div class="card">
      <div class="legend">
        <span><i style="background:var(--machine)"></i>precision</span>
        <span><i style="background:var(--ok)"></i>recall</span>
      </div>
      <figure class="plot" id="plotAcc"></figure>
    </div>
    <p class="callout"><b>It reads the number correctly <span id="nv">96.6</span>% of the
      time.</b> On the clause that actually costs money — the notice window — it finds
      <b id="nrec">92</b>% of them, and when it does, the day count is exact in
      <span id="nx">84</span> of <span id="nn">87</span> cases. That's the difference between
      a diary entry and a renewal you didn't choose.</p>
    <p class="callout warn"><b>Where it's weak, plainly.</b> Liability caps: it is almost never
      wrong when it flags one (<span id="capp">99</span>% precision) but it only finds
      <span id="capr">46</span>% of them — it was told to ignore a bare disclaimer of
      consequential damages, and it errs toward silence. Minimum commitments are the weakest
      (F1 <span id="mcf1">0.59</span>). This triages a contract estate; it does not replace
      the lawyer reading the one deal that matters.</p>
  </section>

  <section>
    <h2>Ask the whole estate</h2>
    <p class="sub">Nobody files "auto-renewal" in a searchable field — they write two
      paragraphs of prose, differently every time. These are real queries against the
      indexed clauses.</p>
    <div id="qa"></div>
    <p class="callout"><b>This is the part that needs a vector index</b> — and the argument
      for S3 Vectors isn't speed, it's that there's no vector database to stand up, secure,
      and pay for while idle. The index sits in object storage next to the documents.
      Honest caveat: at 499 contracts you could brute-force this. It earns its keep at a few
      thousand.</p>
  </section>

  <section>
    <h2>The register</h2>
    <p class="sub">The deliverable — agreements that renew themselves, soonest deadline first.</p>
    <div class="card" style="overflow-x:auto"><table id="reg"></table></div>
  </section>

  <footer id="foot"></footer>
</div>

<script id="rundata" type="application/json">__RUNDATA__</script>
<script>
const D = JSON.parse(document.getElementById('rundata').textContent);
const R = D.register, A = D.accuracy, C = D.corpus, RT = D.retrieval;
const fmt = n => n.toLocaleString('en-US');
const svgNS='http://www.w3.org/2000/svg';
const el=(n,a={})=>{const e=document.createElementNS(svgNS,n);
  for(const k in a)e.setAttribute(k,a[k]);return e;};
const txt=(p,x,y,s,o={})=>{const t=el('text',{x,y,'font-family':'var(--mono)',
  'font-size':o.size||12,fill:o.fill||'var(--ink3)','text-anchor':o.anchor||'start',
  ...(o.weight?{'font-weight':o.weight}:{})});t.textContent=s;p.appendChild(t);return t;};

document.getElementById('h1n').textContent = R.auto_renewing;
document.getElementById('tight').textContent = R.tight_window_30d_or_less;
document.getElementById('silent').textContent = R.auto_renew_no_notice_found;

document.getElementById('facts').innerHTML = [
  [fmt(R.n_contracts), 'contracts read', ''],
  [R.auto_renewing + ' (' + R.auto_renewing_pct + '%)', 'renew themselves', ''],
  [R.tight_window_30d_or_less, '30 days or less', 'risk'],
  [R.no_liability_cap + ' (' + R.no_liability_cap_pct + '%)', 'no liability cap', 'risk'],
  [RT.pct_saved + '%', 'of text never sent', ''],
].map(([b,s,c]) => `<div class="fact"><b class="${c}">${b}</b><span>${s}</span></div>`).join('');

document.getElementById('steps').innerHTML = [
  ['The lake', `${fmt(R.n_contracts)} contracts, ${(C.total_chars/1e6).toFixed(1)}M characters, landed in S3.`],
  ['Read them', `Bedrock pulls the obligations from ${RT.pct_sent}% of the text — retrieval throws away the boilerplate.`],
  ['Ask them', `${fmt(RT.chunks_indexed)} clauses indexed in S3 Vectors. No database to run.`],
  ['The register', `Which renew, how long you have, what is uncapped — and what to hand a human.`],
].map(([t,s],i)=>`<div class="step"><i>STEP ${i+1}</i><b>${t}</b><span>${s}</span></div>`).join('');

/* notice-window histogram */
(function(){
  const H = R.notice_histogram, keys = ['<= 30 days','31-60 days','61-90 days','> 90 days'];
  const rows = keys.filter(k=>H[k]).map(k=>[k,H[k]]);
  const W=980,BH=54,H0=40+rows.length*BH,P={l:132,r:250,t:34};
  const svg=el('svg',{viewBox:`0 0 ${W} ${H0}`,role:'img',
    'aria-label':'How much notice you get to stop an automatic renewal'});
  const max=Math.max(...rows.map(r=>r[1]));
  txt(svg,P.l,16,'AGREEMENTS THAT RENEW THEMSELVES, BY NOTICE REQUIRED',{size:11});
  rows.forEach(([k,v],i)=>{
    const y=P.t+i*BH, w=Math.max(v/max*(W-P.l-P.r),3);
    const danger = k==='<= 30 days';
    svg.appendChild(el('rect',{x:P.l,y,width:w,height:30,rx:5,
      fill:danger?'var(--risk)':'var(--machine)'}));
    txt(svg,P.l-12,y+20,k,{anchor:'end',fill:'var(--ink2)',size:13});
    txt(svg,P.l+w+12,y+20,String(v),{fill:'var(--ink)',size:14,weight:600});
    if(danger) txt(svg,P.l+w+44,y+20,'← barely time to act',{fill:'var(--risk)',size:12});
  });
  document.getElementById('plotNotice').appendChild(svg);
})();

/* precision / recall per clause */
(function(){
  const order=['auto-renewal','notice to terminate','expiration date',
               'termination for convenience','cap on liability','minimum commitment'];
  const rows=order.filter(k=>A.clauses[k]).map(k=>[k,A.clauses[k]]);
  const W=980,G=62,H0=44+rows.length*G,P={l:250,r:96,t:30};
  const svg=el('svg',{viewBox:`0 0 ${W} ${H0}`,role:'img',
    'aria-label':'Precision and recall per clause, graded against lawyer annotations'});
  const bw=W-P.l-P.r;
  [0,.25,.5,.75,1].forEach(g=>{
    svg.appendChild(el('line',{x1:P.l+g*bw,x2:P.l+g*bw,y1:P.t-6,y2:H0-16,
      stroke:'var(--rule)','stroke-width':1}));
    txt(svg,P.l+g*bw,H0-4,(g*100)+'%',{anchor:'middle',size:10.5});
  });
  rows.forEach(([k,v],i)=>{
    const y=P.t+i*G;
    txt(svg,P.l-12,y+16,k,{anchor:'end',fill:'var(--ink2)',size:13});
    txt(svg,P.l-12,y+32,`${v.truth_present} in truth`,{anchor:'end',size:10.5});
    [['precision',v.precision,'var(--machine)',0],['recall',v.recall,'var(--ok)',15]]
      .forEach(([,val,col,dy])=>{
        svg.appendChild(el('rect',{x:P.l,y:y+dy,width:Math.max(val*bw,2),height:12,rx:3,fill:col}));
        txt(svg,P.l+val*bw+8,y+dy+10,val.toFixed(2),{fill:'var(--ink)',size:11,weight:600});
      });
  });
  document.getElementById('plotAcc').appendChild(svg);
})();

const nv=A.notice_value_accuracy;
document.getElementById('nv').textContent=nv.exact_pct;
document.getElementById('nx').textContent=nv.exact;
document.getElementById('nn').textContent=nv.n;
document.getElementById('nrec').textContent=Math.round(A.clauses['notice to terminate'].recall*100);
document.getElementById('capp').textContent=Math.round(A.clauses['cap on liability'].precision*100);
document.getElementById('capr').textContent=Math.round(A.clauses['cap on liability'].recall*100);
document.getElementById('mcf1').textContent=A.clauses['minimum commitment'].f1.toFixed(2);

/* search */
document.getElementById('qa').innerHTML = (D.search||[]).map(s=>`
  <div class="qa"><div class="q">“${s.question}”</div>
    <div class="m">${s.latency_ms} ms · searched every indexed clause</div>
    ${s.hits.slice(0,2).map(h=>`<div class="h"><b>${h.contract.slice(0,44)}</b><br>“${h.text.slice(0,190)}…”</div>`).join('')}
  </div>`).join('');

/* register */
(function(){
  const rows=(D.sample_register||[]).slice(0,12);
  document.getElementById('reg').innerHTML =
    `<thead><tr><th>agreement</th><th>renews</th><th>notice</th><th>cap on liability</th></tr></thead><tbody>`+
    rows.map(r=>`<tr>
      <td>${r.contract.slice(0,40)}</td>
      <td>${(r.renewal_term||'—').toString().slice(0,22)}</td>
      <td class="${r.notice_days<=30?'bad':''}">${r.notice_days} d</td>
      <td>${r.liability_cap?String(r.liability_cap).slice(0,44):'<span class="bad">none found</span>'}</td>
    </tr>`).join('')+'</tbody>';
})();

document.getElementById('foot').innerHTML = `
  Data: ${C.name} — ${C.source}. ${fmt(R.n_contracts)} of 510 joined cleanly to the
  annotations; 11 did not and are excluded.<br>
  Extraction: ${D.models.extract}, over passages retrieved from ${D.models.embed} embeddings
  indexed in S3 Vectors (${fmt(RT.chunks_indexed)} clauses). Only ${RT.pct_sent}% of the
  corpus text was ever sent to the model.<br>
  ${R.flagged_for_review} extraction was implausible (a term length read as a notice period)
  and is flagged for a human rather than silently used.<br>
  Precision/recall are measured against the lawyers' labels; they are not self-reported
  confidence. The whole run cost roughly a dollar of Bedrock.
`;
</script>
"""

out = ROOT / "web" / "demo.html"
out.write_text(HTML.replace("__RUNDATA__", json.dumps(DATA, separators=(",", ":"))))
print(f"  -> {out}  ({out.stat().st_size:,} bytes)")
