# Cradilot — AI SME Digital Growth Advisor

**the partner · the 2026 partner AI challenge**
Tagline used in the brief: *"Helping SMEs Discover Their Next Digital Step."*

What Cradilot is: an assessment workflow, not a chat box. A Malaysian SME types its name and
website, answers a short business interview, and inside five minutes gets a scored diagnosis, an
evidence trail behind every claim, and a downloadable company-branded blueprint with real MYR
prices. A sales consultant can pick the lead up with the same document.

---

## Where to find each thing the organizer asked for

The submission is judged on six weighted criteria and the video must cover six mandated parts. This
table is the route through the document; the video's own timings live in
[`Cradilot-Demo-Video-Script.md`](Cradilot-Demo-Video-Script.md).

| Required part of the submission | Where it is here | Criterion it serves |
|---|---|---|
| 1 · Problem statement and objectives | §1 | Industrial problem-solving value — 25% |
| 2 · Proposed solution, its innovation, target users | §2, in three named layers | AI innovation & technical — 25%; UX & design — 15% |
| 3 · Technical approach and design | §5 | AI innovation & technical — 25% |
| 4 · Functional prototype demonstration | §2's step table, plus the demo script | Presentation & demonstration — 15% |
| 5 · Testing and validation | §3 and §6 | AI innovation — 25%; Industry impact — 20% |
| 6 · Industry value and future potential | §4 and §7 | Industry impact & feasibility — 20% |

The founder's background and practical experience are in **§0**, ahead of the problem, because the firsthand experience with Cradle Fund's institutional governance model is where the method in §2 layer 3 came from. The one boundary that governs how it may be described outward: **no past grant amount, no clause text, nothing confidential from any agreement** appears anywhere in this document, the blueprint or the video.

## 0. Who built this, and why that bears on the method

Cradilot was founded by an entrepreneur who has **personally applied for, navigated the rigorous due diligence of, and successfully received grant funding from Cradle Fund in the past**. 

That firsthand experience belongs at the front of this pitch for one reason only, and it is not as a credential: **Cradle Fund is Malaysia's premier government agency mandated to support, nurture, and standardize SMEs and startups.** In that national role, Cradle Fund enforces strict, milestone-gated governance—funds are never released upfront; the next tranche is only unlocked once the previous milestone has verifiably passed its audit. 

Having lived through that exact discipline, the founder realized that this proven standard is precisely what Malaysia's 95% SMEs are missing in their digital journey. Section 2's layer 3 turns that institutional due-diligence mechanism into an actionable digital transformation advisory blueprint.

**Why importing this experience matters here.** The problems in §1 are not problems of product choice. An SME owner is not short of catalogues; they are short of an honest order of operations, and short of a reason to believe the sequence. Which tool should come first is fundamentally a question of when money should be committed, and what objective evidence must be in hand before taking the next step. That is the exact question a milestone-gated national agency answers for a living, and it is the question Cradilot asks of an SME's budget.

Because of these real-world problems, bringing in this battle-tested experience ensures that SMEs operate under proper laws and statutory standards (CMA 1998, PDPA 2024) with a complete, executable blueprint—rather than falling prey to vendor sales pitches. This is why our probe set is strictly read-only, why intrusive checks were permanently deleted on CMA 1998 s.233 and PDPA grounds, and why the gaps surfaced prioritize legal and operational integrity: an undrilled backup, client records that walk out with a departing staff member, or a database reachable from the public internet.

**Not a claim of endorsement.** Cradilot is our product name. Its first seven letters happen to be an institution's name, so to be explicit: **neither Cradle Fund nor any contest sponsor endorsed, commissioned or co-wrote this entry**, and nothing in this document should be read as their official assessment of it.

---

## 1. The problem, stated the way the customer states it

The brief lists what SMEs cannot answer: where to start, which investment gives the biggest impact,
whether they are ready for AI, which tool to implement first, what it costs, what ROI to expect.
The consequence the brief names is that SMEs buy the wrong tools, waste money, implement in the
wrong sequence, and never realise the value.

Cradilot treats that as a **sequencing and evidence problem**, not an information problem. SMEs are
not short of product pages; they are short of an honest order of operations. So the product does
three things the pitch decks do not:

1. **It measures before it advises.** Everything that can be observed from the public internet is
   measured on the run, in front of the customer, and labelled as measured.
2. **It refuses to score what it did not see.** An item that cannot be checked from outside is
   reported as *not collected* and counted **neutrally** — never as a zero, and never as a gap.
   A zero is reserved for a confirmed absence.
3. **It says no to its own upsell.** While the digital foundation scores below 40, the readiness
   score is hard-locked and Phase 3 (AI spend) is held. Cradilot talks the customer out of an
   expensive AI purchase in the same document where it sells them hosting.

That third point is the "Cradle mindset" in one line: *protect the SME's capital first, and let the
commission follow.* It is the difference between an advisor and a brochure.

**Objectives, and what counts as having met one.**

| Objective | Expected outcome | How it is checked, not asserted |
|---|---|---|
| Give an owner a defensible order of operations, fast enough to use in one sitting | A blueprint the owner can act on and a consultant can quote line by line | A full measured run: 16 interview turns, finalized in **99 seconds**, into a **16-page** PDF with 0 non-English characters |
| Remove the failure mode that makes AI advice untrustworthy in a sales setting | Every figure traceable to where it came from | Three-state provenance on every fact (`machine / owner_stated / inferred`), a printed basis chip per score, and **234 offline contract tests** |
| Give our business-development side a reason to open the conversation that is not a sales pitch | A lead record carrying size, budget, ranked pain points, recommended solutions and an assignee | Field-by-field in `sales/lead_dispatcher.py`, and the same document on both sides |
| Leave the SME no worse off under Malaysian law than before the assessment ran | A check-up that touched nothing it had no business touching | Read-only GET/HEAD and DNS/TLS observation only; the intrusive checks that demoed better were deleted on CMA 1998 s.233 and PDPA grounds |

**Who it is for.** The customer-facing surface assumes an owner who does not read technical output,
which is why the screen shows four conclusions and the PDF carries the 210-row detail. The industries
it ships understanding for are ten, served live from `/api/catalog/industries`: IoT & smart hardware
engineering · IT, software & AI cloud services · auto parts & hardware wholesale · F&B & cloud kitchen ·
professional corporate services · construction & materials · cross-border logistics & haulage ·
retail & multi-store chain · manufacturing & engineering · wholesale & distribution.

## 2. Methodology — Three-Layer Architecture Across Six Operational Steps

The flow is easier to evaluate if it is read in layers, because the three parts answer three different
questions and only the first of them is what the competition brief asked for.

