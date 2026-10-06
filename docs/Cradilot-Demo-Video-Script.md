# Cradilot — submission video: 6–10 minute script, shot by shot

**The requirement this is written against:** teams submit a **6–10 minute** prototype demonstration
video covering six mandated parts — (1) problem statement and objectives, (2) proposed solution,
(3) technical approach and design, (4) functional prototype demonstration, (5) testing and
validation, (6) industry value and future potential — scored on six criteria worth
25 / 25 / 20 / 15 / 15 points.

> **This supersedes the 1 minute 50 second cut drafted earlier.** A film that short is a trailer, and a
> trailer aimed at this rubric would be **non-compliant on length and missing four of the six required
> parts**. It is kept out of the way on purpose rather than as an alternative.

**Designed runtime: 9:05. Hard ceiling 9:30,** so a slow read does not push past ten minutes.

---

## 1. Narration is now mandatory, and that reverses my earlier advice

At 1:50 the product could carry the film and captions could subtitle it. At 9:00 the film is an
argument, and an argument cannot be carried by lower-third captions at the rate a judge reads them.
So the order flips: **narration leads, captions support.**

What does not change is the voice. The only speech engines installed on this machine are Windows
SAPI (`Microsoft Zira Desktop`, `Microsoft David Desktop`), and they date from around 2015. A dated
synthetic voice narrating an entry to the *AI Horizon* Solution Challenge argues against the product
louder than any judge's criticism would. Use a neural voice — Clipchamp ships with Windows 11 and
CapCut has the same class of voices free — and record the whole narration in one pass so the tone
does not change mid-film.

**Captions stay, but they change job.** They are no longer the explanation; they are the mute-safe
signposting. One line per part, naming which of the organizer's six sections is on screen, so a judge
skimming with sound off can still tick the rubric. That is the whole reason to burn them in.

**The one place the product's own voice wins**, untouched, is Part 4 while Step 3 asks its question.
Let the machine speak there and drop the narration. It is the most persuasive audio in the film
because it is not narration at all.

---

## 2. The script

Timings are cumulative. `Narration` is meant to be read aloud; word counts are sized to roughly
150 spoken words per minute with room to breathe. `Caption` is burned in. `On screen` is what must be
happening, and nothing in it is invented — see §4 for where each figure was measured.

### Part 0 — Cold Open Vision Teaser & Introduction  ·  0:00–0:40

| | |
|---|---|
| **On screen** | Black screen slowly illuminates with ambient cyan glow (`#00F0FF`). Slow cinematic push-in towards the glowing frosted glass Orb pulsing in the void. Line-by-line typography fades in. Hard cut to the product hero: *"5 Minutes to Find Your Digital Blind Spots."* |
| **Caption** | Cradilot · The Fiduciary SME Digital Growth Advisor |
| **Narration (Apple Keynote "Imagine" Hook)** | *"Imagine an advisor that never tries to sell you software. Imagine an SME owner entering their website, and in just five minutes—getting complete clarity on what to build, what to fix, and what to leave alone. No hype. No aggressive sales pitches. Just pure, honest evidence that protects your capital first. This is Cradilot."* |

> **Slide 01 Transition (0:20–0:40):** Cut directly to Slide 01 (Master Deck Cover).  
> **Speaker Narration:** *"Judges, meet Cradilot. Most AI tools act like sales reps eager to push software. Cradilot acts like a fiduciary advisor: an automated system that diagnoses an SME's true digital standing first, so owners know exactly what to buy, what to fix, and what to ignore."*  
> *(Founder disclosure note: Cradilot was founded by a past Cradle Fund grant recipient; neither Cradle Fund nor any contest sponsor co-wrote this entry).*

### Part 1 — Problem statement and objectives  ·  0:35–1:45  (70 s)

| | |
|---|---|
| **On screen** | Slow push across the seven Step 1 questions being answered; then the four conclusion cards, un-clicked, as the counterexample to "generic output". |
| **Caption** | 1 · Problem statement and objectives |
| **Narration** | "The brief names the problem plainly: an SME owner cannot say where to start, which investment pays back first, whether they are ready for AI, what it costs, or what sequence to do it in. The consequence is money spent in the wrong order on tools that never get used. But there is a second problem on the other side of the table, and it is the one that costs more. A digital consultant has no credible reason to open the conversation. Without evidence, every recommendation reads as a catalogue, and the most expensive line in the catalogue is the easiest one to sell by accident. Cradilot's objective is to give both sides the same artefact: an assessment whose every number can be traced to where it came from, produced in under five minutes, in the owner's language and priced in real ringgit." |

