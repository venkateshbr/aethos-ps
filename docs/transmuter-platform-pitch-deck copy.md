---
marp: true
title: Transmuter Enterprise Transformation Platform Pitch Deck
description: Visual SaaS pitch deck for investors, board members, CEO/CFO/COO, transformation office teams, and initiative owners.
paginate: true
theme: default
size: 16:9
footer: "Transmuter | Enterprise Transformation Value Creation Platform"
---

<style>
:root {
  --navy: #071f3c;
  --navy-2: #102f4f;
  --steel: #315f86;
  --blue: #48a9d6;
  --blue-soft: #d9edf7;
  --ink: #13283a;
  --muted: #607083;
  --line: #c9d6e2;
  --paper: #f5f8fb;
  --white: #ffffff;
  --green: #168a62;
  --green-soft: #dff3eb;
  --amber: #b7791f;
  --amber-soft: #fff2d2;
  --red: #b84343;
  --red-soft: #f8dddd;
}

section {
  font-family: "Libre Franklin", Arial, Helvetica, sans-serif;
  color: var(--ink);
  background: var(--paper);
  letter-spacing: 0;
  padding: 46px 58px;
}

h1, h2, h3 {
  letter-spacing: 0;
  margin: 0;
}

h1 {
  color: var(--navy);
  font-size: 54px;
  font-weight: 900;
  line-height: 1.02;
}

h2 {
  color: var(--steel);
  font-size: 31px;
  font-weight: 850;
  line-height: 1.16;
}

h3 {
  color: var(--navy);
  font-size: 23px;
  font-weight: 850;
}

p, li {
  font-size: 25px;
  line-height: 1.35;
}

ul {
  margin: 18px 0 0 0;
  padding-left: 26px;
}

li {
  margin: 7px 0;
}

strong {
  color: var(--navy);
}

table {
  width: 100%;
  border-collapse: collapse;
  font-size: 20px;
}

th {
  color: var(--navy);
  background: #edf3f8;
  font-weight: 850;
}

td, th {
  border: 1px solid var(--line);
  padding: 9px 10px;
  vertical-align: top;
}

section.cover {
  background:
    linear-gradient(112deg, var(--navy) 0 58%, var(--paper) 58% 100%);
  color: var(--white);
}

section.cover h1,
section.cover h2,
section.cover strong {
  color: var(--white);
}

section.section {
  background:
    linear-gradient(90deg, var(--navy) 0 34%, var(--navy-2) 34% 100%);
  color: var(--white);
}

section.section h1,
section.section h2,
section.section h3,
section.section strong {
  color: var(--white);
}

section.dark {
  background: var(--navy);
  color: var(--white);
}

section.dark h1,
section.dark h2,
section.dark h3,
section.dark strong {
  color: var(--white);
}

.kicker {
  color: var(--blue);
  font-size: 13px;
  font-weight: 900;
  letter-spacing: 2.2px;
  margin-bottom: 14px;
  text-transform: uppercase;
}

.muted {
  color: var(--muted);
}

.small {
  font-size: 18px;
  line-height: 1.35;
}

.caption {
  color: var(--muted);
  font-size: 15px;
  line-height: 1.25;
}

.micro {
  font-size: 13px;
  letter-spacing: 1.3px;
  text-transform: uppercase;
  font-weight: 900;
}

.split {
  display: grid;
  grid-template-columns: 0.96fr 1.04fr;
  gap: 34px;
  align-items: center;
  height: 100%;
}

.split-wide {
  display: grid;
  grid-template-columns: 1.18fr 0.82fr;
  gap: 34px;
  align-items: center;
  height: 100%;
}

.grid-2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 18px;
}

.grid-3 {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 16px;
}

.grid-4 {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 14px;
}

.card {
  background: var(--white);
  border: 1px solid var(--line);
  border-radius: 6px;
  box-shadow: 0 10px 28px rgba(7, 31, 60, 0.08);
  padding: 18px;
}

.card.dark-card {
  background: rgba(255, 255, 255, 0.08);
  border-color: rgba(255, 255, 255, 0.26);
  color: var(--white);
}

.card h3 {
  margin-bottom: 9px;
}

.card p,
.card li {
  font-size: 18px;
}

.stat {
  background: var(--white);
  border: 1px solid var(--line);
  border-radius: 6px;
  padding: 16px;
}

.stat .value {
  color: var(--navy);
  font-size: 38px;
  font-weight: 950;
  line-height: 1;
}

.stat .label {
  color: var(--muted);
  font-size: 13px;
  font-weight: 850;
  letter-spacing: 1px;
  margin-top: 8px;
  text-transform: uppercase;
}

.icon-row {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.icon-card {
  display: grid;
  grid-template-columns: 42px 1fr;
  gap: 12px;
  align-items: center;
  background: var(--white);
  border: 1px solid var(--line);
  border-radius: 6px;
  padding: 13px;
}

.icon-card p {
  margin: 0;
  font-size: 16px;
}

.icon {
  width: 42px;
  height: 42px;
  display: grid;
  place-items: center;
  color: var(--white);
  background: var(--navy);
  border-radius: 6px;
  font-size: 18px;
  font-weight: 950;
  box-shadow: inset 0 -5px 0 var(--blue);
}

.icon.green {
  background: var(--green);
  box-shadow: inset 0 -5px 0 #6ed3a8;
}

.icon.amber {
  background: var(--amber);
  box-shadow: inset 0 -5px 0 #efc36a;
}

.icon.red {
  background: var(--red);
  box-shadow: inset 0 -5px 0 #ef8e8e;
}

.browser {
  background: var(--white);
  border: 1px solid var(--line);
  border-radius: 8px;
  color: var(--ink);
  box-shadow: 0 24px 45px rgba(7, 31, 60, 0.18);
  overflow: hidden;
}

.browser-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 38px;
  background: var(--navy);
  color: var(--white);
  padding: 0 14px;
  font-size: 12px;
  font-weight: 850;
}

.dots {
  display: flex;
  gap: 6px;
}

.dot {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  background: var(--blue);
}

.screen-body {
  padding: 16px;
  background: #f8fafc;
  color: var(--ink);
}

.app-nav {
  display: flex;
  gap: 6px;
  margin-bottom: 14px;
}

.app-nav span {
  color: var(--steel);
  background: #e8f1f7;
  border: 1px solid #ccdae6;
  border-radius: 4px;
  font-size: 9px;
  font-weight: 900;
  letter-spacing: 0.8px;
  padding: 6px 7px;
  text-transform: uppercase;
}

.mini-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
}

.mini-card {
  background: var(--white);
  border: 1px solid var(--line);
  border-radius: 5px;
  min-height: 62px;
  padding: 10px;
}

.mini-card b {
  color: var(--navy);
  display: block;
  font-size: 20px;
  line-height: 1;
}

.mini-card span {
  color: var(--muted);
  display: block;
  font-size: 10px;
  font-weight: 850;
  margin-top: 7px;
  text-transform: uppercase;
}

.bar-row {
  display: grid;
  grid-template-columns: 145px 1fr 74px;
  gap: 10px;
  align-items: center;
  margin: 9px 0;
}

.bar-row .name,
.bar-row .num {
  font-size: 13px;
  font-weight: 850;
}

.bar-shell {
  background: #e5edf4;
  border-radius: 3px;
  height: 16px;
  overflow: hidden;
}

.bar {
  display: block;
  height: 16px;
  background: var(--steel);
}