**Layer 1 · The Brief baseline — what any competent hackathon entry delivers.** A profile interview, a machine
audit of the customer's own website, a scored maturity diagnosis, a pain-point list, a three-phase plan
with MYR prices, a company-branded PDF, and a sales lead record on the consultant's side. Steps 0 to 5
below fulfill this baseline. It is the part of the entry that can be compared feature-for-feature against
another team's, and it is deliberately the part we spend least argument on.

**Layer 2 · The Agentic System — how autonomous intelligence and deterministic validation actually run.**
This is the dynamic machinery under the surface that transforms a static checklist into an adaptive advisor:
* **The question order is a function of evidence gaps, not a static script.** The next target is chosen
  from what is still unobservable, adapting dynamically between an automated retailer and a paper-based wholesaler.
* **Site-type gating runs before scoring.** L1–L5 is decided from fetched content, ensuring a brochure site
  is never penalized for a missing cart and a complex web app is never evaluated on a landing page alone.
* **Every answer becomes an immutable evidence node in SQLite.** The thinking chain on screen is that
  live record, ticked only where a verified fact supports the step.
* **Language comes from the model; every number comes from fixed arithmetic.** The model emits three
  things and no others: the question text, the prose around an answer, and a band label that must match
  one of the 16 dimensions' canonical ladders. Everything numeric is a declared weight times a fact
  score, or a catalogue lookup — never a generated figure.
  * **DMS (out of 100):** `cloud` 0.20 · `crm` 0.20 · `website` 0.15 · `marketing` 0.15 ·
    `cybersecurity` 0.15 · `ai_adoption` 0.15.
  * **ARS (out of 100):** `data_availability` 0.25 · `process_maturity` 0.20 · `digital_workflow` 0.20 ·
    `employee_skills` 0.20 · `leadership` 0.15.
  * **ROI — six locked constants:** RM 22.00 default hourly rate (RM 15.00 floor), employer overhead
    1.167, 176.0 standard monthly hours, RM 3,500.00 default monthly salary, RM 120.00 gross margin per
    order, salvage share 0.8. Recoverable hours come from the CRM tier the owner landed in
    (no system / personal WhatsApp / ad hoc → 18.0 h; spreadsheet → 8.0 h; formal CRM → 2.0 h), and
    after-hours orders recovered from the AI tier (none → 14.0/mo, individual use → 9.0, workflow pilot
    → 5.0, deployed → 2.0). Better existing tooling therefore yields a *smaller* claimed saving.
  * **Prices and timelines are looked up, not written.** The SEO retainer is RM 2,288/mo — RM 27,456/yr,
    6-month minimum term — because that is the row in the catalogue; per-seat and per-device lines scale
    off verified headcount and machine count; the phase windows are Quick Wins 2–4 weeks, Productivity
    3–6 months, Growth 6–12 months. Where the model must return structured data it is schema-validated,
    retried once with the failure quoted back, and otherwise replaced by a deep-copied industry template.
    (`core/dms_engine.py`, `core/ars_engine.py`, `core/recommendation.py`, `core/roi_engine.py`,
    `core/product_catalog.py`, `data/product_catalog.json`)
* **A run closes on evidence or on budget, and says which.** `DIAG_TIME_BUDGET_SECONDS = 210`, with a
  benchmarked full run closing `ALL_EVIDENCE_VERIFIED` in 99 seconds.

**Layer 3 · The Cradilot Mindset (Cradle Governance) — the fiduciary rules that govern what Layer 2 is permitted to advise.**
This is where Cradilot ceases to be a sales pitch and becomes a genuine advisor. Borrowed from Cradle Fund's
proven milestone-gated grant discipline (where tranches are unlocked strictly upon verified milestone completion),
this layer enforces strict capital protection and Malaysian statutory compliance:
* **Hard-Lock Capital Protection:** While the digital foundation scores below 40, $\mu(\text{DMS})$ hard-caps
  AI readiness, physically preventing an owner from being sold Phase 3 AI tools when basic digital hygiene is absent.
* **Fiduciary Upsell Refusal:** If an SME's stated monthly ad spend is less than the published cost of an SEO
  retainer (RM 2,288/mo), Cradilot explicitly refuses the upsell and recommends free GA4/Meta Pixel self-setup.
* **Transparent Third-Party Recommendation:** Where a dedicated CRM is required, Cradilot recommends HubSpot or
  Zoho with zero markup, stating plainly that we sell no native standalone CRM.
* **Statutory Compliance & Non-Intrusive Safety:** Built strictly under the Communications and Multimedia Act
  1998 (CMA 1998 s.233) and the Personal Data Protection Act (PDPA 2024). Intrusive penetration tests, port sweeps,
  and credential stuffing were permanently deleted in favor of safe, passive observation.
* **Neutral Unknowns:** Uncollected facts score neutrally; 0 is reserved strictly for confirmed absence.

### Master Overview: The Six Operational Steps across Three Layers

| Step | What happens | Layer 1 · Brief Baseline Requirement | Layer 2 · How Agentic System Works | Layer 3 · Cradilot Mindset (Cradle Governance) |
|---|---|---|---|---|
| **0 · Start** | Types company name & initiates diagnostic | Named session, user-friendly entry point | Generates UUID, binds SQLite wiki dossier, initializes 210s time budget, injects industry prior | Zero PII barrier; no phone/card gate; ephemeral sandboxed session; no ad telemetry |
| **1 · Business Discovery** | 7 baseline profile questions | Brief's "~5 smart questions" (name, industry, size, turnover, challenge, 12mo goal) | Captures 7th dimension **Current digital tools**; normalizes tokens via `sql_wiki_engine._stated_tool_tokens` | Free-text escape on every turn; self-reported tools labeled `owner_stated` (fallback only, never verified machine fact); unstated = `not collected` |
| **2 · Technical Audit** | Automated site & domain inspection | Automated diagnostic of SME website & digital footprint | 210 items across 13 modules executed in 1 pass; L1–L5 site-type gating; 4 executive cards + 210-row expandable toggle | CMA 1998 s.233 & PDPA 2024 compliance (passive GET/HEAD/DNS only); 55 unmeasurable items excluded from denominator; 82 conversion checks map to only 6 real SKUs |
| **3 · Contextual Interview** | Adaptive Q&A confirming operational facts | Interactive dialogue identifying internal workflow gaps | Entropy-driven next-question selection; 16 dimensions (11 primary + 5 deep dives); live Thinking Chain linked to SQLite nodes | Dual safety exits ("Not sure" & "Other"); "Not sure" costs 0 pts; Ask-then-Review ledger separation prevents premature confirmation bias |
| **4 · Objective Scoring** | DMS & ARS scores computed | DMS (6 dimensions) & ARS (5 factors) | Deterministic Python calculation (`dms_engine`, `ars_engine`); 3-state provenance chips (`[Measured]`, `[Stated]`, `[Inferred]`) | Cradle Capital Hard-Lock: $\mu(\text{DMS})$ caps ARS at 10 if DMS < 40; `unknown` always scores above `none`; 234 contract tests prevent LLM hallucination |
| **5 · Phased Blueprint** | Actionable roadmap, quotation & handover | 3 phases (Quick Wins, Productivity, Growth), our product cart, CRM lead dispatch | Dynamic catalog pricing from `product_catalog.json`; 7-question option comparison matrices; programmatic ROI engine | Refuses upsells below budget; recommends 3rd-party CRM at RM 0 markup; unquoted usage printed as "needs a quote"; conservative ROI shrinks as maturity rises |

