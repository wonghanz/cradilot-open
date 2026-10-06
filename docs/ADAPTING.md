# Adapting Cradilot to your own business

The README's [Make it yours](../README.md#make-it-yours) covers the three environment
variables. This file covers what happens after that: the data files you replace, the
code that reads them, and what breaks if you replace one and not the other.

Work through it in this order. Each step is independently verifiable, so if a test
goes red you know which step caused it.

```
1. identity        env vars only                      → 5 minutes
2. price list      data/product_catalog.json          → the work
3. SKU references  core/site_audit.py + 3 test files  → where step 2 bites back
4. industries      data/industry_catalog.json         → only for a new market
5. market law      PDPA / currency / company suffix   → only beyond Malaysia
```

---

## 1. Identity

| Variable | Reaches |
|---|---|
| `CRADILOT_VENDOR_NAME` | console header, PDF letterhead and footer, talk tracks, every "who is selling" sentence |
| `CRADILOT_VENDOR_DOMAIN` | PDF contact line |
| `CRADILOT_VENDOR_TAGLINE` | API description, report subtitle |
| `CRADILOT_REPORT_PREFIX` | the `CRDL-…` case reference on report IDs |

Nothing else needs touching. `static/index.html` carries `{{VENDOR_NAME}}` markers that
`serve_index()` fills at request time, and `tests/test_ui_integrity.py` fails if a
company name is ever hardcoded into the markup again — so the substitution cannot drift
back.

Verify:

```bash
python -m pytest tests/test_ui_integrity.py -q
curl -s http://<server-address>:8000/ | grep -o "<your vendor name>" | head -1
```

---

## 2. Your price list

`data/product_catalog.json` is the only source of every quoted amount. The loader is
`core/product_catalog.py`; point at your own file with `CRADILOT_PRODUCT_CATALOG`
rather than overwriting the sample, so the diff stays readable.

### Structure

```jsonc
{
  "_meta": {
    "status":            "free-text label shown wherever the catalogue is quoted",
    "currency":          "MYR",              // appears in the PDF and the console
    "annualization_rule":"how a monthly figure becomes a yearly one",
    "renewal_caveat":    "printed next to every first-year price",
    "verify_legend":     { "official": "…", "to_verify": "…", "not_priced": "…" },
    "confirmed_partner_tiers": []            // only what you can prove in writing
  },
  "products": [ /* one object per SKU */ ],
  "bundles":  { /* optional named groups of SKUs */ }
}
```

### Product fields

| Field | Required | What reads it |
|---|---|---|
| `sku` | **yes** | the join key everywhere: roadmap lines, cart, audit mapping, tests |
| `name` | **yes** | customer-facing text |
| `category` | yes | grouping; unknown values fall back to `"other"` |
| `billing` | no | default `"Annual"` |
| `annual_myr` | **yes to be priced** | if absent, the line can only be described in words |
| `verify_status` | no | default `"to_verify"` — see the legend below |
| `includes` | no | bullet list in the blueprint |
| `solves` | no | the sentence tying the SKU to a pain point |
| `source` | recommended | where the price came from; quote it when a customer argues |
| `note` | no | caveat text |

Per-seat and per-device products use `annual_myr_per_user`, `annual_myr_per_device` and
`seats_block` instead of a flat `annual_myr`. One-off work uses `one_off_myr` (or
`one_off_setup_myr`).

### The three verify statuses are load-bearing

`official` may be quoted with an amount. `to_verify` must be confirmed with your own
desk before it goes in front of a customer. `not_priced` may only be *mentioned in
words* — never with a figure. The sample catalogue ships `confirmed_partner_tiers: []`
on purpose: it lists a resold Cloudflare-powered service whose source page publishes no
certification tier, and the wording rule recorded in `_meta` is *say "Cloudflare-powered
managed service", never claim a tier you cannot point to in writing*. Apply the same
rule to your own partnerships.

### Naming your SKUs

The sample uses a `DEMO-` prefix (`DEMO-DOM-COM`, `DEMO-SSL-BUSINESS`). Renaming is
fine, but the strings are referenced outside the catalogue — see step 3.

---

## 3. Where SKUs are referenced

Grep before you rename:

```bash
grep -rn "DEMO-" --include="*.py" --include="*.json" .
```