**Objectives belong on screen as a list here** — four lines, one per objective, appearing as the
narration names them (fast enough to be skimmed, real enough to be challenged):

1. A defensible order of operations, inside one sitting.
2. No number anywhere that cannot be traced to its source.
3. A consultant who can open the call with evidence instead of a pitch.
4. An assessment that leaves the SME no worse off under Malaysian law.

### Part 2 — Proposed solution  ·  1:45–2:50  (65 s)

| | |
|---|---|
| **On screen** | A simple three-band diagram building up, then cut to the product at Step 4 showing the basis chips. |
| **Caption** | 2 · Proposed solution — three layers |
| **Narration** | "The solution has three layers, and only the first is what the brief asked for. The base layer is the obvious one: profile interview, machine audit of the company's own website, a scored diagnosis, a three-phase plan with prices, a branded blueprint, and a lead record on the consultant's side. The second layer is the agentic system underneath it, which decides what to ask next from what is still unproven rather than from a script, and decides what may be concluded from what was actually measured. The third layer is the one that makes this an advisor rather than a brochure: a governance rule that decides what the second layer is allowed to sell. Target users are owners of SMEs in ten industries the product ships understanding for — wholesale, F&B, construction, logistics, professional services, manufacturing and the rest — none of whom read a technical report, and all of whom will act on a sequence." |

**On the uniqueness line**, say it once and prove it immediately, because it is checkable:
*"Innovation here is not the model. It is the firewall — the language model writes questions and
prose, and every number that reaches a score, a price or a timeline is computed by a deterministic
engine."*

### Part 3 — Technical approach and design  ·  2:50–4:05  (75 s)

| | |
|---|---|
| **On screen** | Architecture diagram, one box at a time, matched to the file that implements it. Then the thinking-chain strip on screen with a tick landing. |
| **Caption** | 3 · Technical approach and design |
| **Narration** | "FastAPI and Pydantic on the back, a build-step-free single-page front end, SQLite acting as an evidence chain, Typst rendering the document, and one local model — a fine-tuned Gemma running on our own hardware, so no customer fact leaves the building. The audit is driven by a two-hundred-and-ten item checklist held as data, not code: each item declares how it must be verified, which site type it applies to, how severe a miss is, and which product closes it. Only six of the ten verification methods are observable from the public internet, so only those can produce a pass or a fail; the rest become consultant review items and never enter the score denominator. Interview answers are stored as evidence nodes with the owner's own words attached, and the reasoning chain shown on screen is that record — ticked only where a stored fact supports the step. Where the model must return structured data it is schema-validated, retried once with the failure quoted back to it, and otherwise replaced by an industry template that is deep-copied so it cannot poison the shared question bank." |

**Diagrams to prepare** (draw these, do not screen-grab the code):
`browser → API → [audit engine | wiki | engines] → Typst`, with the LLM drawn **outside** the box that
produces numbers. That one visual is the technical claim of the whole entry.

### Part 4 — Functional prototype demonstration  ·  4:05–6:55  (170 s)

**This is the live run and it is the only part that must not be edited for effect.** Real timings
below were measured, not stylised.

| Time | On screen | Narration / sound |
|---|---|---|
| 4:05–4:25 | Step 1. Type the company name; the live industry match appears tagged `[AI recommended match]`. Then click the remaining six profile answers. | "It reads the trade name before it asks — and it asks what the business already runs, as its own question." |
| 4:25–5:00 | **Step 2.** Paste a URL. The progress line runs — this takes **about 23 seconds of real time**, so speed-ramp to roughly 8 s and leave one un-ramped beat so the wait reads as genuine. The four conclusion cards land; hold on the counters. | "Two hundred and ten checks, read-only, from the public internet. A hundred and fifty-one apply to a site of this kind; fifty-three cannot be seen from the public internet at all and go to the consultant instead. The rest come back clear or as confirmed gaps — read that off the screen rather than from me, because a probe that misses its deadline moves between those two columns from run to run." |
| 5:00–5:20 | Click one gap row and show its plain-language explanation and its state word. | "Notice the words. Gap means measured and missing. Not measured means we did not see it — and it is excluded from the score, never converted into a defect." |
| 5:20–6:10 | **Step 3.** The orb breathes; the question streams in token by token. **Let the product's own question be heard here.** Answer by clicking, by label, on camera. Show the read-back line. Then say "Not sure" on one question and show the counter. | *[product voice]* … then: "When the owner says not sure, the question becomes an open item. It does not pull the score down and it does not pretend to be an answer." |
| 6:10–6:25 | The ledger review phase — the evidence map with quotes attached. | "Before it scores anything, it plays the answers back and lets the owner correct the record." |
| 6:25–6:45 | **Step 4.** Scorecard paints. Push in on the ARS row and hold on the basis chips. | "Five readiness factors — leadership, data availability, employee skills, digital workflow, process maturity. Each one carries the fact it rests on and says whether you confirmed it or we inferred it." |
| 6:45–6:55 | **Step 5.** Three phase cards, then scroll to one comparison block. | "And the plan is priced from the live catalogue, per seat and per device, in ringgit." |