---

### Step 0 — Start / Session Initialization & Sandbox Setup

* **Layer 1 · Brief Baseline Requirement:** A clean, welcoming entry screen where the SME owner enters their company name to begin their digital transformation journey.
* **Layer 2 · How Agentic System Works:** The backend engine instantiates a clean session state machine, generates a cryptographically unique session UUID, binds an isolated SQLite evidence dossier (`core/sql_wiki_engine.py`), sets `DIAG_TIME_BUDGET_SECONDS = 210`, and loads one of 10 localized Malaysian industry baselines (`/api/catalog/industries`) to initialize Bayesian prior distributions without hallucinating initial data.
* **Layer 3 · Cradilot Mindset (Cradle Governance):** Zero-friction, zero-PII barrier. The SME owner is not forced through an aggressive lead capture form, credit card prompt, or phone verification before receiving value. The session is completely sandboxed, respects executive time (target completion under 2 minutes), and uses zero third-party advertising tracking scripts.

### Step 1 — Business Discovery (Baseline Profile & Current Tools)

* **Layer 1 · Brief Baseline Requirement:** The contest brief's requirement for approximately five smart questions capturing company name, industry, headcount, annual turnover, primary business challenge, and 12-month digital goals.
* **Layer 2 · How Agentic System Works:** Cradilot captures a critical 7th dimension: **"Current digital tools"**, asked as its own explicit question. Owner responses are recorded verbatim and tokenized through `core/sql_wiki_engine.py` (`_stated_tool_tokens`) against canonical software categories (e.g., AutoCount, SQL Accounting, Bukku, WhatsApp, Excel). These tokens dynamically set prior beliefs and branch downstream interview targets.
* **Layer 3 · Cradilot Mindset (Cradle Governance):** 
  * Every single question carries a *Free-Text Escape* ("Other — I'll describe it") so owners are never forced into inaccurate pre-canned vendor categories.
  * Self-reported tools are strictly recorded under provenance `owner_stated` and used only as a **fallback** input for data availability scoring; they are never falsely promoted to verified machine facts.
  * Silence is never penalized: unstated fields remain strictly marked `not collected` rather than fabricating synthetic averages.

*Narration for demo:* "Before Cradilot advises your business, it asks seven questions — including what you already run your business on. If your tool is not in the list, you type it. If you don't know, we don't guess: that line stays 'not collected'."

---

### Step 2 — The Machine Audit (210-Item Technical Inspection)

* **Layer 1 · Brief Baseline Requirement:** Automated inspection of the SME's website, online assets, and hosting infrastructure to uncover operational bottlenecks, performance lags, and digital weaknesses.
* **Layer 2 · How Agentic System Works:**
  * Single-pass, non-intrusive probe executing **210 structured checks across 13 modules**, mapped directly into the **6 official DMS categories**.
  * **Site-Type Gating (L1–L5):** Automatically determines whether the site is a brochure site (L1), interactive portal (L2), SaaS (L3), e-commerce shop (L4), or cloud platform (L5). A brochure site is judged against 107 applicable checks, never penalized for absent carts or API tokens.
  * **UI Progressive Disclosure:** Frontend surfaces 4 high-level executive cards (`Cloud Hosting & Resilience`, `Security & Exposure`, `Appeal & Conversion Potential`, `AI Coverage of Enquiries`), backed by an interactive expandable `<details>` toggle live-rendering all 210 rows by module with status chips, while the full technical matrix is printed in the 16-page PDF appendix.
* **Layer 3 · Cradilot Mindset (Cradle Governance):**
  * **Strict Malaysian Statutory Compliance:** Built to comply with Section 233 of the Communications and Multimedia Act 1998 (CMA 1998 s.233) and the Personal Data Protection Act (PDPA 2024). All aggressive port scanning, brute-force crawling, and vulnerability fuzzing were permanently eliminated in favor of passive GET/HEAD, DNS, and TLS observation.
  * **Strict Denominator Integrity:** Of the 210 checks, only 155 are measurable from outside. The 55 unobservable items are labeled "Consultant Review" and strictly **excluded from the scoring denominator**. An unobservable check never counts as a zero or a failure; 0 is reserved strictly for confirmed absence.
  * **Remediation Honesty:** 82 conversion items resolve to only 6 distinct our catalogue products. Where an issue has no corresponding our SKU, the system honestly displays no product rather than pushing an irrelevant item.

#### The 210 Audit Checks: Complete Master Table across the 6 Official DMS Categories

This table outlines exactly what Cradilot tests across the 6 categories, showing judges the depth, safety, and business relevance of the automated audit:

| DMS Category & Items | Modules & Levels | What We Are Testing (Core Parameters & Specific Checks) | Verification Method (`how`) | Failure Risk & Business Consequence | Our company Remedy SKU |
|---|---|---|---|---|---|
| **1. Website**<br>*(39 items)* | `infra` (27 items)<br>`perf` (12 items)<br><br>Applicability:<br>L1–L5 | • **Domain & DNS Hygiene**: Domain registrant ownership, domain expiry runway (<30 days alert), DNS TTL hygiene, A/AAAA IPv6 record alignment.<br>• **Network & Latency**: Time to First Byte (TTFB < 800ms target), server response latency, CDN presence.<br>• **Transport Security**: TLS certificate validity, strong cipher suites, automated HTTP→HTTPS 301 redirection.<br>• **Performance & Experience**: Mobile responsive viewport, payload compression (Gzip/Brotli), asset minification, image dimensions & compression. | `passive_http` (18)<br>`passive_dns` (8)<br>`content_parse` (5)<br>`perf_sample` (2)<br>`passive_tls` (2)<br>`passive_tcp_targeted` (1)<br>`internal_access` (2)<br>`interview` (1)<br><br>*36 measurable / 3 review* | Site unreachable or slow (TTFB > 2s loses 40% of mobile visitors); domain expires unnoticed causing complete business downtime; unencrypted HTTP triggers browser security warnings and destroys buyer trust. | `DEMO-WP17-BUSINESS`<br>`DEMO-DOM-MY`<br>`DEMO-DOM-COM`<br>`DEMO-SSL-BUSINESS`<br>`DEMO-CF-BOOSTER-PERSONAL` |
| **2. Cloud & Resilience**<br>*(23 items)* | `cloud` (23 items)<br><br>Applicability:<br>L1–L5 | • **Cloud Asset Identification**: Public cloud infrastructure footprint (AWS/GCP/Our company), public IP geolocation, origin server cloaking.<br>• **Storage & Backup Safety**: Public S3/object storage bucket leakage, bucket ACLs read-only verification.<br>• **Resilience & Continuity**: Automated off-site backup frequency, disaster recovery RTO/RPO runway, snapshot retention schedule, database replication across zones.<br>• **Sovereignty**: Data residency in Malaysian Tier-3 data centers for regulatory compliance. | `internal_access` (9)<br>`passive_http` (6)<br>`interview` (4)<br>`passive_dns` (3)<br>`content_parse` (1)<br><br>*10 measurable / 13 review* | Ransomware or hardware failure wiping unbacked local PC accounting databases; public S3 bucket exposing private customer data; foreign jurisdiction cloud subpoena risks under cross-border data transfer laws. | `DEMO-WP17-BUSINESS`<br>`DEMO-ACRONIS-SRV`<br>`DEMO-ACRONIS-WKS`<br>`DEMO-VPS-C1`<br>`DEMO-CF-BOOSTER-PERSONAL` |
| **3. CRM & Lead Capture**<br>*(15 items)* | `crm` (15 items)<br><br>Applicability:<br>L2–L5 | • **Lead Capture & Ingestion**: Functional contact/quote intake forms, email intake validation, conversion tracking pixels.<br>• **Customer Portal & Self-Service**: Customer self-registration, authenticated portal login, self-service profile edit, secure account recovery workflow.<br>• **Pipeline & Data Segregation**: Centralized customer database vs fragmented personal WhatsApp, quote-to-order linkage, salesperson follow-up ownership traceability, order history visibility. | `content_parse` (7)<br>`internal_access` (6)<br>`passive_http` (1)<br>`interview` (1)<br><br>*8 measurable / 7 review* | Customer inquiries lost in personal WhatsApp when staff resign; no record of who owns open quotes; slow manual quote-to-order reconciliation losing hot commercial deals. | `DEMO-MAIL-PRO-10U`<br>*(Plus direct guidance: recommends dedicated 3rd-party CRMs like HubSpot/Zoho at RM 0 Our company markup since we sell no standalone CRM)* |
| **4. Marketing & Conversion**<br>*(67 items)* | `biz` (29 items)<br>`seo` (19 items)<br>`content` (13 items)<br>`ecom` (6 items)<br><br>Applicability:<br>L1–L5 | • **Technical SEO**: Single clear `<h1>`, title tag length hygiene, descriptive meta tags, canonical URL consistency, OpenGraph social sharing tags, `sitemap.xml` presence, `robots.txt` indexation directives.<br>• **Positioning & Trust Signals**: Clear value proposition above the fold, identifiable target audience, visible Malaysian SSM business registration number, physical office address, copyright date freshness.<br>• **Conversion Friction**: Prominent WhatsApp direct chat button, clickable tel links, clear product/service pricing indicators.<br>• **E-Commerce & Payments**: Storefront engine detection, streamlined checkout flow, trusted payment gateway badges (FPX, credit card, e-wallet), cart abandonment safeguards.<br>• **Statutory Compliance**: Accessible PDPA 2024 privacy policy statement and Terms of Service. | `content_parse` (53)<br>`passive_http` (4)<br>`human_review` (3)<br>`perf_sample` (2)<br>`interview` (2)<br>`internal_access` (2)<br>`external_service` (1)<br><br>*59 measurable / 8 review* | Inability to be indexed on Google search; anonymous website lacking SSM/trust badges scaring corporate buyers; ad traffic bounces because value proposition is buried; abandoned checkouts due to payment friction. | `DEMO-SEO-STANDARD`<br>`DEMO-IWB-STARTER`<br>`DEMO-WP17-BUSINESS`<br>`DEMO-ECOM-STANDARD`<br>`DEMO-CF-BOOSTER-PERSONAL` |
| **5. Cybersecurity & Exposure**<br>*(40 items)* | `api` (14 items)<br>`data` (11 items)<br>`auth` (9 items)<br>`vuln` (6 items)<br><br>Applicability:<br>L1–L5 | • **Secrets & Source Code Exposure**: Publicly reachable `/.env`, `/.git/config`, database dumps (`backup.sql`), server info leaks (`phpinfo.php`), directory listing enabled.<br>• **Client-Side Asset Leakage**: Hardcoded cloud API keys, private tokens, or database credentials embedded in public JS bundles.<br>• **Administrative Attack Surface**: Exposed `/wp-login.php`, `/admin` management paths, lack of brute-force login rate-limiting, missing password complexity policy.<br>• **API & Protocol Surface**: Public Swagger/OpenAPI documentation endpoints, unauthenticated GraphQL introspection, exposed debug routes (`/_debug`), verbose stack traces.<br>• **Software Vulnerability & Headers**: Detected CMS/plugins with published CVE hits, end-of-life PHP/Apache, anti-clickjacking `X-Frame-Options`, Content-Security-Policy (CSP), Strict-Transport-Security (HSTS).<br>• **Non-Intrusive Port Check**: Targeted single-packet reachability test on ports 3306 (MySQL), 5432 (PostgreSQL), 22 (SSH). | `content_parse` (21)<br>`passive_http` (9)<br>`internal_access` (7)<br>`interview` (3)<br><br>*30 measurable / 10 review* | Server compromise via exposed `.env` database passwords; automated brute-force takeover of WordPress admin; public database port leading to total data exfiltration under PDPA statutory penalties. | `DEMO-CF-BOOSTER-PRO`<br>`DEMO-WP17-BUSINESS` |
| **6. AI Adoption & Readiness**<br>*(26 items)* | `ai` (26 items)<br><br>Applicability:<br>L1–L5 | • **Customer Engagement Automation**: Live chat widget presence, automated after-hours AI inquiry responder, instant FAQ deflection.<br>• **LLM Machine Readability**: Structured data readability for AI search engines, existence of `llms.txt`, schema.org semantic tagging for LLM crawlers.<br>• **Operational Automation**: Automated lead qualification workflows, automated quote generation pilot readiness, internal Copilot tool integration.<br>• **AI Governance & Safety**: Seamless human escalation fallback protocols, prevention of hallucinated commitments, data privacy boundary guarding client confidential queries. | `content_parse` (11)<br>`interview` (6)<br>`internal_access` (4)<br>`external_service` (3)<br>`passive_http` (1)<br>`human_review` (1)<br><br>*12 measurable / 14 review* | Lost sales leads arriving after 6 PM or on weekends; invisible to new generative search engines (SearchGPT/Perplexity); staff burning 20+ hours/week manually answering repetitive customer inquiries. | `DEMO-AI-AGENT`<br>`DEMO-SEO-STANDARD`<br>`DEMO-VPS-C1` |