| Place | Why it holds SKUs |
|---|---|
| `core/site_audit.py` | the website-checklist table maps each finding to the SKUs that resolve it (`["DEMO-CF-BOOSTER-PERSONAL", "DEMO-SSL-BUSINESS"]`). This is what turns "no HTTPS" into a purchasable line item |
| `data/audit_checklist.json` | the same mapping, as data, for the machine checklist (23 probes across 13 modules) |
| `core/recommendation.py` | phase templates and the option-comparison blocks |
| `tests/test_recommendation_option_matrix.py` | 39 SKU references pinning the comparison layer |
| `tests/test_site_audit.py`, `tests/test_audit_checklist_contract.py` | contract tests |

Two honest options:

* **Keep the `DEMO-` keys as opaque identifiers** and only change `name`, prices and
  copy. Fastest; the tests stay green; but a customer could open the PDF and see a
  `DEMO-` code in a cart export, so check the rendered output.
* **Rename properly.** Update the mapping in `core/site_audit.py` and
  `data/audit_checklist.json` in the same commit, then run
  `python -m pytest tests/test_recommendation_option_matrix.py tests/test_site_audit.py -q`
  and fix the fixtures. Budget an hour.

Either way, the invariant to preserve is the one the tests enforce: **a compared-but-
not-sold option must never reach a budget line, a phase total or the cart.** If your
new catalogue makes that false, the catalogue is wrong, not the test.

---

## 4. Industry profiles

`data/industry_catalog.json` is the single source shared by the backend and the
front end — do not add an industry in one place only. Ten Malaysian profiles ship as
the default set.

```jsonc
{
  "val":   "Auto Parts & Hardware Wholesale",   // stored on the dossier
  "label": "same as val, shown in the picker",
  "sub":   "the sentence that makes an owner recognise themselves",
  "en":    ["iot", "sensor*", "firmware"],      // * = prefix match, else whole word
  "zh":    ["物联", "智能硬件"]                    // substring match
}
```

Matching is first-hit-wins in array order, so put narrow profiles before broad ones.
English uses word boundaries (`ai` will not match "Air"); Chinese uses substrings
because there are no word boundaries to find. Malay-English mixed company names are the
norm in the source market, which is why `en` lists carry Malay vocabulary too.

---

## 5. Adapting beyond Malaysia

The engine logic is market-neutral; the *vocabulary* is not. Roughly three dozen files
carry Malaysian-market wording, and they are the last honest layer to replace.

| Assumption | Where | Replace with |
|---|---|---|
| Currency `MYR` / `RM ` strings | `_meta.currency`, field names `annual_myr`, `total_financial_loss_myr`, PDF text, prompt library | your currency; the field *names* are cosmetic but grep for `RM ` before shipping |
| Compliance framing: PDPA, MACC 17A | `core/dev_audit.py`, `llm/prompt_library.py`, audit checklist | your jurisdiction's data-protection and anti-bribery regime — or delete the claims; an unverifiable compliance warning is worse than none |
| Company suffix "Sdn Bhd" | interview copy, prompts, tests' fixtures | your local suffix |
| Business reality: WhatsApp-first quoting, month-end manual reconciliation, 6–20 person teams | `llm/prompt_library.py`, `core/agentic_diagnostic.py` fallbacks, `data/knowledge_base/*` | rewrite for how your market's SMEs actually operate |
| Hourly labour cost and working-hours assumptions | `core/roi_engine.py` | your own — every ROI figure the tool prints is derived from these |
| The 10 industry profiles | `data/industry_catalog.json` | your verticals |

`data/knowledge_base/` holds the two derived files the recommendation layer quotes:
`cradle_framework.json` (the maturity model) and `vendor_rules.json` (partner rules and
named platforms). `scripts/extract_cradle_knowledge.py` rebuilds them, but only from
source documents you supply under `cradle data/` and `cradle data/brief.pdf` — the
originals were third-party material and are not in this repo.

---

## Verification checklist

Before you trust an adapted build in front of a customer:

```bash
python -m pytest -q                          # nothing regressed
python scripts/check_no_secrets.py           # no credential slipped in while editing
curl -s http://<server-address>:8000/api/system/engine-status   # provider + reachable
```

Then run one full interview and read the PDF end to end. Specifically confirm:

- [ ] every amount in the PDF exists in *your* catalogue
- [ ] the vendor name is yours in the header, footer and talk track
- [ ] no `DEMO-` code appears in a customer-facing line
- [ ] a `to_verify` product is not quoted with a hard number
- [ ] with the engine switched off, the scores and prices are unchanged and only the
      prose degrades — that asymmetry is the point of the architecture
