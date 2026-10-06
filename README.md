# Cradilot — AI SME Digital Growth Advisor

A consultative sales instrument, not a chatbot. It runs a structured digital-health
interview with a small-business owner, scores what the owner actually said with
deterministic engines, and produces a 6-page PDF blueprint whose every number traces
back to an answer given in the room.

**The one rule everything else follows:** the language model is never allowed to
produce a number. Scores, losses, payback periods and prices come from arithmetic over
verified answers. The model writes prose, asks follow-ups and explains findings — and
when no model is available, it says so instead of pretending.

---

## Where this came from

Built for the **AI Horizon Solution Challenge 2026**, run by **Exabytes Malaysia**.
The submission was titled *AI SME Digital Growth Advisor*, tagline *"Helping SMEs
Discover Their Next Digital Step"*, against this brief:

> "Over 95% of Malaysian businesses are SMEs. Many know they should digitalise or
> adopt AI, but struggle to answer questions like: Where should I start? Which
> investment gives me the biggest impact? Am I ready for AI? Which tools should I
> implement first? How much will it cost? What ROI can I expect?"

The original worked inside one partner's sales motion, so this snapshot has been
stripped of that identity: no company name in the markup, no price list presented as
fact, no internal server addresses, no credentials. What remains is the machinery —
which is the part worth reusing. **See [Make it yours](#make-it-yours) to put your own
company, products and market in its place.**

---

## I want to…

| I want to… | Go to |
|---|---|
| …see it running with my own AI key | [Quick start](#quick-start) |
| …use Gemini / OpenAI / a local model | [Bring your own engine](#bring-your-own-engine) |
| …put my company and price list in it | [Make it yours](#make-it-yours) → [docs/ADAPTING.md](docs/ADAPTING.md) |
| …understand why the numbers can be trusted | [Why the numbers hold up](#why-the-numbers-hold-up) |
| …run it with no AI at all | [Running with no engine](#running-with-no-engine) |
| …know what was removed | [What is not in this snapshot](#what-is-not-in-this-snapshot) |
| …change the market or the currency | [Adapting beyond Malaysia](docs/ADAPTING.md#5-adapting-beyond-malaysia) |

---

## What one run looks like

```
① Company + industry        type a name → 10 industry profiles match on the
                            business's own words, in English or Malay-English mix
② Website audit             real TLS handshake, response headers, tech fingerprint,
                            DNS SPF/DMARC — measured, never assumed
③ Agentic interview         six DMS dimensions, follow-up probes generated per answer,
                            every fact stored with the quote it came from
④ Scorecard                 DMS (6 dimensions) + ARS (5 factors), rule-scored
⑤ Pain points               ranked, each carrying its evidence quote and severity
⑥ Roadmap + ROI             phased plan, options compared side by side, payback
                            computed from the owner's own stated hours and costs
      ↓
   6-page PDF blueprint  ·  sales talk track  ·  cart of purchasable line items
```

24 API routes behind it, server-sent-event streaming for the narrative layers, SQLite
as the evidence store. The console is plain HTML/CSS/JS with no build step.

---

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate    # Python 3.12
pip install -r requirements.txt
cp .env.example .env                                  # then edit it
python app.py
```

The server binds `0.0.0.0` on `$PORT` (default `8000`). Open it at
`http://<server-address>:8000` — on the same machine, that is the address your browser
resolves for the host you are sitting at.

Check the engine really answered before you show anyone:

```bash
curl http://<server-address>:8000/api/system/engine-status
# {"provider": "gemini", "model": "gemini-2.5-flash", "api_key_present": true, "reachable": true, …}
```

`reachable: false` is not a cosmetic warning. It means the prose you are reading came
from the built-in rule engine, and the console labels it as such.

---

## Bring your own engine

One contract, four backends, chosen by environment variables. **No key is committed,
no key is echoed by any endpoint, and `.env` is gitignored.**

| Engine | Set these | Default model | Notes |
|---|---|---|---|
| **Google Gemini** | `CRADILOT_LLM_PROVIDER=gemini`, `GEMINI_API_KEY` | `gemini-2.5-flash` | an AI Studio key; `GOOGLE_API_KEY` also accepted |
| **OpenAI** | `CRADILOT_LLM_PROVIDER=openai`, `OPENAI_API_KEY` | `gpt-4o-mini` | |
| **Any OpenAI-compatible endpoint** | as above + `CRADILOT_OPENAI_BASE_URL` | `gpt-4o-mini` | OpenRouter, DeepSeek, a vLLM or llama.cpp server — same provider, different base URL |
| **Self-hosted Ollama** | `CRADILOT_LLM_PROVIDER=ollama`, `CRADILOT_OLLAMA_URL` | `gemma3:12b` | nothing leaves your network; the URL has **no** default, because a guessed address is how a demo silently runs on canned copy |
| **None** | leave everything blank | — | deterministic engines still score, still price, still produce the PDF |

If you leave `CRADILOT_LLM_PROVIDER` unset, the provider is inferred from whichever
credential is present. Override the model with `CRADILOT_MODEL`.

Keys are read from the environment at startup and never accepted over HTTP — there is
no endpoint that takes a key, so nothing to leak into an access log.

To fine-tune a model on this domain instead, `training/` holds the QLoRA setup
(`pip install -r requirements-train.txt`), and `scripts/deploy_cradilot_model.py`
registers the result into Ollama.

---

## Why the numbers hold up

A sales tool that invents a statistic is not a demo problem, it is a commercial
promise problem. Three mechanisms enforce that, each quoted from the code:

**1. Degraded copy contains no figures at all.** When no engine answers, the text is
written to be useless as a claim:

> "刻意不含任何具体数字或百分比。这里的文字会被销售当成"AI 对贵司的分析"念给 SME 老板听，
> 一旦编造行业统计就是拿假数据做商业承诺。" — `llm/engine_client.py`

*("Deliberately contains no specific numbers or percentages. A salesperson reads this
aloud as "the AI's analysis of your company" — inventing an industry statistic here
turns fake data into a commercial promise.")*

**2. The model may not book money.** Extraction can report a pain point; it cannot
attach a loss figure to it:

> "模型给的 loss_myr 不许入账：那是在替客户编一个他没算过的数字。" — `core/sql_wiki_engine.py`

*("The model's loss_myr is not allowed into the books: that would be inventing a number
the customer never calculated.")*

Money appears only at the ROI stage, allocated from the owner's own inputs, and split
rather than estimated per item so the same saved hours cannot be counted twice:

> "均分而不是各自估一笔：同一批被省下的工时不会既算进 CRM 又算进对账，……" — `core/recommendation.py`

**3. Unmeasured is reported as unmeasured.** A website audit that did not run is
written as "not tested", never as "tested and clean":

> "没测"不能写成"测了且没问题"。 — `core/sql_wiki_engine.py`

These are not comments; they are pinned by tests (`test_pain_roadmap_evidence_bound.py`,
`test_audit_checklist_contract.py`, `test_sql_wiki_and_agentic_loop.py`).

---

## Running with no engine

Deliberately supported, because the deterministic half is the trustworthy half.

* Scores, pain-point ranking, roadmap phasing, pricing and the PDF: **real output,
  quotable as usual.**
* Plain-language readings and talk tracks: **rule-based placeholders that name
  themselves as such** and carry no numbers.

Startup prints the warning, `/api/system/engine-status` reports it, and the console
shows it — so nobody mistakes canned copy for analysis.

---

## Make it yours

Three things, none of them a code edit to the front end:

```bash
# 1. Identity — console header, PDF letterhead, talk tracks, report IDs
CRADILOT_VENDOR_NAME="Northgate Digital"
CRADILOT_VENDOR_DOMAIN=northgate.example
CRADILOT_VENDOR_TAGLINE="Digital Growth Advisory"
CRADILOT_REPORT_PREFIX=NGD

# 2. Your products — replace the sample list
CRADILOT_PRODUCT_CATALOG=./data/my_catalog.json

# 3. Your market — see docs/ADAPTING.md for currency, industry profiles and rules
```

`static/index.html` ships with `{{VENDOR_NAME}}` markers that the server fills from
config, and a test asserts that no company name is ever baked into the markup again.
The sample catalog's 18 SKUs are labelled `SAMPLE DATA - not your price list` in the
file itself; the numbers came from a hosting partner's public pages and are only there
so the pricing and comparison layers have something real-shaped to compute over.

Full walkthrough — schema, which fields are load-bearing, what breaks if you skip one —
in **[docs/ADAPTING.md](docs/ADAPTING.md)**.

---

## Layout

```
app.py                FastAPI surface: 24 routes, SSE streaming, branding injection
config.py             every tunable: engine choice, vendor identity, paths, .env loader
llm/engine_client.py  one contract over Ollama / Gemini / OpenAI-compatible / off
core/
  agentic_diagnostic.py   the interview loop and follow-up probes
  sql_wiki_engine.py      evidence store: facts, quotes, coverage, readiness
  recommendation.py       roadmap phasing, option comparison, loss allocation
  dms_engine / ars_engine deterministic scoring
  web_scraper.py          real TLS/header probes behind an SSRF blocklist
  dev_audit.py            passive security & leaked-credential review
typst_generator/      compiles the 6-page blueprint PDF
data/                 industry catalog, sample product catalog, knowledge base
sales/                lead hand-off: cart, talk track, dispatch
static/               the console — HTML/CSS/JS, no build step
training/             QLoRA config + Modelfile for a specialised model
docs/                 ADAPTING.md + the original pitch and demo scripts
```

## Tests

```bash
pip install -r requirements-dev.txt
python -m pytest -q          # 229 passed, 6 skipped
python scripts/check_no_secrets.py
```

229 tests cover the scoring contracts, the evidence binding, the pricing invariants
(no alternative option may reach a budget line or the cart), the PDF text, and the
UI integrity rules. The 6 skips are the fine-tuning corpus checks: that dataset is
generated, not committed. CI runs the suite on every push along with the credential
scan and a docs-hygiene check that keeps machine-specific addresses out of the
instructions.

---

## What is not in this snapshot

Stated plainly, so you are not surprised later:

* **The contest brief and the partner's internal documents.** The originals are
  third-party material; `docs/` keeps the pitch deck and demo scripts, neutralised.
* **The fine-tuning corpus** (~8 MB of generated SFT/DPO pairs). Recreate it with
  `python scripts/generate_sft_dataset.py`; the integrity tests then un-skip.
* **Any credentials or internal hostnames.** This repo was scanned across every git
  object before publication, and CI keeps scanning.
* **The sample price list is not a price list.** Replace it before quoting anyone.

## License

MIT — see [LICENSE](LICENSE).