### Part 5 — Testing and validation  ·  6:55–8:00  (65 s)

The organizer asks for this to be concrete, so lead with the arithmetic that disproves the obvious
suspicion, then with the harness, then with the discipline.

| | |
|---|---|
| **On screen** | The three-row sensitivity table, then a terminal running the suite, then two or three captured screenshots. |
| **Caption** | 5 · Testing and validation |
| **Narration** | "The obvious suspicion of a product with a score on the screen is that the score is fixed. Three answer sets were pushed through the same weight function with the same digital maturity figure, and only the facts changed: paper records, no written procedures and a manual flow produced an AI readiness of twenty point two; ERP, CRM, written procedures and an automated flow produced sixty-seven point eight; and nothing collected at all produced forty-two point four — every factor landing on its neutral value. An owner's enthusiasm cannot move a number, and neither can ours. Beyond that, two hundred and thirty-four offline contract tests pin the behaviours a customer would notice, including that the five states in the interface and the five in the PDF appendix are the same five words. And three of the defects we found in our own document were only visible by reading the rendered PDF back as text — one run had hyphenated customer-facing words thirty times in the file a consultant physically hands to an owner." |

**The measured sensitivity table, on screen, legible:**

| What the owner confirmed | Raw ARS | Final ARS |
|---|---|---|
| Paper records · no written SOP · low skills · manual flow | 25.2 | **20.2** |
| ERP and CRM · written SOP · keen staff · automated flow | 84.8 | **67.8** |
| Nothing collected at all | 53.0 | **42.4** |

**Screenshots for this part**: five real page captures exist in the pipeline — Playwright driving its
own Chromium against the running server. They are genuine renders, verified by measuring glyph-edge
contrast inside each content band (headline band 5.87, card area 4.73, CTA band 5.06, against ~1.4 on
an empty strip). Two cautions, both earned the hard way: the hero **fades in over 1.3 seconds**, so a
shot taken at `networkidle` catches a half-painted page, and nothing here has been judged by eye —
**look at every image before it goes in the film.**

### Part 6 — Industry value and future potential  ·  8:00–8:50  (50 s)

| | |
|---|---|
| **On screen** | The blueprint's milestone page, then the appendix's "needs inside access" rows, then the end card. |
| **Caption** | 6 · Industry value and future potential |
| **Narration** | "For the SME, the value is an order of operations they can defend, in their own words, with a severity label only where a gap was confirmed. For Our company, the buyer, the value is the hour before a first call: the lead record already carries size, budget, ranked pain points, recommended solutions and an assignee. It scales without code — the checklist and the catalogue are both data files, so a different reseller or a different market is a file swap. We are equally clear about the ceiling: fifty-three of the two hundred and ten items are simply not visible from the public internet, and closing them requires an opt-in, credentialed read of the customer's own console — which is exactly the boundary we drew on legal grounds, so it has to be redrawn by consent and not by working around it. The AI agent line has no published price, so Phase 3 names a capability and asks for a quote. And the honest risk of deployment is this: an advisor that tells you to buy nothing will be measured on close rate, and someone will be tempted to switch the refusals off. That is the part worth protecting." |

### Close  ·  8:50–9:05

| | |
|---|---|
| **On screen** | The 16-page blueprint opening from a real download; first page, appendix, cover. |
| **Caption** | Cradilot — five minutes, evidence first. |
| **Narration** | "Ninety-nine seconds, start to blueprint, and not one number we cannot show you the source of." |

---

## 3. What was measured, so nothing in the script is a guess