*Summary of master list totals: 39 + 23 + 15 + 67 + 40 + 26 = **210 items** (155 measurable from outside, 55 consultant review).*

#### Verification Methods Breakdown (`how`)

| `how` Method | Total Items | Can it produce a pass or fail? | Measurement Technique |
|---|---|---|---|
| `content_parse` | 98 | **Yes** | Analyzed directly from the initial page fetch. Zero extra HTTP requests. |
| `passive_http` | 39 | **Yes** | Single read-only GET/HEAD request against public URLs on the customer's domain. |
| `internal_access` | 30 | No — consultant review item | Requires authenticated backend or cloud console access; omitted from score denominator. |
| `interview` | 17 | No — asked in Step 3 | Verified directly through business owner dialogue in Step 3. |
| `passive_dns` | 11 | **Yes** | Standard DNS, RDAP, and certificate-transparency record lookups. |
| `human_review` | 4 | No — consultant review item | Subjective branding or qualitative checks evaluated by a our consultant. |
| `perf_sample` | 4 | **Yes** | Live TTFB request timing, payload compression, and asset delivery measurements. |
| `external_service` | 4 | No | Requires third-party search engine API calls; marked as consultant review. |
| `passive_tls` | 2 | **Yes** | Passive TLS cryptographic handshake inspection for cipher suite validity. |
| `passive_tcp_targeted` | 1 | **Yes** | Targeted reachability check for ports 3306/5432/22. **Not an aggressive port sweep.** |

#### The Thirteen Modules and Four Executive Buckets

| Module Code | Category Bucket | Items | Dominant Verification Methods |
|---|---|---|---|
| `biz` — positioning, conversion & trust | conversion | 29 | content_parse 27 |
| `seo` — SEO and indexability | conversion | 19 | content_parse 13, passive_http 3 |
| `crm` — CRM and customer data | conversion | 15 | content_parse 7, internal_access 6 |
| `content` — content, trust & legal | conversion | 13 | content_parse 10, human_review 2 |
| `ecom` — e-commerce and payments | conversion | 6 | content_parse 3 |
| `infra` — website & infrastructure | hosting | 27 | passive_http 15, passive_dns 7 |
| `cloud` — cloud and hosting | hosting | 23 | internal_access 9, passive_http 6 |
| `perf` — performance & availability | hosting | 12 | content_parse 3, passive_http 3 |
| `api` — API surface | security | 14 | content_parse 6, passive_http 4 |
| `data` — data and secrets exposure | security | 11 | content_parse 6, passive_http 3 |
| `auth` — authentication | security | 9 | content_parse 5, internal_access 4 |
| `vuln` — web vulnerabilities | security | 6 | content_parse 4 |
| `ai` — AI adoption and AI safety | ai | 26 | content_parse 11, interview 6 |

**Bucket Totals:** `conversion 82` · `hosting 62` · `security 40` · `ai 26` = **210 total items**.
* **Severity Spread:** CRITICAL 22 · HIGH 54 · MEDIUM 95 · LOW 35 · INFO 4. Severity tags are only displayed beside confirmed gaps; internal unknown states are never shown to the customer.
* **Site-Type Applicability Thresholds:** L1: 107 · L2: 36 · L3: 41 · L4: 20 · L5: 6.
* **Reachability of catalogue SKUs:** Hosting (62 items → 9 SKUs) · Conversion (82 items → 6 SKUs) · Security (40 items → 2 SKUs) · AI (26 items → 4 SKUs).

---

### Step 3 — The Contextual Interview (Ask, Then Read Back)

* **Layer 1 · Brief Baseline Requirement:** Interactive consultation asking smart operational questions to understand the SME's software stack, data organization, workflows, and digital pain points.
* **Layer 2 · How Agentic System Works:**
  * **Entropy-Driven Adaptive Routing:** Questions are ordered dynamically by remaining evidence gaps rather than following a rigid script.
  * **16 Structured Dimensions:** 11 first-level probes and 5 deep-dive follow-ups that branch automatically upon confirmed answers.
  * **Strict Canonical Ladders:** Every free-text response is folded onto a deterministic ladder of canonical values (e.g., `backup_strategy`: `single_pc` → `manual_usb` → `cloud_auto`), preventing LLM scoring drift.
  * **Live Visual Thinking Chain:** Displays the exact 4-step reasoning state (*fact recorded, what it costs, guardrail check, next step*), with each step ticked only when backed by an immutable SQLite evidence node.
* **Layer 3 · Cradilot Mindset (Cradle Governance):**
  * **Dual Fiduciary Safety Exits:** Every turn provides "Not sure" and "Other — I'll describe it". Choosing "Not sure" records an open item at neutral weighting without penalizing the score.
  * **Ask-Then-Review Separation:** The evidence ledger opens only after the interview completes, preventing confirmation bias or premature sales anchoring.
  * **Canonical Normalization Invariant:** Prevents silent scoring bugs (e.g. `spreadsheet` is correctly scored as tabular file storage rather than over-scored as enterprise cloud or unfairly zeroed out).

#### The 16 Interview Dimensions and Canonical Ladders

| Dimension | Fact Key | Canonical Ladder (Fragile → Mature) |
|---|---|---|
| `web` | `web_engine_status` | none · outdated · modern |
| `cloud` | `backup_strategy` | single_pc · manual_usb · cloud_auto |
| `crm` | `crm_status` | personal_whatsapp · spreadsheet · formal_crm |
| `marketing` | `marketing_tracker` | none · untracked · pixel_and_ga4 |
| `cyber` | `email_type` | free_gmail · business_domain |
| `ai` | `ai_tier` | none · individual_use · workflow_pilot · deployed |
| `leadership` | `leadership_willingness` | reluctant · conservative · high |
| `employee_skills` | `employee_skill_level` | low · medium · high |
| `process_maturity` | `has_sop` | false · partial · true |
| `digital_workflow` | `order_reconcile_flow` | manual · semi · auto |
| `data_availability` | `data_availability_status` | unstructured · spreadsheet · structured |

Five targeted deep-dives fire upon specific responses: `crm_lead_source` (inquiry attribution), `crm_followup_owner` (sales responsibility), `crm_quote_to_order` (reconciliation mechanism), `crm_pipeline_visible` (deal transparency), and `marketing_channel_mix` (channel allocation & stated monthly budget).

---

### Step 4 — Scores, with the Arithmetic Exposed