.bar.green {
  background: var(--green);
}

.bar.amber {
  background: var(--amber);
}

.bar.red {
  background: var(--red);
}

.bar.steel {
  background: var(--steel);
}

.w100 { width: 100%; }
.w92 { width: 92%; }
.w89 { width: 89%; }
.w88 { width: 88%; }
.w82 { width: 82%; }
.w80 { width: 80%; }
.w76 { width: 76%; }
.w75 { width: 75%; }
.w74 { width: 74%; }
.w72 { width: 72%; }
.w69 { width: 69%; }
.w64 { width: 64%; }
.w46 { width: 46%; }
.w42 { width: 42%; }
.w38 { width: 38%; }
.w35 { width: 35%; }
.w28 { width: 28%; }
.w25 { width: 25%; }
.w20 { width: 20%; }
.w15 { width: 15%; }
.w14 { width: 14%; }
.w11 { width: 11%; }

.flow {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 10px;
  align-items: stretch;
}

.node {
  position: relative;
  background: var(--white);
  border: 1px solid var(--line);
  border-radius: 6px;
  min-height: 108px;
  padding: 14px;
}

.node::after {
  content: "";
  position: absolute;
  right: -10px;
  top: 48%;
  width: 18px;
  height: 2px;
  background: var(--blue);
}

.node:last-child::after {
  display: none;
}

.node .step {
  color: var(--blue);
  font-size: 13px;
  font-weight: 950;
}

.node h3 {
  font-size: 18px;
  margin-top: 8px;
}

.node p {
  color: var(--muted);
  font-size: 14px;
}

.matrix {
  display: grid;
  grid-template-columns: 1.25fr repeat(4, 1fr);
  gap: 6px;
}

.matrix div {
  background: var(--white);
  border: 1px solid var(--line);
  border-radius: 4px;
  min-height: 48px;
  padding: 9px;
  font-size: 13px;
  font-weight: 850;
}

.matrix .head {
  background: var(--navy);
  color: var(--white);
}

.matrix .hot {
  background: var(--green-soft);
  border-color: #9bdabb;
  color: var(--green);
}

.matrix .warm {
  background: var(--amber-soft);
  border-color: #e8c981;
  color: var(--amber);
}

.wf {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 14px;
  align-items: stretch;
  height: 330px;
  margin-top: 18px;
}

.wf-col {
  display: flex;
  flex-direction: column;
  gap: 7px;
  justify-content: flex-end;
  align-items: stretch;
  text-align: center;
  height: 100%;
}

.wf-bar {
  width: 100%;
  min-height: 18px;
  border-radius: 5px 5px 0 0;
  background: var(--steel);
}

.wf-bar.green {
  background: var(--green);
}

.wf-bar.amber {
  background: var(--amber);
}

.wf-bar.red {
  background: var(--red);
}

.wf-label {
  color: var(--muted);
  font-size: 12px;
  font-weight: 850;
}

.wf-value {
  color: var(--navy);
  font-size: 19px;
  font-weight: 950;
}

.timeline {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 10px;
}

.timeline .item {
  background: var(--white);
  border-top: 6px solid var(--steel);
  border-left: 1px solid var(--line);
  border-right: 1px solid var(--line);
  border-bottom: 1px solid var(--line);
  border-radius: 6px;
  padding: 13px;
  min-height: 108px;
}

.timeline .item h3 {
  font-size: 17px;
}

.timeline .item p {
  color: var(--muted);
  font-size: 14px;
}

.personas {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 14px;
}

.persona {
  background: var(--white);
  border: 1px solid var(--line);
  border-radius: 6px;
  padding: 16px;
  min-height: 214px;
}

.persona h3 {
  font-size: 22px;
}

.persona .ask {
  color: var(--steel);
  font-size: 16px;
  font-weight: 850;
  margin-top: 12px;
}

.persona p {
  color: var(--muted);
  font-size: 15px;
}