| Claim in the film | Source |
|---|---|
| Full run: 16 turns, finalize at **99 s**, **16-page** PDF, 0 CJK characters, all five ARS factors `verified_fact` | End-to-end run `SESS-BC04E55D` against `https://www.vendor.example/` on this machine |
| Audit **≈ 22–24 s**; 210 items · 151 applied · 53 need inside access · site type L5 · **stable across runs**. The clear/gap/not-measured split is **not** stable: two runs of the same URL returned 95 clear / 31 gaps / 25 not measured and 94 / 31 / 26 | Two direct `/api/audit/site` runs plus the appendix header read back out of the rendered PDF text. A probe that misses its deadline moves a row from `pass` to `unverified`, so never narrate that split from memory |
| ARS sensitivity 25.2 → 20.2 · 84.8 → 67.8 · 53.0 → 42.4 | §3 of `Cradilot-Presentation-and-Spec.md`; raw and final both computed |
| **234** offline contract tests passing | `pytest tests/ -q` → `234 passed` this session |
| Ten industries | Live `GET /api/catalog/industries` |
| 53 "needs inside access" · 6 of 10 verification methods measurable · six SKUs across 82 conversion items | `data/audit_checklist.json` and the appendix header printed in the blueprint |
| Screenshots are real renders | Local-gradient measurement per content band |

---

## 4. Take-killer checklist — before every recording, in order

1. **Confirm the server on screen is Cradilot.** This bit for real: `<app-host>:8000` got taken over by a
   different project (`SignalGuard`) while Cradilot's process died, and the open browser tab kept
   displaying the Cradilot title from before the handover — so everything looked fine until someone
   refreshed. **`curl http://<app-host>:8888/api/system/engine-status` must return 200, and a 404 means
   you are pointed at another application.** Cradilot currently runs on **8888**.
2. **Click answers by their label, never by position.** Same prompt, same dimension, and option index
   one came back as *"Manual copy to a USB or external drive"* on one run and *"Automated Cloud Backup"*
   on the next — the model reorders its own options. Click position one on the second take and the
   customer suddenly has a backup, and **Phase 1 renders with 0 tasks and RM 0.0**. Measured, not
   hypothesised.
3. **The AI engine is one machine on the LAN.** `llm/engine_client.py:15` hardcodes
   `http://<ollama-host>:11434`, no `.env`. If it is off, asleep or re-addressed, every AI sentence
   becomes `[Local rule engine mode — the AI engine is currently unavailable]`. Keep the model warm:
   **1.3–1.8 s per generation warm**, against an 8.1 GB cold load.
4. **Two native browser dialogs sit in the flow** — `static/js/app.js:1294` on a failed reasoning step,
   `:720` on an unreachable site. Both freeze the tab and both are 2001 on a glass UI. Either one firing
   ends the take.
5. **Paste the URL, do not type it.** An unresolvable name fails DNS and is reported as *"the probe to a
   private or reserved address was blocked"* in 0.6 s — honest failure, wrong explanation — then
   triggers dialog 4 above.
6. **Do not build the demo around the live microphone.** `app.js:1554` sets `lang = "zh-CN"` on an
   English-only product, `continuous = false` captures one utterance, it is Chromium-only, and the Web
   Speech API streams to Google — on a LAN-only machine it errors and stops silently.
7. **Answer to tell the gap story — but not all the way to the floor.** No website plus "not sure" on all
   sixteen turns still completes — DMS 48.0, ARS 37.4 — but with **0 cart lines, 0 tasks in all three
   phases and no ROI percentage**. The opposite failure is subtler and was observed twice: picking the
   *worst* option on every turn leaves a dimension unconfirmed, so the agent keeps probing it — turns
   9–12 all came back "Digital customer reach" and turns 13–17 all "Structured business data", several
   with near-identical wording. On camera four consecutive cards under one heading does not read as a
   system digging deeper; it reads as a system stuck. **Vary one tier off the floor after two answers in
   the same dimension** so the run moves on, and keep the gap story where it is visible — Step 2's audit.
8. **`reload=True` is on.** No `.py` file may be touched during a take; the watcher restarts the process
   and the in-memory session dies mid-interview. If you want a wording change mid-shoot, stop, change,
   restart, new take.
9. **If I am capturing rather than you: expect ~12 fps.** Measured 11.7 fps at native 3840×1080 with
   captions drawn in. Fine for text and clicks; visibly not smooth on the orb and the token stream.
   And your desktop is **3840×1080, 32:9** — frame a 16:9 browser window or the finished film is the
   wrong shape for any submission portal.
10. **Never open `GET /api/sales/leads` on camera.** It returns every stored lead. The SPA never calls
    it and it is unreachable from the interface — just do not type it.

---

## 5. How to use the still images