* **Layer 1 · Brief Baseline Requirement:** A Digital Maturity Score (DMS) covering 6 key dimensions and an AI Readiness Score (ARS) assessing readiness for advanced automation.
* **Layer 2 · How Agentic System Works:**
  * Deterministic Python mathematical calculation (`core/dms_engine.py`, `core/ars_engine.py`) using fixed weights:
    * **DMS Weights:** `cloud` 0.20 · `crm` 0.20 · `website` 0.15 · `marketing` 0.15 · `cybersecurity` 0.15 · `ai_adoption` 0.15.
    * **ARS Weights:** `data_availability` **0.25** · `process_maturity` 0.20 · `digital_workflow` 0.20 · `employee_skills` 0.20 · `leadership` 0.15.
  * **3-State Provenance Attribution:** Every score factor carries an explicit provenance chip: `[Measured]` / `[You stated]` / `[Inferred]`.
* **Layer 3 · Cradilot Mindset (Cradle Governance):**
  * **Cradle Grant Capital Protection Hard-Lock:** Piecewise multiplier function $\mu(\text{DMS})$ ensures that when DMS < 40, ARS is hard-capped near 10 points:
    $$\mu(\text{DMS}) = \begin{cases} 0.10 & \text{when } \text{DMS} < 40 \quad (\text{ARS capped near 10, full stop}) \\ 0.50 + 0.50 \times \frac{\text{DMS} - 40}{30} & \text{when } 40 \le \text{DMS} < 70 \quad (\text{ramps } 0.50 \to 1.00) \\ 1.00 & \text{when } \text{DMS} \ge 70 \end{cases}$$
    This mathematically forbids the system from recommending expensive Phase 3 AI tools to an SME whose basic digital foundation is broken.
  * **Neutral Unknowns:** `unknown` is an explicit ladder rung positioned strictly above `none`. Uncollected data never defaults to zero.
  * **Anti-Vibe-Coding Integrity:** 234 automated regression tests verify that scores are strictly deterministic and immune to LLM hallucination.

---

### Step 5 — Blueprint, Quotation & Consultant Handover

* **Layer 1 · Brief Baseline Requirement:** An actionable digital transformation roadmap structured into 3 distinct phases (Quick Wins 2–4 weeks, Productivity 3–6 months, Growth 6–12 months), with concrete our product recommendations, timeline, ROI estimates, downloadable branded PDF, and sales lead handover.
* **Layer 2 · How Agentic System Works:**
  * **Live Catalog Pricing Engine:** Looks up exact SKUs and prices from `data/product_catalog.json`, dynamically scaling per-seat and per-device licenses based on verified headcount and machine counts.
  * **7-Dimension Option Comparison Matrices:** Evaluates 2–3 real products for key architectural decisions (email hosting, CMS engine, backup strategy, CRM, order flow, after-hours support, attribution tracking), providing live prices and explicit reasons why competing options were rejected.
  * **Programmatic ROI Engine (`core/roi_engine.py`):** Calculates annual labor savings and night order recovery based on locked evidence tiers:
    $$\text{Labor Savings} = \text{Saved Hours/Wk} \times 52 \times (\text{Hourly Rate} \times 1.167)$$
    $$\text{Salvaged Revenue} = \text{Night Orders Salvaged/Mo} \times \text{Gross Margin} \times 12$$
  * **Sales Lead Dispatch (`sales/lead_dispatcher.py`):** Automatically packages the complete audit trail, stated budget, ranked pain points, and recommended SKUs into an actionable sales lead dossier for our consultants.
* **Layer 3 · Cradilot Mindset (Cradle Governance):**
  * **Refusal of Upsells below Viable Budgets:** If the customer's stated monthly ad budget is below the published monthly cost of the SEO retainer (**RM 2,288/mo**), Cradilot explicitly refuses to sell the retainer and advises free GA4/Meta Pixel self-setup, quoting the price it declined to charge.
  * **Zero-Markup Third-Party Guidance:** Recommends dedicated CRMs (HubSpot, Zoho, Freshsales) at RM 0 Our company markup when Our company has no native fit, refusing to disguise email hosting as a CRM pipeline.
  * **Inverted ROI Discipline:** Better existing tooling yields *smaller* claimed savings, mathematically preventing the engine from inflating ROI figures.
  * **Honest Unquoted Lines:** Unstated usage parameters print as "needs a quote" rather than hallucinating artificial numbers.

#### The 16-Page Blueprint Structure (`typst_generator/compiler.py`)

| Page | Blueprint Section | Contents & Deliverables |
|---|---|---|
| 1 | Cover & Executive Dashboard | Company profile, DMS 6-dimension score radar, 2 weakest digital areas highlighted |
| 2 | Architecture & Why our company | Provenance breakdown (`[Measured]`, `[Stated]`, `[Inferred]`), 4 executive conclusions |
| 3 | Three-Phase Action Roadmap | Quick Wins / Productivity / Growth deliverables, itemized budget lines, pending quote callouts |
| 4 | Cradle Milestone Governance | Tranche release criteria (borrowed from CIP Spark Form A1/A2/A3), acceptance criteria per phase |
| 5 | Acceptance Checklist | Objective phase-completion verification tests ensuring transparency |
| 6 | ROI & Legal Shield | Programmatic ROI calculation, assumptions disclosure, CMA 1998 / PDPA 2024 scope statement |
| A | Technical Inspection Appendix | Full 210-row audit checklist itemizing pass/fail/unverified statuses, severity, and remedy SKUs |


---

## 3. Testing and validation — "is it actually evaluating, or is that a scripted demo?"

This is the question the surface invites, so the product answers it with arithmetic rather than
assurance.

**The readiness score moves when the answers move.** AI readiness is not a constant dressed up per
industry. Three answer sets were pushed through the same weight function with the same digital-maturity
score of 58 — only the facts changed:

| What the owner confirmed | Raw ARS | Final ARS | Factor scores |
|---|---|---|---|
| Paper records, no written SOP, low staff skills, manual document flow | 25.2 | 20.2 | 30 / 15 / 30 / 25 / 30 |
| ERP and CRM, written SOP, keen staff, automated flow | 84.8 | 67.8 | 90 / 85 / 85 / 85 / 80 |
| Nothing collected at all | 53.0 | 42.4 | 50 / 50 / 55 / 55 / 55 |

(Factors in column 4 are leadership, data availability, employee skills, digital workflow, process
maturity, in that order.) The third row is the interesting one: with nothing gathered, every factor
lands on its **neutral** value and every basis reads `inferred_default` — silence neither buys a good
score nor costs one. Nothing in `core/ars_engine.py` holds a per-industry or per-demo lookup table;
there is no branch anywhere that says "if it is the demo company, score 78".

**Each of the five factors the brief names is scored on a stated basis, and the basis is printed.**
Leadership, data availability, employee skills, digital workflow and process maturity each carry a
score, a weight, the one fact it rests on, and a chip saying where that fact came from — *Measured*,
*You stated*, *Inferred*. The scorecard on screen and the ARS matrix in the PDF both show it, so a
reader can see which numbers are observations and which are guesses.