.pill-row {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.pill {
  background: #e8f1f7;
  border: 1px solid #ccdae6;
  border-radius: 999px;
  color: var(--steel);
  font-size: 12px;
  font-weight: 900;
  letter-spacing: 0.8px;
  padding: 7px 10px;
  text-transform: uppercase;
}

.quote {
  border-left: 7px solid var(--blue);
  color: var(--navy);
  font-size: 31px;
  font-weight: 850;
  line-height: 1.18;
  padding-left: 20px;
}

.mini-table {
  font-size: 15px;
}

.mini-table td,
.mini-table th {
  padding: 6px 8px;
}

.source-list li {
  font-size: 17px;
}
</style>

<!-- _class: cover -->

<div class="split">
<div>
<div class="kicker">Enterprise SaaS pitch deck</div>

# Transmuter

## Transformation value creation, governed from idea to realized EBITDA.

<p class="small" style="color:#d9edf7;margin-top:24px;">A multi-tenant platform for transformation offices, CFOs, executives, boards, and initiative owners.</p>
</div>

<div class="browser">
<div class="browser-bar"><span>transmuter.ishirock.tech</span><span class="dots"><span class="dot"></span><span class="dot"></span><span class="dot"></span></span></div>
<div class="screen-body">
<div class="app-nav"><span>Dashboard</span><span>Financials</span><span>Shared Costs</span><span>Control Tower</span></div>
<div class="mini-grid">
<div class="mini-card"><b>$8.35M</b><span>FY28 net run-rate</span></div>
<div class="mini-card"><b>10</b><span>initiatives</span></div>
<div class="mini-card"><b>$1.45M</b><span>shared cost plan</span></div>
</div>
<div style="margin-top:15px;">
<div class="bar-row"><span class="name">GM uplift</span><span class="bar-shell"><span class="bar green w92"></span></span><span class="num">$5.40M</span></div>
<div class="bar-row"><span class="name">Cost savings</span><span class="bar-shell"><span class="bar green w64"></span></span><span class="num">$3.75M</span></div>
<div class="bar-row"><span class="name">Run cost</span><span class="bar-shell"><span class="bar amber w14"></span></span><span class="num">$0.80M</span></div>
<div class="bar-row"><span class="name">Risk burden</span><span class="bar-shell"><span class="bar red w28"></span></span><span class="num">Amber</span></div>
</div>
</div>
</div>
</div>

---

# The One-Liner

<div class="quote">Transmuter is the operating system for enterprise transformation value: strategy, initiatives, financial benefits, shared costs, risks, and executive reporting in one governed tenant workspace.</div>

<div class="grid-4" style="margin-top:32px;">
<div class="stat"><div class="value">RLS</div><div class="label">tenant isolation</div></div>
<div class="stat"><div class="value">Decimal</div><div class="label">finance precision</div></div>
<div class="stat"><div class="value">AI + HITL</div><div class="label">guarded assistance</div></div>
<div class="stat"><div class="value">Board</div><div class="label">reporting ready</div></div>
</div>

---

# Why This Deck Exists

<div class="personas">
<div class="persona">
<div class="icon">I</div>
<h3>Investors</h3>
<div class="ask">Can this become a valuable SaaS company?</div>
<p>Market wedge, defensibility, product proof, GTM path, commercial gaps to fill.</p>
</div>
<div class="persona">
<div class="icon green">B</div>
<h3>Board</h3>
<div class="ask">Is transformation value real?</div>
<p>Governance, bankable value, risk, shared-cost burden, realized benefits.</p>
</div>
<div class="persona">
<div class="icon amber">C</div>
<h3>C-suite</h3>
<div class="ask">Where do we intervene?</div>
<p>CEO value story, CFO assurance, COO execution and dependencies.</p>
</div>
<div class="persona">
<div class="icon">T</div>
<h3>Transformation Office</h3>
<div class="ask">How do we run the program?</div>
<p>Tenant setup, initiative lifecycle, finance workflow, dashboards.</p>
</div>
</div>

---

<!-- _class: section -->

# 01

## The Problem: transformation value is managed in fragments.

---

# The Broken Transformation Stack

<div class="split-wide">
<div class="card">
<div class="grid-3">
<div class="icon-card"><div class="icon">S</div><p>Strategy in board decks</p></div>
<div class="icon-card"><div class="icon amber">P</div><p>PMO status in spreadsheets</p></div>
<div class="icon-card"><div class="icon green">$</div><p>Finance validation in offline models</p></div>
<div class="icon-card"><div class="icon red">R</div><p>Risks in separate registers</p></div>
<div class="icon-card"><div class="icon">K</div><p>KPIs outside the value case</p></div>
<div class="icon-card"><div class="icon amber">C</div><p>Shared costs allocated late</p></div>
</div>
</div>
<div>
<h2>Executives ask a simple question. The enterprise cannot answer quickly.</h2>
<p class="quote" style="font-size:28px;margin-top:24px;">What value is bankable, what is realized, and what could put it at risk?</p>
</div>
</div>

---

# Why Current Tools Do Not Solve It

<div class="matrix">
<div class="head">Alternative</div><div class="head">Execution</div><div class="head">Finance</div><div class="head">Governance</div><div class="head">Board View</div>
<div>Spreadsheets</div><div class="warm">Flexible</div><div class="warm">Manual</div><div>Weak</div><div>Static</div>
<div>Project tools</div><div class="hot">Strong</div><div>Weak</div><div class="warm">Partial</div><div>Limited</div>
<div>BI dashboards</div><div>Downstream</div><div class="warm">Visual</div><div>Weak</div><div class="hot">Readable</div>
<div>FP&A / EPM</div><div>Weak</div><div class="hot">Strong</div><div class="warm">Planning</div><div class="warm">Finance-only</div>
<div>Consulting PMO</div><div class="warm">Helpful</div><div class="warm">Manual</div><div class="warm">Method-led</div><div class="hot">Polished</div>
<div><strong>Transmuter</strong></div><div class="hot">Initiative workflow</div><div class="hot">Finance engine</div><div class="hot">Stage gates</div><div class="hot">Live control tower</div>
</div>

---

# Why Now

<div class="grid-3">
<div class="card"><div class="icon">$</div><h3>CFO scrutiny</h3><p>Transformation value must reconcile to validated benefits, not optimistic claims.</p></div>
<div class="card"><div class="icon green">B</div><h3>Board pressure</h3><p>Directors want evidence, risk context, and value realization discipline.</p></div>
<div class="card"><div class="icon amber">AI</div><h3>AI complexity</h3><p>AI adds urgency for governed workflows, traceability, and tenant-safe assistance.</p></div>
</div>
<div class="grid-3" style="margin-top:16px;">
<div class="card"><div class="icon">PM</div><h3>PMO fatigue</h3><p>Manual decks and trackers are hard to sustain across multi-year programs.</p></div>
<div class="card"><div class="icon green">SC</div><h3>Shared platforms</h3><p>Central technology, PMO, change, and vendor costs need transparent allocation.</p></div>
<div class="card"><div class="icon">PE</div><h3>Value creation plans</h3><p>Portfolio companies need repeatable transformation governance after the initial plan.</p></div>
</div>

---

<!-- _class: section -->

# 02

## The Product: one governed workspace from setup to realized value.

---

# Product Map

<div class="flow">
<div class="node"><div class="step">01</div><h3>Set up tenant</h3><p>Roles, master data, fiscal settings, stage gates.</p></div>
<div class="node"><div class="step">02</div><h3>Create initiatives</h3><p>Scope, owners, workstreams, KPIs, risks, dependencies.</p></div>
<div class="node"><div class="step">03</div><h3>Build value case</h3><p>Benefits, costs, scenarios, formulas, baselines.</p></div>
<div class="node"><div class="step">04</div><h3>Govern and lock</h3><p>Gate criteria, Finance validation, bankable plan.</p></div>
<div class="node"><div class="step">05</div><h3>Track realization</h3><p>Actuals, waterline, shared costs, Control Tower.</p></div>
</div>

<div class="pill-row" style="margin-top:28px;">
<span class="pill">Dashboard</span><span class="pill">Financial Overview</span><span class="pill">Benefits Register</span><span class="pill">Bankable Plan</span><span class="pill">Benefit Tracking</span><span class="pill">Shared Costs</span><span class="pill">Control Tower</span>
</div>

---

# Product Pillars

<div class="grid-3">
<div class="card">
<div class="icon">G</div>
<h3>Governed setup</h3>
<p>Tenant onboarding, master data, RBAC, stage gates, criteria, fiscal calendar.</p>
</div>
<div class="card">
<div class="icon green">$</div>
<h3>Finance engine</h3>
<p>Metrics, formulas, scenarios, baselines, cost categories, value bridge.</p>
</div>
<div class="card">
<div class="icon amber">V</div>
<h3>Value assurance</h3>
<p>Benefits Register, Bankable Plan, Benefit Tracking, Waterline.</p>
</div>
</div>
<div class="grid-3" style="margin-top:16px;">
<div class="card">
<div class="icon">PM</div>
<h3>Operating cadence</h3>
<p>Pipeline, milestones, KPIs, risks, dependencies, progress, governance.</p>
</div>
<div class="card">
<div class="icon green">SC</div>
<h3>Shared-cost burdening</h3>
<p>Pools, policies, weights, previews, locked runs, report treatment.</p>
</div>
<div class="card">
<div class="icon">AI</div>
<h3>AI with guardrails</h3>
<p>Tenant-aware assistant, Langfuse tracing, human-in-the-loop write actions.</p>
</div>
</div>

---

# Implemented Product Surface

<div class="browser">
<div class="browser-bar"><span>Transmuter navigation</span><span>Angular 21 SPA</span></div>
<div class="screen-body">
<div class="grid-4">
<div class="mini-card"><b>Admin</b><span>tenant setup</span></div>
<div class="mini-card"><b>Dashboard</b><span>executive readout</span></div>
<div class="mini-card"><b>Financials</b><span>value bridge</span></div>
<div class="mini-card"><b>Initiatives</b><span>pipeline and detail</span></div>
<div class="mini-card"><b>Benefits</b><span>register and tracking</span></div>
<div class="mini-card"><b>Bankable</b><span>locked plan</span></div>
<div class="mini-card"><b>Shared Costs</b><span>allocation engine</span></div>
<div class="mini-card"><b>Control Tower</b><span>board view</span></div>
<div class="mini-card"><b>Progress</b><span>milestones</span></div>
<div class="mini-card"><b>PMO</b><span>governance, KPIs, risks</span></div>
<div class="mini-card"><b>People</b><span>roles and access</span></div>
<div class="mini-card"><b>AI Insights</b><span>assistant context</span></div>
</div>
</div>
</div>

---

<!-- _class: section -->

# 03

## Proof: ACME demo scenario shows the end-to-end value story.

---

# ACME Portfolio Snapshot

<div class="grid-4">
<div class="stat"><div class="value">10</div><div class="label">initiatives</div></div>
<div class="stat"><div class="value">$20.0M</div><div class="label">FY26 revenue baseline</div></div>
<div class="stat"><div class="value">$9.0M</div><div class="label">FY26 GM baseline</div></div>
<div class="stat"><div class="value">$8.35M</div><div class="label">FY28 net run-rate</div></div>
</div>

<div class="grid-2" style="margin-top:24px;">
<div class="card">
<h3>Portfolio themes</h3>
<div class="pill-row" style="margin-top:12px;"><span class="pill">Automation</span><span class="pill">Commercial growth</span><span class="pill">Offshoring</span><span class="pill">Procurement</span><span class="pill">ERP and data</span></div>
</div>
<div class="card">
<h3>Demo readiness</h3>
<p>Built from blank tenant setup through financial configuration, initiatives, KPIs, risks, milestones, benefits, bankable plan, tracking, shared costs, and dashboards.</p>
</div>
</div>

---

# ACME Value Bridge

<div class="split-wide">
<div>
<h2>FY28 EBITDA-effective net run-rate is a finance-readable bridge, not a single optimistic headline.</h2>
<div class="card" style="margin-top:24px;">
<p class="quote" style="font-size:26px;">$5.40M GM uplift + $3.75M cost savings - $0.80M recurring cost = $8.35M net run-rate.</p>
</div>
</div>
<div class="card">
<h3>FY28 value drivers</h3>
<div class="bar-row"><span class="name">Revenue uplift</span><span class="bar-shell"><span class="bar steel w74"></span></span><span class="num">$4.00M</span></div>
<div class="bar-row"><span class="name">GM uplift</span><span class="bar-shell"><span class="bar green w100"></span></span><span class="num">$5.40M</span></div>
<div class="bar-row"><span class="name">Cost savings</span><span class="bar-shell"><span class="bar green w69"></span></span><span class="num">$3.75M</span></div>
<div class="bar-row"><span class="name">Recurring cost</span><span class="bar-shell"><span class="bar amber w15"></span></span><span class="num">-$0.80M</span></div>
<div class="bar-row"><span class="name">One-off investment</span><span class="bar-shell"><span class="bar red w46"></span></span><span class="num">$2.50M</span></div>
<div class="bar-row"><span class="name">Net run-rate</span><span class="bar-shell"><span class="bar green w100"></span></span><span class="num">$8.35M</span></div>
</div>
</div>

---

# Benefit Tracking Proof

<div class="split-wide">
<div>
<h2>ACME demonstrates plan, bankable baseline, actual realization, and variance.</h2>
<div class="grid-3" style="margin-top:22px;">
<div class="stat"><div class="value">$9.15M</div><div class="label">locked baseline</div></div>
<div class="stat"><div class="value">$8.16M</div><div class="label">realized actual</div></div>
<div class="stat"><div class="value">-$0.99M</div><div class="label">variance</div></div>
</div>
</div>
<div class="card">
<h3>Realization bridge</h3>
<div class="bar-row"><span class="name">Locked</span><span class="bar-shell"><span class="bar green w100"></span></span><span class="num">$9.15M</span></div>
<div class="bar-row"><span class="name">Actual</span><span class="bar-shell"><span class="bar green w89"></span></span><span class="num">$8.16M</span></div>
<div class="bar-row"><span class="name">Gap</span><span class="bar-shell"><span class="bar red w11"></span></span><span class="num">-$0.99M</span></div>
<p class="caption">Use Benefit Tracking and Waterline for plan-vs-realization governance.</p>
</div>
</div>

---

# Shared Cost Proof

<div class="grid-4">
<div class="stat"><div class="value">4</div><div class="label">FY28 pools</div></div>
<div class="stat"><div class="value">9</div><div class="label">allocation methods</div></div>
<div class="stat"><div class="value">$1.45M</div><div class="label">allocated plan</div></div>
<div class="stat"><div class="value">$1.305M</div><div class="label">actual allocation</div></div>
</div>

<div class="grid-2" style="margin-top:24px;">
<div class="card">
<h3>Allocation methods in ACME3</h3>
<div class="pill-row"><span class="pill">Benefit weighted</span><span class="pill">Equal split</span><span class="pill">Fixed percentage</span><span class="pill">Manual amount</span></div>
</div>
<div class="card">
<h3>Finance principle</h3>
<p>Direct initiative economics remain owner-accountable. Control Tower can show fully loaded economics after central PMO, platform, change, and vendor costs are allocated.</p>
</div>
</div>

---

<!-- _class: section -->

# 04

## Platform Walkthrough: how a live demo should flow.

---

# Walkthrough Map

<div class="timeline">
<div class="item"><h3>1. Admin</h3><p>Configure tenant, roles, master data, finance engine, gates.</p></div>
<div class="item"><h3>2. Pipeline</h3><p>Create initiatives and show portfolio segmentation.</p></div>
<div class="item"><h3>3. Financials</h3><p>Build benefits, costs, baselines, scenarios, value bridge.</p></div>
<div class="item"><h3>4. Governance</h3><p>Validate benefits and lock the bankable plan.</p></div>
<div class="item"><h3>5. Realization</h3><p>Track actuals, variance, waterline, KPIs, risks.</p></div>
<div class="item"><h3>6. Control Tower</h3><p>Show executive value, burden, dependencies, attention.</p></div>
</div>

---

# 1. Tenant Setup and Financial Engine

<div class="split-wide">
<div class="browser">
<div class="browser-bar"><span>Admin / Financial Configuration</span><span>first-run setup</span></div>
<div class="screen-body">
<div class="mini-grid">
<div class="mini-card"><b>USD</b><span>reporting currency</span></div>
<div class="mini-card"><b>Jan</b><span>fiscal start</span></div>
<div class="mini-card"><b>4</b><span>scenarios</span></div>
</div>
<div class="bar-row"><span class="name">Master data</span><span class="bar-shell"><span class="bar green w100"></span></span><span class="num">Done</span></div>
<div class="bar-row"><span class="name">Metrics</span><span class="bar-shell"><span class="bar green w100"></span></span><span class="num">10</span></div>
<div class="bar-row"><span class="name">Cost cats</span><span class="bar-shell"><span class="bar green w80"></span></span><span class="num">8</span></div>
<div class="bar-row"><span class="name">Stage gates</span><span class="bar-shell"><span class="bar green w100"></span></span><span class="num">5</span></div>
</div>
</div>
<div>
<h2>Start with a clean tenant, not a hardcoded demo.</h2>
<ul>
<li>Business units, workstreams, markets, themes, tags.</li>
<li>Scenarios, metrics, formulas, baselines, cost categories.</li>
<li>Stage gates and criteria before initiative creation.</li>
</ul>
</div>
</div>

---

# 2. Executive Dashboard

<div class="split-wide">
<div>
<h2>Open with portfolio health and value concentration.</h2>
<div class="icon-row" style="margin-top:22px;">
<div class="icon-card"><div class="icon">10</div><p>Initiatives in flight</p></div>
<div class="icon-card"><div class="icon green">$</div><p>Executive value cards</p></div>
<div class="icon-card"><div class="icon amber">R</div><p>Risk and KPI pulse</p></div>
</div>
</div>
<div class="browser">
<div class="browser-bar"><span>Dashboard</span><span>executive readout</span></div>
<div class="screen-body">
<div class="mini-grid">
<div class="mini-card"><b>10</b><span>portfolio count</span></div>
<div class="mini-card"><b>2</b><span>amber initiatives</span></div>
<div class="mini-card"><b>$8.35M</b><span>FY28 net</span></div>
</div>
<div class="matrix" style="grid-template-columns:1fr repeat(3,1fr); margin-top:14px;">
<div class="head">Workstream</div><div class="head">Automation</div><div class="head">Commercial</div><div class="head">Offshoring</div>
<div>Automation</div><div class="hot">$1.4M</div><div>-</div><div>-</div>
<div>Commercial</div><div class="warm">$0.8M</div><div class="hot">$3.4M</div><div>-</div>
<div>Procurement</div><div class="warm">$0.5M</div><div>-</div><div class="hot">$0.9M</div>
</div>
</div>
</div>
</div>

---

# 3. Initiative Pipeline and Detail

<div class="split-wide">
<div class="browser">
<div class="browser-bar"><span>Initiatives / Pipeline</span><span>operating list</span></div>
<div class="screen-body">
<div class="app-nav"><span>Commercial Growth</span><span>Automation</span><span>Offshoring</span><span>Executing</span></div>
<div class="mini-card" style="margin-bottom:10px;"><b>ENT-006</b><span>Pricing and discount optimization / commercial growth / green</span></div>
<div class="mini-card" style="margin-bottom:10px;"><b>ENT-005</b><span>Enterprise data platform / ERP and data / amber</span></div>
<div class="mini-card"><b>ENT-009</b><span>Supply chain control tower / procurement / amber</span></div>
</div>
</div>
<div>
<h2>Drill from portfolio to the initiative source of truth.</h2>
<ul>
<li>Owner, sponsor, stage, RAG, dimensions.</li>
<li>Financial scope, benefits, costs, baselines.</li>
<li>Milestones, KPIs, risks, dependencies, governance.</li>
</ul>
</div>
</div>

---

# 4. Financial Overview

<div class="split-wide">
<div>
<h2>Show direct initiative economics before shared-cost burdening.</h2>
<div class="grid-2" style="margin-top:24px;">
<div class="stat"><div class="value">$9.15M</div><div class="label">benefits</div></div>
<div class="stat"><div class="value">$0.80M</div><div class="label">recurring costs</div></div>
<div class="stat"><div class="value">$8.35M</div><div class="label">net run-rate</div></div>
<div class="stat"><div class="value">$2.50M</div><div class="label">one-off investment</div></div>
</div>
</div>
<div class="card">
<h3>FY28 value bridge</h3>
<div class="bar-row"><span class="name">GM uplift</span><span class="bar-shell"><span class="bar green w92"></span></span><span class="num">$5.40M</span></div>
<div class="bar-row"><span class="name">Savings</span><span class="bar-shell"><span class="bar green w64"></span></span><span class="num">$3.75M</span></div>
<div class="bar-row"><span class="name">Run cost</span><span class="bar-shell"><span class="bar amber w14"></span></span><span class="num">$0.80M</span></div>
<div class="bar-row"><span class="name">Net</span><span class="bar-shell"><span class="bar green w100"></span></span><span class="num">$8.35M</span></div>
<p class="caption">Financial Overview is direct-only by default.</p>
</div>
</div>

---

# 5. Benefits Register

<div class="split-wide">
<div class="browser">
<div class="browser-bar"><span>Financials / Benefits Register</span><span>finance control sheet</span></div>
<div class="screen-body">
<table class="mini-table">
<tr><th>Line</th><th>Status</th><th>Owner</th><th>Value</th></tr>
<tr><td>ENT-006 pricing uplift</td><td>Finance validated</td><td>Commercial</td><td>$1.20M</td></tr>
<tr><td>ENT-009 savings</td><td>Rejected</td><td>Operations</td><td>$0.30M</td></tr>
<tr><td>ENT-005 platform benefit</td><td>Submitted</td><td>Technology</td><td>$0.80M</td></tr>
</table>
</div>
</div>
<div>
<h2>Separate proposed value from validated value.</h2>
<ul>
<li>Draft, submitted, validated, rejected.</li>
<li>Evidence labels and realization owner.</li>
<li>Risk adjustment and bankable amount where configured.</li>
</ul>
</div>
</div>

---

# 6. Bankable Plan and Benefit Tracking

<div class="grid-2">
<div class="card">
<div class="icon green">BP</div>
<h3>Bankable Plan</h3>
<p>Locks the approved value case after gate approval. Future performance is compared to a controlled baseline.</p>
<div class="bar-row"><span class="name">Approved</span><span class="bar-shell"><span class="bar green w100"></span></span><span class="num">v1</span></div>
<div class="bar-row"><span class="name">Rebaseline</span><span class="bar-shell"><span class="bar amber w35"></span></span><span class="num">ENT-005</span></div>
</div>
<div class="card">
<div class="icon">BT</div>
<h3>Benefit Tracking</h3>
<p>Turns locked plans into realized-value conversations across portfolio, workstream, and initiative views.</p>
<div class="bar-row"><span class="name">Locked</span><span class="bar-shell"><span class="bar green w100"></span></span><span class="num">$9.15M</span></div>
<div class="bar-row"><span class="name">Actual</span><span class="bar-shell"><span class="bar green w89"></span></span><span class="num">$8.16M</span></div>
<div class="bar-row"><span class="name">Gap</span><span class="bar-shell"><span class="bar red w11"></span></span><span class="num">-$0.99M</span></div>
</div>
</div>

---

# 7. Shared Costs Workbench

<div class="split-wide">
<div>
<h2>Keep owner accountability and fully loaded economics separate.</h2>
<p>Finance configures pools, allocation policies, targets, weights, previews, locked runs, and reporting treatment.</p>
<div class="pill-row"><span class="pill">Equal split</span><span class="pill">Benefit weighted</span><span class="pill">Fixed %</span><span class="pill">Manual amount</span><span class="pill">Metric weighted</span></div>
</div>
<div class="browser">
<div class="browser-bar"><span>Shared Costs</span><span>allocation run preview</span></div>
<div class="screen-body">
<div class="mini-grid">
<div class="mini-card"><b>$650K</b><span>platform burden</span></div>
<div class="mini-card"><b>$420K</b><span>PMO burden</span></div>
<div class="mini-card"><b>$200K</b><span>change burden</span></div>
</div>
<div class="bar-row"><span class="name">Reconciled</span><span class="bar-shell"><span class="bar green w100"></span></span><span class="num">100%</span></div>
<div class="bar-row"><span class="name">Locked runs</span><span class="bar-shell"><span class="bar green w75"></span></span><span class="num">4</span></div>
</div>
</div>
</div>

---

# 8. Executive Control Tower

<div class="split-wide">
<div class="browser">
<div class="browser-bar"><span>Reports / Control Tower</span><span>2028</span></div>
<div class="screen-body">
<div class="mini-grid">
<div class="mini-card"><b>$8.35M</b><span>net before allocation</span></div>
<div class="mini-card"><b>$1.45M</b><span>allocated cost</span></div>
<div class="mini-card"><b>$1.40M</b><span>net after allocation proof</span></div>
</div>
<div style="margin-top:14px;">
<div class="bar-row"><span class="name">Value</span><span class="bar-shell"><span class="bar green w88"></span></span><span class="num">Strong</span></div>
<div class="bar-row"><span class="name">Risk</span><span class="bar-shell"><span class="bar amber w42"></span></span><span class="num">Amber</span></div>
<div class="bar-row"><span class="name">Dependency</span><span class="bar-shell"><span class="bar red w25"></span></span><span class="num">Watch</span></div>
</div>
</div>
</div>
<div>
<h2>End with the executive operating view.</h2>
<ul>
<li>Direct costs plus allocated shared costs.</li>
<li>Net before and after allocation.</li>
<li>Dependency risk and initiatives needing attention.</li>
<li>Persona views for management, investor, and owner.</li>
</ul>
</div>
</div>

---

<!-- _class: section -->

# 05

## Audience Section: Investors

---

# Investor Thesis

<div class="split-wide">
<div>
<h2>Transmuter productizes transformation value assurance into recurring SaaS workflows.</h2>
<div class="pill-row" style="margin-top:20px;"><span class="pill">Enterprise transformation</span><span class="pill">CFO controls</span><span class="pill">Board reporting</span><span class="pill">AI governed workflows</span></div>
</div>
<div class="card">
<h3>Wedge</h3>
<p>Land with transformation offices that need finance-grade value control. Expand into board packs, benefit realization, shared-cost burdening, AI copilot workflows, and partner-led deployments.</p>
</div>
</div>

---

# ICP and GTM Motion

<div class="grid-3">
<div class="card"><div class="icon">PE</div><h3>Private equity</h3><p>Value creation plans across portfolio companies.</p></div>
<div class="card"><div class="icon green">CFO</div><h3>CFO-led programs</h3><p>Margin, working-capital, cost, and transformation value assurance.</p></div>
<div class="card"><div class="icon">PMO</div><h3>Transformation offices</h3><p>Multi-workstream programs that have outgrown spreadsheet governance.</p></div>
</div>
<div class="flow" style="margin-top:24px;">
<div class="node"><div class="step">Land</div><h3>ACME demo</h3><p>Show full tenant value story.</p></div>
<div class="node"><div class="step">Deploy</div><h3>Starter tenant</h3><p>First 10 to 25 initiatives.</p></div>
<div class="node"><div class="step">Expand</div><h3>Finance controls</h3><p>Benefits, bankable plan, tracking.</p></div>
<div class="node"><div class="step">Scale</div><h3>Executives</h3><p>Control Tower and board packs.</p></div>
<div class="node"><div class="step">Channel</div><h3>Partners</h3><p>Consulting and operating partners.</p></div>
</div>

---

# Business Model Visual

<div class="grid-3">
<div class="card">
<div class="icon">S</div>
<h3>Starter</h3>
<p>Fewer than 50 users. Transformation office entry point.</p>
</div>
<div class="card">
<div class="icon green">G</div>
<h3>Growth</h3>
<p>50 to 100 users. Multi-workstream operating cadence.</p>
</div>
<div class="card">
<div class="icon amber">E</div>
<h3>Enterprise</h3>
<p>More than 100 users. Security, support, custom scale, partner motion.</p>
</div>
</div>

<div class="card" style="margin-top:24px;">
<h3>Expansion vectors</h3>
<div class="pill-row"><span class="pill">More tenants</span><span class="pill">More owners</span><span class="pill">Board reporting</span><span class="pill">Shared costs</span><span class="pill">AI workflows</span><span class="pill">Partner rollout</span></div>
</div>

---

# Defensibility

<div class="matrix">
<div class="head">Moat layer</div><div class="head">Why it compounds</div><div class="head">Evidence in product</div><div class="head">Buyer value</div><div class="head">Expansion path</div>
<div>Operating data</div><div class="hot">Initiatives, risks, KPIs, costs, gates live together</div><div>Pipeline, detail, PMO</div><div>Less manual reconciliation</div><div>More workflows</div>
<div>Finance controls</div><div class="hot">Validated benefits and locked baselines</div><div>Benefits Register, Bankable Plan</div><div>CFO confidence</div><div>Realization tracking</div>
<div>Shared costs</div><div class="hot">Fully loaded economics are hard to model manually</div><div>Allocation engine</div><div>Board clarity</div><div>Advanced reporting</div>
<div>Tenant trust</div><div class="hot">Security model is core architecture</div><div>RLS, JWT, RBAC</div><div>Enterprise procurement</div><div>Larger tenants</div>
</div>

---

# Investor Proof and Open Inputs

<div class="grid-2">
<div class="card">
<h3>What is already evidenced</h3>
<ul>
<li>Production app and documented deployment flow.</li>
<li>End-to-end ACME demo guide.</li>
<li>Financial engine, bankable plan, benefit tracking, shared costs.</li>
<li>CI gates, security review trail, RLS hardening.</li>
</ul>
</div>
<div class="card">
<h3>Founder inputs still required</h3>
<ul>
<li>ARR, customers, pilots, pipeline.</li>
<li>Target ACV and pricing proof.</li>
<li>Market sizing and segment data.</li>
<li>Funding ask, team bios, use of funds.</li>
</ul>
</div>
</div>

---

<!-- _class: section -->

# 06

## Audience Section: Board Members

---

# Board Control Room

<div class="split-wide">
<div>
<h2>The board should not have to ask whether a number came from a spreadsheet, a deck, or an approved plan.</h2>
<p>Transmuter creates one chain from value case to governance approval to realized benefit.</p>
</div>
<div class="card">
<h3>Board questions answered</h3>
<div class="bar-row"><span class="name">What is approved?</span><span class="bar-shell"><span class="bar green w100"></span></span><span class="num">Bankable</span></div>
<div class="bar-row"><span class="name">What is realized?</span><span class="bar-shell"><span class="bar green w89"></span></span><span class="num">Actuals</span></div>
<div class="bar-row"><span class="name">What is at risk?</span><span class="bar-shell"><span class="bar amber w42"></span></span><span class="num">Risks</span></div>
<div class="bar-row"><span class="name">What is fully loaded?</span><span class="bar-shell"><span class="bar steel w75"></span></span><span class="num">Burdened</span></div>
</div>
</div>

---

# Board Pack Blueprint

<div class="grid-3">
<div class="card"><div class="icon green">$</div><h3>Value bridge</h3><p>Direct and burdened value, benefit drivers, costs, net run-rate.</p></div>
<div class="card"><div class="icon">BP</div><h3>Bankable baseline</h3><p>Approved plan versions and rebaseline history.</p></div>
<div class="card"><div class="icon amber">R</div><h3>Risk exposure</h3><p>Risks, dependencies, stale KPIs, initiatives needing attention.</p></div>
</div>
<div class="grid-3" style="margin-top:16px;">
<div class="card"><div class="icon">WT</div><h3>Waterline</h3><p>Approved targets versus actual realization by workstream.</p></div>
<div class="card"><div class="icon green">SC</div><h3>Shared costs</h3><p>Central burden allocation and fully loaded economics.</p></div>
<div class="card"><div class="icon">G</div><h3>Governance</h3><p>Stage gates, criteria completion, approvals, exceptions.</p></div>
</div>

---

# Board Cadence

<div class="timeline">
<div class="item"><h3>Dashboard</h3><p>Portfolio health and value concentration.</p></div>
<div class="item"><h3>Financials</h3><p>Direct value, costs, plan-vs-actual.</p></div>
<div class="item"><h3>Bankable</h3><p>Locked approved value and rebaseline trail.</p></div>
<div class="item"><h3>Tracking</h3><p>Actual realization and variance.</p></div>
<div class="item"><h3>Shared Costs</h3><p>Central burden and fully loaded view.</p></div>
<div class="item"><h3>Risks</h3><p>Decisions, escalations, owner accountability.</p></div>
</div>

---

<!-- _class: section -->

# 07

## Audience Section: CEO, CFO, COO

---

# CEO: Strategy to Intervention

<div class="split-wide">
<div>
<h2>CEO question: Are we creating the value we promised, and where do I need to intervene?</h2>
<div class="pill-row"><span class="pill">Portfolio health</span><span class="pill">Value concentration</span><span class="pill">Escalations</span><span class="pill">Board narrative</span></div>
</div>
<div class="card">
<h3>CEO dashboard</h3>
<div class="bar-row"><span class="name">FY28 value</span><span class="bar-shell"><span class="bar green w100"></span></span><span class="num">$8.35M</span></div>
<div class="bar-row"><span class="name">Amber initiatives</span><span class="bar-shell"><span class="bar amber w20"></span></span><span class="num">2 of 10</span></div>
<div class="bar-row"><span class="name">Executive focus</span><span class="bar-shell"><span class="bar red w28"></span></span><span class="num">ENT-005</span></div>
</div>
</div>

---

# CFO: Assurance and Reconciliation

<div class="split-wide">
<div class="card">
<h3>CFO control stack</h3>
<div class="flow" style="grid-template-columns: repeat(4, 1fr);">
<div class="node"><div class="step">1</div><h3>Submitted</h3><p>Owner claims.</p></div>
<div class="node"><div class="step">2</div><h3>Validated</h3><p>Finance checks.</p></div>
<div class="node"><div class="step">3</div><h3>Bankable</h3><p>Gate lock.</p></div>
<div class="node"><div class="step">4</div><h3>Realized</h3><p>Actual ledger.</p></div>
</div>
</div>
<div>
<h2>CFO question: Which value is validated, bankable, realized, and fully loaded?</h2>
<ul>
<li>Money precision: PostgreSQL NUMERIC(15,4), Python Decimal, JSON strings.</li>
<li>One-off, recurring, direct, and shared-cost treatment are explicit.</li>
<li>Reports reconcile to initiative financials and benefit lines.</li>
</ul>
</div>
</div>

---

# COO: Delivery Reality

<div class="split-wide">
<div>
<h2>COO question: Is execution moving fast enough to land the financial case?</h2>
<ul>
<li>Milestones and roadmap expose timing health.</li>
<li>KPIs prove operational movement.</li>
<li>Risks and dependencies show blockers before value slips.</li>
<li>Governance connects delivery readiness to stage movement.</li>
</ul>
</div>
<div class="card">
<h3>COO execution view</h3>
<div class="bar-row"><span class="name">Milestone health</span><span class="bar-shell"><span class="bar green w76"></span></span><span class="num">Good</span></div>
<div class="bar-row"><span class="name">KPI coverage</span><span class="bar-shell"><span class="bar green w82"></span></span><span class="num">High</span></div>
<div class="bar-row"><span class="name">Dependencies</span><span class="bar-shell"><span class="bar amber w38"></span></span><span class="num">Watch</span></div>
<div class="bar-row"><span class="name">Risks</span><span class="bar-shell"><span class="bar amber w46"></span></span><span class="num">Amber</span></div>
</div>
</div>

---

# C-Suite Operating Rhythm

<div class="matrix">
<div class="head">Cadence</div><div class="head">CEO</div><div class="head">CFO</div><div class="head">COO</div><div class="head">Platform source</div>
<div>Weekly</div><div>Escalations</div><div>Validation exceptions</div><div>Milestones and blockers</div><div class="hot">Dashboard, Risks, Progress</div>
<div>Monthly</div><div>Portfolio value</div><div>Plan vs actual</div><div>Workstream delivery</div><div class="hot">Financials, Tracking, KPIs</div>
<div>Quarterly</div><div>Board narrative</div><div>Waterline, rebaseline</div><div>Capacity and dependencies</div><div class="hot">Control Tower, Bankable Plan</div>
</div>

---

<!-- _class: section -->

# 08

## Audience Section: Transformation Office and Initiative Owners

---

# Transformation Office Operating System

<div class="grid-3">
<div class="card"><div class="icon">1</div><h3>Configure</h3><p>Tenant setup, dimensions, financial engine, gates, users.</p></div>
<div class="card"><div class="icon">2</div><h3>Mobilize</h3><p>Create initiatives, assign owners, set stage and value scope.</p></div>
<div class="card"><div class="icon">3</div><h3>Govern</h3><p>Review criteria, validate benefits, lock bankable plan.</p></div>
</div>
<div class="grid-3" style="margin-top:16px;">
<div class="card"><div class="icon green">4</div><h3>Track</h3><p>Actuals, milestones, KPIs, risks, dependencies, status.</p></div>
<div class="card"><div class="icon amber">5</div><h3>Allocate</h3><p>Shared costs, previews, approvals, locked runs.</p></div>
<div class="card"><div class="icon">6</div><h3>Report</h3><p>Dashboard, financials, Control Tower, board pack.</p></div>
</div>

---

# Initiative Owner Workspace

<div class="split-wide">
<div class="browser">
<div class="browser-bar"><span>Initiative / ENT-006</span><span>source of truth</span></div>
<div class="screen-body">
<div class="mini-grid">
<div class="mini-card"><b>Green</b><span>RAG</span></div>
<div class="mini-card"><b>$1.2M</b><span>benefit</span></div>
<div class="mini-card"><b>Gate 2</b><span>approved</span></div>
</div>
<div class="app-nav"><span>Overview</span><span>Financials</span><span>Milestones</span><span>KPIs</span><span>Risks</span></div>
<div class="bar-row"><span class="name">Evidence</span><span class="bar-shell"><span class="bar green w88"></span></span><span class="num">Ready</span></div>
<div class="bar-row"><span class="name">Milestones</span><span class="bar-shell"><span class="bar green w72"></span></span><span class="num">On track</span></div>
</div>
</div>
<div>
<h2>The owner knows exactly what they are accountable for.</h2>
<ul>
<li>Direct economics and assumptions.</li>
<li>Operational KPIs and delivery milestones.</li>
<li>Risks, dependencies, and evidence.</li>
<li>Status updates and gate readiness.</li>
</ul>
</div>
</div>

---

# Weekly Transformation Office Cadence

<div class="matrix">
<div class="head">Meeting topic</div><div class="head">Question</div><div class="head">Primary view</div><div class="head">Owner</div><div class="head">Output</div>
<div>Portfolio health</div><div>Where is value at risk?</div><div class="hot">Dashboard</div><div>TO lead</div><div>Escalation list</div>
<div>Finance validation</div><div>Which claims are bankable?</div><div class="hot">Benefits Register</div><div>CFO delegate</div><div>Validation decisions</div>
<div>Delivery</div><div>What is late or blocked?</div><div class="hot">Progress, KPIs, Risks</div><div>Owners</div><div>Actions</div>
<div>Realization</div><div>What moved into actuals?</div><div class="hot">Benefit Tracking</div><div>Finance</div><div>Variance notes</div>
<div>Executive readout</div><div>What should leadership decide?</div><div class="hot">Control Tower</div><div>TO lead</div><div>Board/ELT pack</div>
</div>

---

<!-- _class: section -->

# 09

## Architecture, Security, and Trust

---

# Architecture at a Glance

<div class="flow">
<div class="node"><div class="step">UI</div><h3>Angular 21</h3><p>Standalone SPA, lazy routes, design tokens.</p></div>
<div class="node"><div class="step">API</div><h3>FastAPI</h3><p>Router, service, repository layers.</p></div>
<div class="node"><div class="step">DB</div><h3>Supabase</h3><p>PostgreSQL 15, Auth, RLS.</p></div>
<div class="node"><div class="step">AI</div><h3>PydanticAI</h3><p>OpenRouter gateway, HITL writes.</p></div>
<div class="node"><div class="step">Ops</div><h3>Langfuse</h3><p>Tracing, evals, observability.</p></div>
</div>

<div class="card" style="margin-top:26px;">
<h3>Deployment context</h3>
<p class="small">Production app: https://transmuter.ishirock.tech. Dev app: https://transmuter-dev.ishirock.tech. Docker/Traefik/Hostinger production stack is documented in the repo.</p>
</div>

---

# Trust Controls

<div class="grid-3">
<div class="card"><div class="icon">RLS</div><h3>Tenant isolation</h3><p>Every tenant table uses tenant_id; RLS policies enforce tenant boundaries.</p></div>
<div class="card"><div class="icon green">JWT</div><h3>Scoped access</h3><p>JWT context carries user, tenant, and role into API and DB access patterns.</p></div>
<div class="card"><div class="icon">$</div><h3>Finance precision</h3><p>NUMERIC(15,4), Python Decimal, and string JSON money responses.</p></div>
</div>
<div class="grid-3" style="margin-top:16px;">
<div class="card"><div class="icon amber">PII</div><h3>AI safety</h3><p>Raw PII must not be sent to external LLM APIs.</p></div>
<div class="card"><div class="icon">HITL</div><h3>Write control</h3><p>Agent write actions require human confirmation before DB mutation.</p></div>
<div class="card"><div class="icon green">CI</div><h3>Release gates</h3><p>Backend checks, frontend build, workflow validation, secret scan.</p></div>
</div>

---

# Current Release Reality

<div class="grid-2">
<div class="card">
<h3>Promoted</h3>
<ul>
<li>Shared Costs configurable allocation engine.</li>
<li>Financial Configuration Engine consolidation.</li>
<li>Bankable Plan, Benefit Tracking, Benefits Register, Waterline.</li>
<li>Control Tower burdened-value views.</li>
</ul>
</div>
<div class="card">
<h3>Known caveat</h3>
<p>Production ACME seeded data is not yet at full dev ACME3 parity. The schema, API, and UI are live, but the complete ACME3 demo-data parity backfill is tracked in issue #304.</p>
</div>
</div>

---

<!-- _class: section -->

# 10

## Closing Narrative

---

# What Transmuter Replaces

<div class="split-wide">
<div class="card">
<h3>Before</h3>
<div class="icon-row">
<div class="icon-card"><div class="icon red">XL</div><p>Spreadsheet trackers</p></div>
<div class="icon-card"><div class="icon red">PP</div><p>Static board decks</p></div>
<div class="icon-card"><div class="icon red">BI</div><p>Downstream dashboards</p></div>
<div class="icon-card"><div class="icon red">$</div><p>Offline finance models</p></div>
</div>
</div>
<div class="card">
<h3>After</h3>
<div class="icon-row">
<div class="icon-card"><div class="icon green">OS</div><p>Transformation operating system</p></div>
<div class="icon-card"><div class="icon green">BP</div><p>Bankable benefit control</p></div>
<div class="icon-card"><div class="icon green">CT</div><p>Live executive control tower</p></div>
<div class="icon-card"><div class="icon green">AI</div><p>Guarded portfolio assistant</p></div>
</div>
</div>
</div>

---

# Audience-Specific Close

<div class="matrix">
<div class="head">Audience</div><div class="head">Message</div><div class="head">Proof screen</div><div class="head">Metric</div><div class="head">Next action</div>
<div>Investors</div><div>Transformation value assurance can become a durable SaaS category.</div><div>Product map</div><div>Tenants, ACV, value tracked</div><div>Add commercial metrics</div>
<div>Board</div><div>Value commitments become auditable and risk-aware.</div><div>Control Tower</div><div>Bankable vs realized</div><div>Run quarterly pack</div>
<div>CEO</div><div>One view of value, risk, and intervention.</div><div>Dashboard</div><div>Net run-rate</div><div>Escalate blockers</div>
<div>CFO</div><div>Submitted, validated, bankable, realized, and fully loaded value are separate.</div><div>Financials</div><div>Variance</div><div>Validate benefits</div>
<div>COO</div><div>Execution health is connected to value.</div><div>Progress / PMO</div><div>Milestones, KPIs, risks</div><div>Clear dependencies</div>
<div>TO and owners</div><div>The weekly operating cadence has one system of record.</div><div>Pipeline / detail</div><div>Owner accountability</div><div>Run the demo guide</div>
</div>

---

<!-- _class: dark -->

# Transmuter

## Govern transformation value from idea to realized EBITDA.

<div class="grid-4" style="margin-top:42px;">
<div class="card dark-card"><h3>Plan</h3><p>Initiatives, scenarios, baselines.</p></div>
<div class="card dark-card"><h3>Approve</h3><p>Stage gates and bankable plan.</p></div>
<div class="card dark-card"><h3>Realize</h3><p>Actuals, waterline, variance.</p></div>
<div class="card dark-card"><h3>Report</h3><p>Executive dashboard and Control Tower.</p></div>
</div>

---

# Appendix: Demo Script

<div class="timeline">
<div class="item"><h3>Admin</h3><p>Show blank tenant setup and financial engine.</p></div>
<div class="item"><h3>Dashboard</h3><p>Show portfolio health and value matrix.</p></div>
<div class="item"><h3>Initiative</h3><p>Open ENT-006 or ENT-005 for detail.</p></div>
<div class="item"><h3>Financials</h3><p>Explain FY28 direct value.</p></div>
<div class="item"><h3>Benefits</h3><p>Show validation, bankable plan, tracking.</p></div>
<div class="item"><h3>Control Tower</h3><p>Show fully loaded economics and risk.</p></div>
</div>

---

# Appendix: Source Guides Reviewed

<ul class="source-list">
<li>README.md</li>
<li>docs/team/CODEX_CONTEXT.md</li>
<li>docs/team/ARCHITECTURE.md</li>
<li>docs/team/RELEASE_MANIFEST.md</li>
<li>docs/team/TENANT_ONBOARDING_USER_GUIDE.md</li>
<li>docs/user-guides/acme-demo-tenant-ui-setup-guide.md</li>
<li>docs/user-guides/acme-transformation-office-detailed-setup-and-demo-guide.md</li>
<li>docs/user-guides/acme-transformation-value-demonstration-guide.md</li>
<li>docs/user-guides/admin-financial-configuration-user-guide.md</li>
<li>Angular routes and navigation under apps/web/src/app.</li>
</ul>

---

# Appendix: Pitch Deck References

<ul class="source-list">
<li>Sequoia, "Writing a Business Plan": https://sequoiacap.com/article/writing-a-business-plan/</li>
<li>Y Combinator, "How to build your seed round pitch deck": https://www.ycombinator.com/library/2u-how-to-build-your-seed-round-pitch-deck</li>
<li>Guy Kawasaki, "The Only 10 Slides You Need in Your Pitch": https://guykawasaki.com/the-only-10-slides-you-need-in-your-pitch/</li>
<li>NFX Pitch Deck Library: https://www.nfx.com/post/the-nfx-pitch-deck-library</li>
</ul>