Five stage captures and four blueprint page renders come out of the pipeline in
`%TEMP%\cradilot_shots\`. They are genuine renders — Playwright driving the running product on `:8888`
— each certified non-blank by measuring glyph-edge contrast inside its content bands, not by eye.

**Nine rules, in order of how much they cost to break.**

1. **A still never replaces a live step.** The organizer's part 4 asks for a *live demonstration of the
   prototype in operation*. Cutting to a screenshot where Step 2's audit or Step 3's interview should be
   running is a compliance problem, not a taste problem. Stills support the live run; they do not stand
   in for it.
2. **Every still must read as a still.** A frame that is perfectly sharp and perfectly motionless inside
   an otherwise moving film looks like a hang. Say so on screen — `same run · 99 seconds` — or annotate
   it. Never let a judge decide for themselves why the picture stopped.
3. **Give every still motion.** A 3–5% scale or pan across a 3–5 second hold. A dead still in a nine-minute
   film is a slideshow, and the slide show is what makes good footage look cheap.
4. **Crop to the claim, not to the page.** When the narration names the basis chip, show the basis chip —
   a tight crop of one element beats a whole scorecard every time. Full-page frames are for two moments
   only: the hero and the blueprint cover.
5. **Hold a still no longer than five seconds, and never more than two stills per sentence.**
6. **Frame shapes are not interchangeable.** The Playwright page captures come out **exactly 1920×1080**,
   true 16:9, because the browser viewport is decoupled from the physical 3840×1080 desktop — verified
   across every file. The blueprint page renders are **portrait 1310×1853**; dropping one into a 16:9
   slot and stretching it is the single most common way a document looks fake. Set the page at full
   height on the film's own background and let the sides breathe.
7. **Never upscale.** Capture at 1920, export at 1080p, and keep any detail crop at least 640 px wide.
   A crop blown past its own pixels is visible at the exact moment you are asking for trust.
8. **Do not generate imagery of an interface that never ran.** No text-to-video, no "mockup" of a screen.
   This entry sells on the audit trail; a fabricated frame is the one thing that would invalidate the
   rest of it, and it is the trap the whole submission is designed to avoid.
9. **Say which run the image is from.** Every still here came from a single unbroken pass. That sentence is
   free, and it is the difference between a screenshot reel and evidence.

**Placement:**

| Image | Where it goes | Narration it sits under | How to use it |
|---|---|---|---|
| `00_hero.png` | Part 0, after the black card | "…we built Cradilot to supply the reason." | Full frame, slow 4% push-in. Sparse by design: bands 3.9 / 4.2 / 3.2 |
| `01a_step1_industry_match.png` | Part 1 or 2 | "It reads the trade name before it asks." | **Best image in the set** (10.6 / 8.0 / 9.0). Crop to the `[AI recommended match]` tag |
| `02_step2_conclusions.png` | Part 4 freeze, or Part 5 | "…read that off the screen rather than from me." | Bands 7.5 / 3.5 / 3.0 — the detail sits low, so crop to the counters and back to live |
| `03a_step3_question.png` | Part 4 freeze | *[product voice]* | Bands 3.2 / 8.0 / 6.0. Crop to the orb plus one option card |
| `03b_step3_late.png` | Part 4 | "Before it scores anything, it plays the answers back." | Bands 3.6 / 6.4 / 3.1 |
| `04_step4_scorecard.png` | Part 2 or 5 | "Five readiness factors…" | Bands 8.8 / 4.7 / 7.3 |
| `04b_step4_ars_basis.png` | Part 2 or 5 | "…says whether you confirmed it or we inferred it." | **Crop to one basis chip — this is the money detail** |
| `05a_step5_phases.png` | Part 2 close | "And the plan is priced from the live catalogue." | 3 phase cards, bands 12.2 / 11.7 / 9.4 |
| `05b_step5_comparison.png` | Part 4 end, held longest | "…and it is not in our bill." | **Densest frame in the set** (14.5 / 11.6 / 13.8): `Options we compared for this phase` over `What should actually hold your customer records` |
| `pdf_page01.png` | Close | "Ninety-nine seconds, start to blueprint…" | Full height, portrait 1310×1853, side gaps — never stretched |
| `pdf_page15.png` | Part 5 | "…the five states in the interface and the five in the PDF appendix are the same five words." | Crop the legend row |

## 6. Two things this file still cannot promise

**I have not seen a single frame of this product.** The screenshots are verified as real renders by
measuring pixel contrast, not by looking. The orb, the mic ripple, the glass styling and the streaming
animation are correct in the machine and unjudged as pictures — a human eye has to sign off Part 4
and the close, and that sign-off cannot come from me.

**No H.264 encoder exists on this machine.** The only ffmpeg here is Playwright's minimal build, whose
sole useful encoder is VP8, so anything I stitch comes out as `.webm` or MPEG-4 Part 2. That is fine
as an edit source; the final upload should be encoded by Clipchamp or CapCut, which also solves the
neural-voice problem in the same pass.