**The same question now feeds a factor.** Step 1 asks what tools the business already runs. The
answer is stored verbatim, tokenised into canonical systems (`_stated_tool_tokens` in
`core/sql_wiki_engine.py`) and used **only** as a fallback for the data-availability factor, always
labelled as owner-stated. It can raise a factor; it can never impersonate a measurement.

**Where the model writes, it writes words, not numbers.** The LLM phrases questions and prose, and may
label an answer with a band that must match one of the 16 dimensions' canonical ladders. Every weight
that turns a band into a score, every MYR price and every hour count is fixed arithmetic whose full
tables are in §2 — the model has no path to them. A structured response is schema-validated, retried
once with the validation error quoted back into the prompt, and otherwise replaced by a deep-copied
industry template. The thinking chain on screen is the run's real state with a tick only where the
evidence record supports the step.

**And the honest number is allowed to look worse.** An item that could not be checked is counted
**neutrally** and labelled *not collected* — it is never silently converted into a zero, and never
into a gap either. 0 is reserved for a confirmed absence. The refusal is asymmetric on purpose: the
engine would rather admit it does not know than manufacture a confident score.

## 4. Impact — what can be pointed at

* **Five minutes is a constraint, not a slogan.** The analysis budget is 210 seconds with per-branch
  deadlines; a probe that runs past its budget is reported as *not verified this run* instead of
  holding the page hostage.
* **210 checks, 4 conclusions, 0 invented numbers.** The machine audit covers what a network
  consultant would look at; the customer only sees what those checks mean for their shop.
* **The refusals are the credibility.** Unverified measurements count neutrally; intrusive checks
  were removed on Malaysian legal grounds (CMA 1998 s.233 and PDPA) rather than kept because they
  demo well; partnership wording is limited to what Our company publishes (Cloudflare is a resold
  managed service, not a certified partnership); product names and MYR prices come from the live
  catalog, and Magento/Shopify are named only as "we do not sell this".
* **A consultant can use it cold.** The same run produces the customer PDF and the internal lead
  record, with notes and assignment fields the brief asked for.

## 5. Specification

**Architecture.** FastAPI + Pydantic v2 backend · vanilla-JS single-page front end (no build step) ·
SQLite as the evidence chain ("LLM Wiki") · Typst for the PDF · one local model
(`cradilot-cradle`, Ollama) for language generation only.

**Decision layers are deterministic.** Six DMS weights summing to 1.00 and five ARS weights summing to
1.00 turn fact scores into the two headline numbers; the piecewise $\mu(\text{DMS})$ cap (0.10 below 40,
ramping 0.50→1.00 across 40–70, 1.00 from 70) gates AI readiness; six locked ROI constants plus the
CRM-hours and AI-orders tier tables produce every MYR saving; prices come from catalogue rows keyed by
SKU; and only `pass + fail` items enter the audit denominator. The LLM writes questions and prose, and
may return a band label validated against the canonical ladders; it never writes a number that reaches a
score or an invoice. Where its output is structured data it is validated and a contextual fallback is
used — deep-copied so it cannot mutate the shared question bank.

**Provenance.** Every claim above names the file and function it comes from at the point it is made, and
`§6` names the check that confirms each brief requirement. Where a figure is a default rather than a
measurement, `core/roi_engine.py` labels it as one on the customer's own page.

**Time budgets.** `DEEP_BUDGET_SECONDS = 18`, `BRANCH_TIMEOUT_SECONDS = 28`,
`PATH_TIMEOUT_SECONDS = 3.5`, `DIAG_TIME_BUDGET_SECONDS = 210`.

**State vocabulary.** Every audit row is one of `pass / fail / unverified / not_applicable /
not_tested`; only `pass + fail` form the score denominator. Every fact carries a source
(`machine / owner_stated / inferred`) and every ROI assumption carries its provenance.

**Interface rules that are enforced, not aspirational.**
English-only customer copy, checked by contract tests over the checklist, the catalog, the audit
prose and the PDF strings; no emoji characters in HTML or JS; no hard-coded conclusions in markup
(every panel is painted from an endpoint, and deleted chrome is pinned as "must stay deleted"); the
liquid-thunder / glacier-glass styling lives in CSS custom properties, and the status orb's five
states are driven by inherited custom properties rather than per-state rules.

Three of these surfaced only by reading the rendered document back, which is why they are asserted
against extracted PDF text or generated Typst source rather than inspected by eye. Typst's automatic
hyphenation is switched off: the blueprint is mostly narrow grid columns, and with the default on,
one run split
customer-facing words 30 times — *Pro - ductivity*, *Data avail - ability*, *cus - tomers* — in the
file a consultant physically hands to an owner. And the appendix prints a severity only beside a
confirmed gap, so the internal `UNKNOWN` sentinel, which appears on 23 never-measured rows, cannot
leak into the customer's document as if it were a risk rating.

A third came from the same read-back and is the most damaging kind, because it is an *honesty label
that lied*. The readiness matrix prefixed every inferred factor with "Not collected this run, counted
neutrally" — while printing 85 / 100 and 90 / 100 two columns to its left. Those values were inferred
from what the customer's stated tools and recorded growth goal imply; they were neither uncollected
nor neutral. The prefix now says only whether the customer confirmed it, matching the chip on screen,
and the neutral-value explanation stays in each factor's own note, where it is actually true.

**Capability boundaries, said out loud.**
Our company has no first-party CRM, so the CRM module checks 15 items and buckets every one of them as
*appeal and conversion* rather than inventing a CRM SKU: 7 of the 15 are only observable from inside
the customer's own console or on a site visit, and at checklist level exactly one of the 15 has a
product that could actually close it. Across the whole conversion bucket — 82 items — only **six**
distinct our SKUs exist. The advisor deliberately leaves gaps unpriced rather than pointing at a
product it cannot deliver, and the consultant call inherits the rest. AI agent products are named but
not priced. The advisor is a lead-generation and advisory tool for our consultants — not an
auditor of other people's systems, and it never sends anything but read requests to the customer's
own site.

## 6. Requirement traceability — the brief, line by line

Checked against `the original brief PDF` on 2026-09-20 against a real end-to-end run
(session `SESS-AABD7872`: 14 interview turns, closed as `ALL_EVIDENCE_VERIFIED`, 102 seconds,
16-page blueprint, 0 CJK characters).

| Brief asks for | Where it is satisfied | How it was checked |
|---|---|---|
| Analyse an SME **in under 5 minutes** | `DIAG_TIME_BUDGET_SECONDS = 210` with per-branch deadlines; a probe that overruns is reported *not verified this run* | Timed live run: 102 s interview, audit inside budget |
| A **personalised** Digital & AI Transformation Blueprint | `typst_generator/compiler.py`; every panel derived from this session's evidence | 16 pages read back as text |
| Practical enough to deploy as a **lead-generation and advisory tool** | `sales/lead_dispatcher.py` | Lead carries size, budget, pain points, solutions, assignee |
| Step 1 · ~5 smart questions: industry, company size, employees, **current digital tools**, biggest challenge, growth objective | Step 1's seven questions (company name, industry, team size, turnover, biggest problem, current tools, 12-month goal) | `test_ui_integrity` pins substeps 1.1–1.7 |
| Step 1 Bonus · AI asks **follow-up questions** | `core/agentic_diagnostic.py`; deep-dive questions fire off a confirmed answer | 14 turns, close reason `ALL_EVIDENCE_VERIFIED` |
| Step 2 · six star-rated dimensions + overall /100 | `core/dms_engine.py`; DMS matrix in the PDF | `DMS fact-diagnosis matrix` present |
| Step 3 · ARS on leadership, data availability, employee skills, digital workflow, process maturity | `core/ars_engine.py`; factor cards on screen and the ARS matrix in the PDF | All five names print whole, each with its basis |
| Step 4 · evidence-based pain points, not generic output | `generate_pain_points`, one quote per finding | Every pain cites a confirmed fact |
| Step 5 · three named phases with their ROI windows | `_PHASE_META` | Quick Wins 2-4 weeks / Productivity / Growth print intact |
| Step 5 · the items the brief lists inside each phase | Email, website, cloud backup (P1); CRM, document flow, structured data (P2); AI enquiry handling, marketing attribution (P3) | See the two partials below |
| **Recommendation engine** · compare real products and explain WHY | Seven comparison blocks in `core/recommendation.py` | 3 comparison sections, 5 question lines, each row reasoned |
| Its two worked examples · Our company email / Google Workspace / Microsoft 365; AI Website Builder / Managed WordPress / Magento / Shopify | Both families carry exactly those candidates | Mail PRO + Workspace + M365; WP Beginner + WP Business + Ecommerce + Instant Website + Magento + Shopify |
| Bonus 1 · estimate potential ROI from hours saved | `core/roi_engine.py`, stated as a range under printed assumptions | `RM` figures present; no percentage before a complete quote |
| Bonus 2 · implementation timeline Month 1-3 → 3-6 → 6-12 | `_PHASE_META[...][2]`, the PDF milestone table and the on-screen phase badge | All three month ranges found in the rendered PDF |
| Bonus 3 · PDF with branding, business summary, maturity, roadmap, ROI, recommended solutions, **consultant notes** | The blueprint | Notes and assignee both print |
| Even Better · create lead → **assign salesperson** → attach report → sales knows size, budget, pain points, solutions | `LeadDispatcher` | Field by field in the lead record |

**Two items the brief names that we have no product for, said plainly.** *Team Collaboration* is
carried by the Google Workspace and Microsoft 365 lines already priced inside the email comparison,
not by a separate SKU. *AI Meeting Assistant* sits in the same bucket as the AI agent — named as a
capability, never priced, because Our company publishes no annual figure for it. The advisor does not
invent a product to fill a row of the brief's example table.

**One internal rule that this audit changed.** The brief gives the Quick Wins window as "ROI 2-4 weeks"
while Bonus 2 gives the implementation timeline as "Month 1-3". Those two disagree for phase 1, so the
engine now carries both: `timeline` is the return window, `months` is when the work runs. The PDF
milestone table prints the month range, the phase card prints the ROI window, and the screen reads
`2-4 weeks · runs Month 1 - 3`.

## 7. Industry value and future potential

The previous six sections say what this run does. This one says how far that reaches, where it stops,
and who would pay.

**What scales without touching a line of code.** Two facts drive the whole product and both live in
JSON. `data/audit_checklist.json` holds all 210 items across 13 modules, each declaring how it must
be verified, which site levels it applies to, which feature signal gates it, how severe a miss is and
which SKU closes it — so changing what gets audited is an edit to a data file, not a rewrite of
`core/site_audit.py`. `data/product_catalog.json` holds the products and MYR prices that every quote
is looked up from, so the entire commercial layer — catalogue, currency, pricing rules — is one file
swap away from a different reseller or a different market. The engines in between know nothing about
either. This is why a second hosting brand could run the same codebase on its own list.

**What is genuinely reusable beyond this brief.** The advisor's hard part is not the audit; it is
sequencing a customer's spend against their own evidence and refusing to price what it cannot close.
That logic is not specific to hosting, and the refusal rules in layer 3 are the portable part.

**The accuracy ceiling, named as a number.** Of the 210 items, **53 are "needs inside access"** — not
visible from the public internet at all, and today they land in the consultant's review list rather
than the score. That single figure is the largest available quality jump: an opt-in read-only
connection to the customer's own hosting or analytics console would move those rows from *not
testable* to *measured*. It is deliberately unbuilt here, because the same capability is exactly what
made the intrusive checks unacceptable in the first place; the boundary that was drawn on CMA 1998
s.233 and PDPA grounds has to be redrawn by consent and credentials before a single one of those 53
items can be closed, not by working around it.

**Three other ceilings, each already visible in the output.** *Pricing*: the AI agent line carries
`verify_status: not_priced`, which is why Phase 3 can name a capability but prints "needs a quote" —
publishing a figure would let Phase 3 carry a number and an ROI percentage for the first time.
*Assortment*: across the whole 82-item conversion bucket only **six** distinct SKUs exist, so most
conversion gaps have no product to point at and the honest remedy stays advisory. *Coverage*: one URL
per run, which is wrong for a group that trades under several brands.

**Longitudinal re-scan is the retention hook.** Every run is a sealed evidence chain keyed by session
in SQLite, and the scores are a pure function of the facts in it. Re-running the same company months
later therefore produces a comparable document rather than a fresh opinion, which is the difference
between a lead-generation one-shot and a quarterly account review a consultant can bill for. Nothing
in the current build schedules or compares runs; the store that makes it possible is already there.

**Who the beneficiary is, and who pays.** The SME's benefit is an order of operations they can defend,
in their own words, with a severity label only where a gap was confirmed. The buyer is not the SME:
the product saves our consultant the part of the sale that is hardest to do well — walking in
with a specific, sourced reason to change something. A lead record already carries team size, budget,
the ranked pain points, the recommended solutions and an assignee, so the preparation before a first
call stops being research and starts being a read-through. The natural commercial shape is a
per-consultant or per-team licence priced against that preparation time and against lead quality, not
a fee to the customer being assessed.

**One adoption risk worth stating before a judge does.** The refusals are the product's credibility and
also its commercial drag: an advisor that tells you to buy nothing will not be measured on close rate
by the team that deploys it. If it is rolled out and scored on immediate conversions, the pressure
will be to switch the refusals off. The scoring denominator — where an unverified item counts
neutrally and never as a gap — is the part to protect in any deployment, because it is the only part
that is expensive to win back once lost.

---

*All numbers, prices and product names in this document come from the repository and
`data/product_catalog.json`; the challenge requirements quoted come from* `the original brief PDF`*.*
