/**
 * Cradilot AI — SME Digital Growth Advisor
 * True Agentic Dynamic Probe Loop Controller
 * Public-internet machine audit (28 tri-state checks) as the evidence source,
 * real-time probe and option generation, visible cognitive reasoning HUD,
 * deterministic pure-function calculations (DMS, ARS, cart-driven ROI),
 * zero emoji characters throughout.
 */

"use strict";

// The company name comes from the page's CRADILOT_BRANDING block, which the server fills
// from config. Fallbacks are role words, so an unconfigured build still reads as honest copy.
const _branding = window.CRADILOT_BRANDING || {};
const BRAND = {
  vendor: _branding.vendor_name || "our consultant",
  domain: _branding.vendor_domain || "",
};

// ─── State ─────────────────────────────────────────────────────────────────────

const state = {
  currentStage: 0,
  totalStages: 6, // 0: Hero, 1: Step 1, 2: Step 2, 3: Dynamic Loop & Workbench, 4: Scorecard, 5: Roadmap/ROI

  // Step 1 sub-step tracking (1 to 6)
  step1Sub: 1,

  // Business Profile
  companyName: "",
  industry: "",
  teamSize: "",
  annualTurnover: "",
  biggestChallenge: "",
  currentTools: "",
  growthObjective: "",

  // Technical facts (Step 2)
  websiteUrl: "",
  websiteStatus: "none",
  webAuditResult: null,

  // SQLite Diagnostic Session
  sessionId: "",
  assessResult: null,
  leadId: "",

  // Live Workbench & Dynamic Loop
  currentTurn: 1,
  exploredCount: 0,
  currentProbe: null,
  diagPhase: "ask",

  // AI-generated Insights
  dmsInsightText: "",
  painPoints: [],
  roadmapPhases: [],
  icebreakerText: "",
};

// ─── DOM Helpers ───────────────────────────────────────────────────────────────

const $ = (id) => document.getElementById(id);
const el = (tag, cls, text) => {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (text !== undefined) e.textContent = text;
  return e;
};

// ─── Stage Navigation & Animations ─────────────────────────────────────────────

function updateProgress(stageIdx) {
  const pct = (stageIdx / (state.totalStages - 1)) * 100;
  if ($("progressFill")) $("progressFill").style.width = pct + "%";

  // Sync Agent Flow Pipeline HUD
  const flowHud = $("agentFlowHud");
  if (flowHud) {
    if (stageIdx >= 1) {
      flowHud.style.display = "flex";
      for (let s = 1; s <= 5; s++) {
        const item = $("flowStep" + s);
        if (item) {
          item.classList.remove("active", "done");
          if (s === stageIdx) item.classList.add("active");
          else if (s < stageIdx) item.classList.add("done");
        }
      }
    } else {
      flowHud.style.display = "none";
    }
  }

  updateTopHud();
}

function updateTopHud() {
  if ($("hudCompanyName")) $("hudCompanyName").textContent = state.companyName || "";
  if ($("hudStagePill")) {
    const stageNames = [
      "Stage 0 · Start",
      "Stage 1 · Business baseline",
      "Stage 2 · Website inspection",
      `Stage 3 · ${state.diagPhase === "review"
        ? "Reviewing what we recorded"
        : `Turn ${state.currentTurn || 1} · Confirming facts`}`,
      "Stage 4 · Diagnostic scorecard",
      "Stage 5 · Growth blueprint"
    ];
    $("hudStagePill").textContent = stageNames[state.currentStage] || "Stage 3";
  }
}

function setOrbState(stateName) {
  const orb = $("appleLiveOrb");
  const label = $("orbStatusLabel");
  if (orb) {
    orb.className = "apple-live-orb state-" + stateName;
  }
  if (label) {
    const labels = {
      idle: "Standing by",
      listening: "Listening to you and writing it down as you speak",
      analyzing: "Turning your answers into facts we can check, and into cost estimates",
      probing: "Asking one more question about the key item we have not confirmed",
      hardlock: "The basics are not firm yet: buying AI now is not advised"
    };
    label.textContent = labels[stateName] || labels.idle;
  }
}

function goTo(targetStage) {
  const currentEl = $("stage-" + state.currentStage);
  const targetEl  = $("stage-" + targetStage);

  if (!targetEl) return;

  if (currentEl) {
    currentEl.classList.add("exit");
    setTimeout(() => {
      currentEl.classList.remove("active", "exit");
      currentEl.style.display = "none";

      targetEl.style.display = "";
      requestAnimationFrame(() => {
        targetEl.classList.add("active");
      });

      state.currentStage = targetStage;
      updateProgress(targetStage);
      window.scrollTo({ top: 0, behavior: "smooth" });

      onStageEnter(targetStage);
    }, 240);
  } else {
    targetEl.style.display = "";
    targetEl.classList.add("active");
    state.currentStage = targetStage;
    updateProgress(targetStage);
    onStageEnter(targetStage);
  }
}

function onStageEnter(stage) {
  if (stage === 1) initStep1Live();
  if (stage === 2) initStep2Live();
  if (stage === 3) initStep3DynamicLoop();
  if (stage === 4) initStage4Scorecard();
  if (stage === 5) initStage5Roadmap();
}

// ─── Step 1: Live Dynamic Sub-Steps (Zero Static Questions) ───────────────────

const step1Labels = {
  1: "Step 1.1 of 7 — Your company name",
  2: "Step 1.2 of 7 — Your main industry",
  3: "Step 1.3 of 7 — Team size",
  4: "Step 1.4 of 7 — Annual turnover",
  5: "Step 1.5 of 7 — Your biggest problem",
  6: "Step 1.6 of 7 — The digital tools you use now",
  7: "Step 1.7 of 7 — Your 12-month goal"
};

function initStep1Live() {
  const t1 = $("title1_1");
  const h1 = $("hint1_1");
  if (t1 && !t1.textContent.trim()) {
    t1.textContent = "First, what is the full name or trading name of your company?";
  }
  if (h1 && !h1.textContent.trim()) {
    h1.textContent = "Type your company or brand name. Cradilot AI then works out which industry you are in, who you compete with, and where the digital gaps usually sit.";
  }
}

async function submitCompanyNameLive() {
  const nameInput = $("companyName");
  const name = (nameInput ? nameInput.value : "").trim();
  if (!name) {
    alert("Please type your company's full name or trading name so we can build your blueprint.");
    if (nameInput) nameInput.focus();
    return;
  }
  state.companyName = name;

  // Move to Substep 1.2 and show AI thinking state
  showStep1Sub(2);
  const thinkingBox = $("thinkingBox1_2");
  const contentBox  = $("contentBox1_2");
  if (thinkingBox) thinkingBox.classList.remove("hidden");
  if (contentBox)  contentBox.classList.add("hidden");

  try {
    const resp = await fetch("/api/live/analyze-company-name", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ company_name: name })
    });

    if (!resp.ok) throw new Error("Live analysis failed: " + resp.status);
    const data = await resp.json();

    const t1_2 = $("title1_2");
    const h1_2 = $("hint1_2");
    if (t1_2) t1_2.textContent = data.ai_prompt || `We took a look at the name "${name}". Which of these best describes what your business mainly does?`;
    if (h1_2) h1_2.textContent = data.sub_hint || "Once we know your industry, the cost estimates use figures from businesses like yours instead of a generic average.";

    renderIndustryOptions(data.industry_options);
  } catch (err) {
    console.warn("Live company analysis fallback:", err);
    const t1_2 = $("title1_2");
    const h1_2 = $("hint1_2");
    if (t1_2) t1_2.textContent = `We took a look at the name "${name}". Which of these Malaysian industries best describes what your business mainly does?`;
    if (h1_2) h1_2.textContent = "Once we know your industry, the cost estimates use figures from businesses like yours instead of a generic average.";
    await loadIndustryCatalog();
    renderIndustryOptions(null);
  } finally {
    if (thinkingBox) thinkingBox.classList.add("hidden");
    if (contentBox)  contentBox.classList.remove("hidden");
  }
}

// 行业选项的唯一来源是后端目录；前端不保留副本，避免两侧措辞漂移。
let INDUSTRY_CATALOG_CACHE = [];
let INDUSTRY_CATALOG_PROMISE = null;

function loadIndustryCatalog() {
  if (!INDUSTRY_CATALOG_PROMISE) {
    INDUSTRY_CATALOG_PROMISE = fetch("/api/catalog/industries")
      .then(resp => (resp.ok ? resp.json() : []))
      .then(list => {
        INDUSTRY_CATALOG_CACHE = Array.isArray(list) ? list : [];
        if ($("options1_2") && !document.querySelector("#options1_2 .option-card")) {
          renderIndustryOptions(null);
        }
        return INDUSTRY_CATALOG_CACHE;
      })
      .catch(err => {
        console.warn("Industry catalogue failed to load:", err);
        INDUSTRY_CATALOG_PROMISE = null;
        return [];
      });
  }
  return INDUSTRY_CATALOG_PROMISE;
}

function renderIndustryOptions(optionsList) {
  const container = $("options1_2");
  if (!container) return;
  container.innerHTML = "";

  const list = (optionsList && optionsList.length > 0) ? optionsList : (INDUSTRY_CATALOG_CACHE.length ? INDUSTRY_CATALOG_CACHE : [{
    val: "", label: "The industry list could not be loaded", sub: "Check that the backend /api/catalog/industries is reachable, then try again."
  }]);

  list.forEach(opt => {
    const isRec = Boolean(opt.is_recommended);
    const card = el("label", `option-card card-3d ${isRec ? "recommended-card" : ""}`);
    card.dataset.val = opt.val;

    const radio = el("input");
    radio.type = "radio";
    radio.name = "industryOpt";
    radio.value = opt.val;

    const lbl = el("div", "option-label");
    if (isRec) {
      const badge = el("span", "badge-matched", "Matched by AI");
      lbl.appendChild(badge);
    }
    const cleanLabelText = (opt.label || "").replace(/\s*\[AI recommended match\]\s*/g, "");
    lbl.appendChild(document.createTextNode(cleanLabelText));

    const sub = el("div", "option-sub", opt.sub);

    card.append(radio, lbl, sub);

    card.onclick = () => {
      document.querySelectorAll("#options1_2 .option-card").forEach(c => c.classList.remove("selected"));
      card.classList.add("selected");
      selectIndustryLive(opt.val, opt.label);
    };

    container.appendChild(card);
  });
}

function selectIndustryLive(ind, label) {
  state.industry = ind;
  showStep1Sub(3);

  const t1_3 = $("title1_3");
  const h1_3 = $("hint1_3");
  if (t1_3) {
    t1_3.textContent = `We have the ${ind} industry basis loaded. For this kind of business, the size of your team decides how much work is done by hand. How many full-time and day-to-day staff do you have now?`;
  }
  if (h1_3) {
    h1_3.textContent = "Handing information between roles and passing paper documents from one desk to another is what we use to work out the hours lost each month.";
  }

  renderTeamSizeOptions();
}

function renderTeamSizeOptions() {
  const container = $("options1_3");
  if (!container) return;
  container.innerHTML = "";

  const teamSizes = [
    { val: "1-5", label: "1 - 5 people (smallest team)", sub: "The owner wears several hats, and the work runs on personal judgement and chat messages." },
    { val: "6-20", label: "6 - 20 people (growing team)", sub: "Roles start to split up, and sales, delivery and finance each re-enter the same paperwork." },
    { val: "21-50", label: "21 - 50 people (expanding)", sub: "Approvals take longer to travel, and without one shared system the handovers between departments cost more time." },
    { val: "51", label: "51 or more people (larger operation)", sub: "Audit and process rules are stricter, and one damaged copy of the data can hold up the whole business." }
  ];

  teamSizes.forEach(opt => {
    const card = el("label", "option-card");
    card.dataset.val = opt.val;

    const radio = el("input");
    radio.type = "radio";
    radio.name = "teamSizeOpt";
    radio.value = opt.val;

    const lbl = el("div", "option-label", opt.label);
    const sub = el("div", "option-sub", opt.sub);

    card.append(radio, lbl, sub);

    card.onclick = () => {
      card.classList.add("selected");
      selectTeamSizeLive(opt.val, opt.label);
    };

    container.appendChild(card);
  });
}

function selectTeamSizeLive(sz, label) {
  state.teamSize = sz;
  showStep1Sub(4);

  const t1_4 = $("title1_4");
  const h1_4 = $("hint1_4");
  if (t1_4) {
    t1_4.textContent = `For ${state.companyName} (${state.industry}, ${sz}), one last basic figure: roughly what was your annual turnover in the last financial year?`;
  }
  if (h1_4) {
    h1_4.textContent = "Turnover is the base we use to turn problems into money. Without it we can only count items, not give you a ringgit figure.";
  }

  renderRevenueOptions();
}

function renderRevenueOptions() {
  const container = $("options1_4");
  if (!container) return;
  container.innerHTML = "";

  const revenues = [
    { val: "RM 500k or under", label: "Under RM 500,000 (building up)", sub: "Cash flow is thin, so the first job is to stop one lost computer from taking the business down. A low-cost cloud backup does that." },
    { val: "RM 500k - 2M", label: "RM 500,000 - 3,000,000 (growing fast)", sub: "Order volume is climbing, so enquiries need one proper route in and customer records need somewhere to collect." },
    { val: "RM 2M - 10M", label: "RM 3,000,000 - 10,000,000 (steady scale)", sub: "At this size, missed orders and repeated month-end checking usually cost more than the wages behind them, so we look there first." },
    { val: "RM 10M and above", label: "RM 10,000,000 and above (sector leader)", sub: "Your systems decide how well the business absorbs a shock, so the foundation has to carry that weight." }
  ];

  revenues.forEach(opt => {
    const card = el("label", "option-card");
    card.dataset.val = opt.val;

    const radio = el("input");
    radio.type = "radio";
    radio.name = "revenueOpt";
    radio.value = opt.val;

    const lbl = el("div", "option-label", opt.label);
    const sub = el("div", "option-sub", opt.sub);

    card.append(radio, lbl, sub);

    card.onclick = () => {
      card.classList.add("selected");
      selectRevenueLive(opt.val, opt.label);
    };

    container.appendChild(card);
  });
}

function selectRevenueLive(rev, label) {
  state.annualTurnover = rev;
  showStep1Sub(5);
  renderChallengeOptions();
}

function renderChallengeOptions() {
  const t = $("title1_5");
  const h = $("hint1_5");
  if (t) t.textContent = `For ${state.companyName} (${state.industry}), what is taking up most of your energy right now, or the problem you would fix first?`;
  if (h) h.textContent = "This decides what we look at first. We only put a money figure on something when you can tell us the volume.";

  const container = $("options1_5");
  if (!container) return;
  container.innerHTML = "";

  const challenges = [
    { val: "Paper delivery notes and month-end checking eat up time, and orders often go wrong or missing", label: "Paper documents and slow month-end checking", sub: "Delivery notes and invoices are worked out by hand. Month-end checking takes hours, and orders go missing or wrong." },
    { val: "No one answers enquiries after 18:00, so night and overseas business is lost", label: "Nobody answers enquiries after office hours", sub: "Customers write in the evening or after you close. By the time you reply the next morning they have gone to someone else." },
    { val: "Sales staff leave and take the customer chats with them, so the company holds no customer record", label: "Customers sit on staff members' own phones", sub: "When a salesperson leaves, the customer and the price quotes go with them. The company has no central record and no follow-up history." },
    { val: "The accounts book lives on one computer only, with real worry about ransomware or a hardware failure", label: "Financial data on one computer, with no safe copy", sub: "The accounts sit on one old office PC. A failed disk or a ransomware attack would stop the business outright." }
  ];

  challenges.forEach(opt => {
    const card = el("label", "option-card card-3d");
    card.dataset.val = opt.val;

    const radio = el("input");
    radio.type = "radio";
    radio.name = "challengeOpt";
    radio.value = opt.val;

    const lbl = el("div", "option-label", opt.label);
    const sub = el("div", "option-sub", opt.sub);

    card.append(radio, lbl, sub);

    card.onclick = () => {
      card.classList.add("selected");
      selectChallengeLive(opt.val);
    };

    container.appendChild(card);
  });
}

function selectChallengeLive(ch) {
  state.biggestChallenge = ch;
  showStep1Sub(6);
  renderToolsOptions();
}

// 简报 Step 1 点名的 "Current digital tools"。答案按客户原话存：它既是数据可用性档位的
// 兜底输入，也是推荐时"已经在用什么就顺着接"的根据；没提到的工具按未采集处理，不算缺失。
function renderToolsOptions() {
  const t = $("title1_6");
  const h = $("hint1_6");
  if (t) t.textContent = `What digital tools does ${state.companyName || "your business"} actually run on today?`;
  if (h) h.textContent = "Pick the line closest to how you work now, or list the tools below. A tool we did not hear about is scored as not collected, not as missing.";

  const container = $("options1_6");
  if (!container) return;
  container.innerHTML = "";

  const toolsets = [
    { label: "Paper documents, phone calls and WhatsApp only", sub: "Quotes, orders and follow-ups are typed out by hand each time; nothing is kept in a system." },
    { label: "Accounting software only (SQL, AutoCount, an Excel ledger)", sub: "The accounts are in a system, but customers, orders and stock are still kept somewhere else." },
    { label: "An ERP, POS or inventory system for stock and orders", sub: "Stock and orders are recorded in one system, though other departments still copy from it by hand." },
    { label: "A CRM or marketing tool already in use", sub: "Customer records and campaigns already live in one place, so the gap is connection and measurement, not collection." },
    { label: "Several tools, but they do not talk to each other", sub: "Someone re-keys the same figures from one system into another, so the numbers never agree at month end." }
  ];

  toolsets.forEach(opt => {
    const card = el("label", "option-card card-3d");
    card.dataset.val = opt.label;

    const radio = el("input");
    radio.type = "radio";
    radio.name = "toolsOpt";
    radio.value = opt.label;

    const lbl = el("div", "option-label", opt.label);
    const sub = el("div", "option-sub", opt.sub);

    card.append(radio, lbl, sub);

    card.onclick = () => {
      card.classList.add("selected");
      selectToolsLive(opt.label);
    };

    container.appendChild(card);
  });
}

function selectToolsLive(tools) {
  state.currentTools = (tools || "").trim();
  showStep1Sub(7);
  renderObjectiveOptions();
}

function submitCustomTools() {
  const val = ($("customToolsInput").value || "").trim();
  if (!val) {
    alert("Pick one of these, or list the tools you actually use.");
    return;
  }
  selectToolsLive(val);
}

function submitCustomChallenge() {
  const val = ($("customChallengeInput").value || "").trim();
  if (!val) {
    alert("Pick one of these problems, or type the one your business actually has.");
    return;
  }
  selectChallengeLive(val);
}

function renderObjectiveOptions() {
  const t = $("title1_7");
  const h = $("hint1_7");
  if (t) t.textContent = `One last thing for the file: over the next 12 months, what is the single thing you most want digital tools or AI to do for you?`;
  if (h) h.textContent = "This goal carries all the way to the final blueprint: what to do, which step comes first, and how much it could save. All of it is worked out from what we measured this time and the numbers you gave us.";

  const container = $("options1_7");
  if (!container) return;
  container.innerHTML = "";

  const objectives = [
    { val: "Move the paperwork and month-end checking online, and give the finance computer an off-site backup that can genuinely be restored", label: "Less checking by hand, and data not kept on one computer only", sub: "Documents move online, and the key computer gets an off-site backup. When it is done, we measure how long month-end checking takes before and after." },
    { val: "Make sure enquiries at night and on public holidays get answered, instead of the next morning", label: "No more missed enquiries at night and on holidays", sub: "An enquiry that arrives after 18:00 gets a first reply automatically, and the serious ones reach the right person." },
    { val: "Bring the customers and deals scattered across staff members' own phones back under company management", label: "Customer records belong to the company, and a handover is possible", sub: "Deals sit on one board, so when someone moves on, the person taking over can see how far each customer got." },
    { val: "Put the outward-facing email and domain in the company's own name, so quotes and invoices can be verified", label: "Company-domain email for outside contact, assets in your own name", sub: "The domain, email, website and data are registered under your company, so a fake sender can be blocked by the person receiving it." }
  ];

  objectives.forEach(opt => {
    const card = el("label", "option-card card-3d");
    card.dataset.val = opt.val;

    const radio = el("input");
    radio.type = "radio";
    radio.name = "objectiveOpt";
    radio.value = opt.val;

    const lbl = el("div", "option-label", opt.label);
    const sub = el("div", "option-sub", opt.sub);

    card.append(radio, lbl, sub);

    card.onclick = () => {
      card.classList.add("selected");
      selectObjectiveLive(opt.val);
    };

    container.appendChild(card);
  });
}

function selectObjectiveLive(obj) {
  state.growthObjective = obj;
  setTimeout(finishStep1, 200);
}

function submitCustomObjective() {
  const val = ($("customObjectiveInput").value || "").trim();
  if (!val) {
    alert("Pick one of these, or type what you want digital tools to do for your business.");
    return;
  }
  selectObjectiveLive(val);
}

function prevStep1Sub(targetSub) {
  showStep1Sub(targetSub);
}

function showStep1Sub(subIdx) {
  state.step1Sub = subIdx;

  if ($("step1BannerTag")) {
    $("step1BannerTag").textContent = step1Labels[subIdx] || ("Step 1." + subIdx + " of 7");
  }

  for (let i = 1; i <= 7; i++) {
    const pane = $("substep1_" + i);
    if (pane) {
      if (i === subIdx) pane.classList.add("active");
      else pane.classList.remove("active");
    }
  }

  if (subIdx === 1 && $("companyName")) {
    $("companyName").focus();
  }
}

async function finishStep1() {
  try {
    const resp = await fetch("/api/diag/start", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        company_name: state.companyName,
        industry: state.industry,
        team_size: state.teamSize,
        annual_turnover: state.annualTurnover,
        biggest_challenge: state.biggestChallenge || "",
        current_tools: state.currentTools || "",
        growth_objective: state.growthObjective || ""
      })
    });

    if (resp.ok) {
      const data = await resp.json();
      state.sessionId = data.session_id;
    } else {
      state.sessionId = "sess_" + Date.now();
    }
  } catch (err) {
    console.warn("Diag start warning (using fallback session):", err);
    state.sessionId = "sess_" + Date.now();
  }

  goTo(2);
}

function initStep2Live() {
  const t2 = $("title-2");
  const h2 = $("hint-2");
  if (t2) {
    t2.textContent = "Enter your company's official website URL";
  }
  if (h2) {
    h2.textContent = "We open that one address from the public internet and read what a customer, "
      + "a search engine or an attacker can see. Nothing is guessed: every line below is either "
      + "measured on this run, or marked as not measured.";
  }
}

// ─── Step 2: 公网机检（210 项主清单，按站型开闸） ─────────────────────────────

const AUDIT_PROGRESS = [
  "Resolving the domain and checking reachability...",
  "Checking the TLS certificate, response headers and mobile rendering...",
  "Fingerprinting the stack and matching published advisories (OSV)...",
  "Matching CISA's actively-exploited list and end-of-support dates...",
  "Reading what the public internet can already reach or download...",
  "Scoring the four conclusions and archiving the evidence..."
];

let auditProgressTimer = null;

function startAuditProgress() {
  const label = $("scrapeLoadingStatus");
  if (!label) return;
  let i = 0;
  label.textContent = AUDIT_PROGRESS[0];
  stopAuditProgress();
  auditProgressTimer = setInterval(() => {
    i = (i + 1) % AUDIT_PROGRESS.length;
    label.textContent = AUDIT_PROGRESS[i];
  }, 2600);
}

function stopAuditProgress() {
  if (auditProgressTimer) {
    clearInterval(auditProgressTimer);
    auditProgressTimer = null;
  }
}

async function runWebsiteScraper() {
  const urlInput = ($("websiteUrlInput").value || "").trim();
  if (!urlInput) {
    alert("Type your website address, or choose “We have no website yet”.");
    $("websiteUrlInput").focus();
    return;
  }

  const btn = $("btnRunScraper");
  state.websiteUrl = urlInput;
  $("scrapeInputContainer").classList.add("hidden");
  $("scrapeResultBox").classList.add("hidden");
  $("scrapeLoadingBox").classList.remove("hidden");
  startAuditProgress();
  if (btn) btn.disabled = true;

  try {
    const resp = await fetch("/api/audit/site", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url: urlInput, session_id: state.sessionId })
    });
    if (!resp.ok) throw new Error("audit/site returned " + resp.status);
    const data = await resp.json();
    if (!data || data.success !== true) throw new Error((data && data.detail) || "The inspection returned no result.");

    state.webAuditResult = data;
    state.websiteStatus = websiteStatusFromAudit(data);

    renderAuditLevel(data);
    renderAuditConclusions(data);
    renderMachineAuditStats(data);
    renderMachineAuditVulns(data);
    renderMachineAuditFindings(data);

    stopAuditProgress();
    $("scrapeLoadingBox").classList.add("hidden");
    $("scrapeResultBox").classList.remove("hidden");

  } catch (err) {
    console.error("Machine audit error:", err);
    stopAuditProgress();
    state.webAuditResult = null;
    state.websiteStatus = "unverified";
    $("scrapeLoadingBox").classList.add("hidden");
    $("scrapeInputContainer").classList.remove("hidden");
    alert("This run could not reach your site. That is not a fault in your website — it means "
      + "we did not measure it. Try again, or continue: anything unmeasured is never scored "
      + "against you.");
  } finally {
    if (btn) btn.disabled = false;
  }
}

function websiteStatusFromAudit(data) {
  const summary = data.summary || {};
  if (data.has_website === false) return "none";
  if (!summary.graded_checks) return "unverified";
  const score = summary.score;
  if (score === null || score === undefined) return "unverified";
  return score >= 70 ? "modern" : "outdated";
}

const RATE_CLASS = {
  CRITICAL: "danger", HIGH: "danger", MEDIUM: "warn", LOW: "warn",
  INFO: "secure", OK: "secure", "N/A": "na", UNKNOWN: "na"
};

function renderAuditLevel(data) {
  const box = $("machineAuditLevel");
  if (!box) return;
  box.innerHTML = "";
  const s = data.checklist_summary || {};
  if (!s.items_total) {
    box.classList.add("hidden");
    return;
  }
  box.classList.remove("hidden");

  const head = el("div", "audit-level-head");
  head.appendChild(el("span", "audit-level-badge", data.site_level || "L1"));
  head.appendChild(el("span", "audit-level-label", data.site_level_label || ""));
  box.appendChild(head);

  const line = el("div", "audit-level-line");
  line.textContent = `${s.items_measured} of ${s.items_total} checks applied to this site. `
    + `${s.not_applicable} were switched off because we saw no matching feature, and `
    + `${s.not_tested} can only be confirmed from inside your own account.`;
  box.appendChild(line);

  const seen = (data.signals_present || []).slice(0, 10);
  if (seen.length) {
    const chips = el("div", "audit-signal-chips");
    chips.appendChild(el("span", "audit-signal-lead", "Found on your site:"));
    seen.forEach(name => chips.appendChild(el("span", "audit-signal-chip", name)));
    box.appendChild(chips);
  }
}

function renderAuditConclusions(data) {
  const box = $("machineAuditConclusions");
  if (!box) return;
  box.innerHTML = "";
  const conclusions = data.conclusions || [];
  if (!conclusions.length) {
    box.appendChild(el("div", "conclusion-empty",
      "No conclusion could be drawn: this run measured too little of the site."));
    return;
  }

  conclusions.forEach(c => {
    const rate = String(c.rate || "N/A");
    const card = el("div", "conclusion-card rate-" + rate.toLowerCase());
    const head = el("div", "cc-head");
    head.appendChild(el("span", "cc-title", c.title));
    head.appendChild(el("span", "cc-rate " + (RATE_CLASS[rate] || "na"), rate));
    card.appendChild(head);

    card.appendChild(el("p", "cc-result", c.result || ""));

    const n = c.counts || {};
    card.appendChild(el("div", "cc-counts",
      `${n.measured || 0} measured · ${n.pass || 0} clear · ${n.fail || 0} gap${n.fail === 1 ? "" : "s"} · `
      + `${n.unverified || 0} not measured · ${n.not_applicable || 0} not applicable`));

    const remedy = el("div", "cc-remedy");
    const names = (c.remedy_products || []).slice(0, 3).map(p => `${p.name} — ${p.price_label}`);
    remedy.appendChild(el("span", "cc-remedy-lead",
      names.length ? "What closes it: " : "Nothing to buy for this one."));
    if (names.length) remedy.appendChild(el("span", "cc-remedy-text", names.join(" · ")));
    card.appendChild(remedy);

    box.appendChild(card);
  });
}

function renderMachineAuditStats(data) {
  const box = $("machineAuditStats");
  if (!box) return;
  const legacy = data.summary || {};
  const cs = data.checklist_summary || {};
  const s = cs.items_total ? {
    graded_checks: cs.items_graded, pass: cs.pass, fail: cs.fail,
    unverified: cs.unverified, not_applicable: cs.not_applicable,
    score_note: cs.score_note || legacy.score_note,
    audit_seconds: legacy.audit_seconds
  } : legacy;

  const tiles = [
    { label: "Checks with a definite result", val: (s.graded_checks || 0) + "", cls: "" },
    { label: "Clear", val: (s.pass || 0) + "", cls: "secure" },
    { label: "Confirmed gaps", val: (s.fail || 0) + "", cls: (s.fail || 0) > 0 ? "danger" : "secure" },
    { label: "Not measured this run", val: (s.unverified || 0) + "", cls: "" },
    { label: "Not applicable to this site", val: (s.not_applicable || 0) + "", cls: "" },
    { label: "Inspection time", val: (s.audit_seconds || 0) + "s", cls: "" }
  ];

  box.innerHTML = "";
  tiles.forEach(t => {
    const item = el("div", "scrape-stat-item");
    item.appendChild(el("div", "scrape-stat-label", t.label));
    item.appendChild(el("div", "scrape-stat-val" + (t.cls ? " " + t.cls : ""), t.val));
    box.appendChild(item);
  });

  const note = $("machineAuditNote");
  if (note) note.textContent = s.score_note || "";

  const badge = $("statBadge");
  if (badge) {
    const n = (data.recorded_facts && data.recorded_facts.length) || 0;
    badge.textContent = n ? (n + " measured facts archived") : "Measured";
    badge.className = "dim-badge verified";
  }
  const toggle = $("machineAuditDetailToggle");
  const total = ((data.checklist || []).length) || (data.findings || []).length;
  if (toggle) toggle.textContent = `Show every check (${total} items on the master list)`;
}

function renderMachineAuditVulns(data) {
  const box = $("machineAuditVuln");
  if (!box) return;
  const rep = data.vulnerability_report || null;
  const hits = (rep && rep.hits) || [];
  const dead = (rep && rep.eol_lines_dead) || [];
  if (!rep || (hits.length === 0 && dead.length === 0)) {
    box.classList.add("hidden");
    box.innerHTML = "";
    return;
  }

  box.classList.remove("hidden");
  box.innerHTML = "";
  box.appendChild(el("div", "vuln-title", "Known advisories and end-of-support versions matched to what we identified"));

  const table = el("table", "vuln-table");
  const head = el("thead");
  const headRow = el("tr");
  ["Component and version", "Advisory", "Level", "Officially fixed in", "Exploited in the wild"].forEach(h => {
    headRow.appendChild(el("th", "", h));
  });
  head.appendChild(headRow);
  table.appendChild(head);

  const body = el("tbody");
  hits.forEach(h => {
    const row = el("tr");
    row.appendChild(el("td", "", (h.component_label || "") + " " + (h.installed_version || "")));
    row.appendChild(el("td", "", h.cve || h.id || ""));
    row.appendChild(el("td", "vuln-sev-" + String(h.severity || "unknown").toLowerCase(), h.severity || "Unrated"));
    row.appendChild(el("td", "", h.fixed_in || "See advisory"));
    row.appendChild(el("td", h.known_exploited ? "vuln-kev" : "",
      h.known_exploited ? ("Yes · " + (h.kev_action_due || "patch by deadline")) : "No"));
    body.appendChild(row);
  });
  dead.forEach(d => {
    const row = el("tr");
    row.appendChild(el("td", "", (d.label || "") + " " + (d.installed || "")));
    row.appendChild(el("td", "", "Version line " + (d.cycle || "") + " is out of support"));
    row.appendChild(el("td", "vuln-sev-eol", "End of life"));
    row.appendChild(el("td", "", "Move to a supported version"));
    row.appendChild(el("td", "", "Support ended " + (d.eol_date || "already passed")));
    body.appendChild(row);
  });
  table.appendChild(body);
  box.appendChild(table);

  if (rep.coverage_note) {
    box.appendChild(el("div", "vuln-coverage", rep.coverage_note));
  }
}

const STATE_LABEL = {
  fail: "Gap", unverified: "Not measured", not_tested: "Needs inside access",
  pass: "Clear", not_applicable: "Not applicable"
};
const STATE_RANK = { fail: 0, unverified: 1, not_tested: 2, pass: 3, not_applicable: 4 };
const SEVERITY_RANK = { CRITICAL: 5, HIGH: 4, MEDIUM: 3, LOW: 2, INFO: 1, UNKNOWN: 0 };

function renderMachineAuditFindings(data) {
  const box = $("machineAuditFindings");
  if (!box) return;
  box.innerHTML = "";
  const rows = data.checklist || [];
  if (!rows.length) {
    renderLegacyFindings(box, data.findings || []);
    return;
  }

  const byModule = new Map();
  rows.forEach(r => {
    if (!byModule.has(r.module_title)) byModule.set(r.module_title, []);
    byModule.get(r.module_title).push(r);
  });

  byModule.forEach((items, title) => {
    const gaps = items.filter(r => r.state === "fail").length;
    const section = el("div", "ck-module");
    section.appendChild(el("div", "ck-module-head",
      `${title} — ${items.length} checks`
      + (gaps ? ` · ${gaps} gap${gaps === 1 ? "" : "s"}` : " · no gap measured")));
    items.slice().sort((a, b) =>
      (STATE_RANK[a.state] - STATE_RANK[b.state])
      || ((SEVERITY_RANK[b.severity] || 0) - (SEVERITY_RANK[a.severity] || 0)))
      .forEach(r => {
        const row = el("div", "ck-row st-" + r.state);
        row.appendChild(el("span", "ck-state", STATE_LABEL[r.state] || r.state));
        const body = el("div", "ck-body");
        body.appendChild(el("span", "ck-label", r.label));
        const detail = r.observed || r.detail || r.skipped_reason || "";
        if (detail) body.appendChild(el("span", "ck-detail", detail));
        row.appendChild(body);
        if (r.state === "fail" || r.state === "unverified") {
          row.appendChild(el("span", "ck-sev", r.severity || ""));
        }
        section.appendChild(row);
      });
    box.appendChild(section);
  });
}

function renderLegacyFindings(box, findings) {
  const groups = [
    ["fail", "Confirmed gaps"], ["pass", "Measured clear"],
    ["unverified", "Not measured this run"]
  ];
  groups.forEach(([key, heading]) => {
    const items = findings.filter(f => f.status === key);
    if (!items.length) return;
    const section = el("div", "finding-group finding-group-" + key);
    section.appendChild(el("div", "finding-group-head", `${heading} (${items.length})`));
    items.forEach(f => {
      const card = el("div", "finding-card severity-" + String(f.severity || "INFO").toLowerCase());
      card.appendChild(el("div", "finding-title", f.title || f.check));
      card.appendChild(el("div", "finding-observed", f.observed || ""));
      if (f.plain) card.appendChild(el("div", "finding-plain", f.plain));
      const meta = el("div", "finding-meta");
      meta.appendChild(el("span", "finding-severity", f.severity || "INFO"));
      if ((f.vendor_skus || []).length) {
        meta.appendChild(el("span", "finding-sku", f.vendor_skus.join(" · ")));
      }
      card.appendChild(meta);
      section.appendChild(card);
    });
    box.appendChild(section);
  });
}

function sourceClass(label) {
  const text = String(label || "");
  if (text.indexOf("Measured") >= 0) return "machine";
  if (text.indexOf("Inferred") >= 0) return "inferred";
  return "stated";
}

async function skipWebsiteScraper() {
  state.websiteUrl = "none";
  state.websiteStatus = "none";

  try {
    const resp = await fetch("/api/audit/site", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url: "none", session_id: state.sessionId })
    });
    if (resp.ok) {
      const data = await resp.json();
      state.webAuditResult = data;
      state.websiteStatus = websiteStatusFromAudit(data);
      renderAuditLevel(data);
      renderAuditConclusions(data);
      renderMachineAuditStats(data);
      renderMachineAuditVulns(data);
      renderMachineAuditFindings(data);
      if (data.has_website === false) {
        const box = $("machineAuditConclusions");
        if (box) {
          box.innerHTML = "";
          box.appendChild(el("div", "conclusion-empty",
            "You told us there is no website yet, so there was nothing to measure. "
            + "That is a starting point, not a failure — the blueprint begins here."));
        }
      }
      $("scrapeInputContainer").classList.add("hidden");
      $("scrapeResultBox").classList.remove("hidden");
    }
  } catch (err) {
    console.warn("Skip website sync note:", err);
  }

  confirmWebScraperAndProceed();
}

async function confirmWebScraperAndProceed() {
  goTo(3);
}

// ─── Stage 3: True Dynamic Agentic Probe Loop & Cradilot Brain Workbench ──────

// Stage 3 is one column with two phases: answer the questions, then read the ledger back.
function showDiagPhase(phase) {
  state.diagPhase = phase === "review" ? "review" : "ask";
  const review = state.diagPhase === "review";

  if ($("diagAskPanel")) $("diagAskPanel").classList.toggle("hidden", review);
  if ($("diagReviewPanel")) $("diagReviewPanel").classList.toggle("hidden", !review);
  if ($("diagFlowPhaseAsk")) {
    $("diagFlowPhaseAsk").className = "diag-flow-step" + (review ? " done" : " active");
  }
  if ($("diagFlowPhaseReview")) {
    $("diagFlowPhaseReview").className = "diag-flow-step" + (review ? " active" : "");
  }

  // The map canvas is sized from its container, so it is measured once the ledger is on screen.
  if (review) initKnowledgeGraph();
  updateTopHud();
  window.scrollTo({ top: 0, behavior: "smooth" });
}

async function initStep3DynamicLoop() {
  const optionsBox = $("diagOptions");
  if (optionsBox) optionsBox.innerHTML = "";
  showDiagPhase("ask");

  setOrbState("analyzing");
  showDiagThinking(true, "Cradilot Brain is working through the facts and pulling up what we know about your industry...", "Checking the confirmed facts against businesses like yours · building the evidence list for this run");
  updateTopHud();

  try {
    // 1. Fetch initial live wiki tree
    const wikiResp = await fetch(`/api/diag/wiki/${state.sessionId}`);
    if (wikiResp.ok) {
      const wikiData = await wikiResp.json();
      updateWorkbenchUI(wikiData, null);
    }

    // 2. Fetch first probe
    const probeResp = await fetch(`/api/diag/first-probe/${state.sessionId}`);
    if (!probeResp.ok) throw new Error("First probe error: " + probeResp.status);
    const probe = await probeResp.json();

    renderDiagProbe(probe, 1);
  } catch (err) {
    console.warn("Init probe loop fallback:", err);
    renderDiagProbe({
      step_title: "Safe copies of your key data",
      question: `For ${state.industry || 'a business like yours'}, the accounts are the lifeline. How are ${state.companyName || 'your'} core accounts backed up today?`,
      sub_hint: "If the accounts live on one machine, ransomware or a failed disk can stop the business for days and lose the records you check yourself against.",
      options: [
        { label: "On one computer, with no backup", sub: "The accounts exist only on one office PC, with no copy held elsewhere. If that machine fails, everything goes with it.", val: "single_pc" },
        { label: "Copied by hand to an external drive", sub: "Someone plugs in a drive now and then. It costs time, and it does not survive fire or theft.", val: "manual_usb" },
        { label: "Automatic encrypted cloud backup", sub: "An encrypted copy goes off-site on a schedule without anyone having to remember it, and you can be running again quickly.", val: "cloud_auto" },
        { label: "Not sure", sub: "It stays an open question, not a bad mark", val: "__unsure" },
        { label: "Other — I'll describe it", sub: "Type or dictate the way it actually works", val: "__describe" }
      ]
    }, 1);
  } finally {
    showDiagThinking(false);
  }
}

function showDiagThinking(show, title, subtitle) {
  const box = $("diagThinkingBox");
  const content = $("diagContentBox");
  if (show) {
    if (box) {
      box.classList.remove("hidden");
      if (title && $("diagThinkingTitle")) $("diagThinkingTitle").textContent = title;
      if (subtitle && $("diagThinkingSubtitle")) $("diagThinkingSubtitle").textContent = subtitle;
    }
    if (content) content.classList.add("hidden");
  } else {
    if (box) box.classList.add("hidden");
    if (content) content.classList.remove("hidden");
  }
}

function renderDynamicContainer(containerData, probe) {
  if (!containerData && probe) {
    containerData = probe.dynamic_container;
  }
  const question = (containerData && containerData.dynamic_question) || {};

  const stageBadge = $("containerStageBadge");
  if (stageBadge) {
    stageBadge.textContent = (containerData && containerData.sop_stage)
      ? containerData.sop_stage
      : `Turn ${state.currentTurn} · ${probe && probe.step_title ? probe.step_title : "Checking the facts"}`;
  }

  // 依据框只说本次真的知道的事：已锁证比例 + 仍缺的维度。没有内容就整块隐藏。
  const rationaleBox = $("containerRationaleBox");
  if (rationaleBox) {
    const bits = [];
    if (question.rationale) bits.push(question.rationale);
    if (containerData && typeof containerData.confidence_score === "number") {
      bits.push(`Evidence held so far: ${Math.round(containerData.confidence_score * 100)}%`);
    }
    const missing = (containerData && containerData.missing_blindspots) || [];
    if (missing.length) bits.push("Not asked yet: " + missing.join(", "));
    rationaleBox.textContent = bits.join(" · ");
    rationaleBox.classList.toggle("hidden", bits.length === 0);
  }
}

function renderDiagProbe(probe, turnNum) {
  // 记录本轮探针归属维度，提交回答时回传给后端，避免槽位被记到错误维度
  state.currentProbe = probe || null;
  state.currentTurn = turnNum || state.currentTurn || 1;
  updateTopHud();

  renderDynamicContainer(probe ? probe.dynamic_container : null, probe);

  const banner = $("diagBannerTag");
  const title = $("diagTitle");
  const hint = $("diagHint");
  const container = $("diagOptions");

  if (banner) banner.textContent = `Cradilot live check · Turn ${state.currentTurn} · ${probe.step_title || "Checking the facts"}`;
  if (title) title.textContent = probe.question || "";
  if (hint) hint.textContent = probe.sub_hint || "";

  if (container && probe.options) {
    container.innerHTML = "";
    probe.options.forEach(opt => {
      // 逃生口不是又一个档位：样式要分开，老板才看得出那是出路而不是选项之一
      const isEscape = opt.val === "__unsure" || opt.val === "__describe";
      const card = el("label", "option-card card-3d" + (isEscape ? " option-escape" : ""));
      card.dataset.val = opt.val || "";

      const radio = el("input");
      radio.type = "radio";
      radio.name = "diagOpt";
      radio.value = opt.val || "";

      const lbl = el("div", "option-label", opt.label || "");
      const sub = el("div", "option-sub", opt.sub || "");

      card.append(radio, lbl, sub);

      card.onclick = () => {
        card.classList.add("selected");
        submitDiagTurn(opt);
      };

      container.appendChild(card);
    });
  }

  if ($("customAnswerInput")) $("customAnswerInput").value = "";
  showInterviewReadBack("");
}

// 后端把这一轮记下了什么（或没记下什么）用一行白话回读给客户
function showInterviewReadBack(text) {
  const box = $("diagReadBack");
  if (!box) return;
  box.textContent = text || "";
  box.classList.toggle("hidden", !text);
}

async function submitDiagTurn(opt) {
  const label = (opt && opt.label) || "";
  const sub = (opt && opt.sub) || "";
  const fullAnswer = sub ? `${label}: ${sub}` : label;
  await processTurnAnswer(fullAnswer, opt || null);
}

async function submitCustomDiagAnswer() {
  const inp = $("customAnswerInput");
  const text = (inp ? inp.value : "").trim();
  if (!text) {
    alert("Type how it works in your business, or pick one of the choices above.");
    return;
  }
  const btn = $("btnSubmitCustom");
  if (btn) {
    btn.disabled = true;
    btn.textContent = "Checking...";
  }
  try {
    await processTurnAnswer(text);
    if (inp) inp.value = "";
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.textContent = "Check this answer";
    }
  }
}

async function processTurnAnswer(userAnswer, selectedOption) {
  setOrbState("analyzing");
  showDiagThinking(true, "Cradilot Brain is turning your answer into facts we can check...", "Pulling out the details · saving them in the evidence record on this machine · judging whether the basics are ready for AI");

  try {
    const resp = await fetch("/api/diag/step", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: state.sessionId,
        user_answer: userAnswer,
        target_dim: (state.currentProbe && state.currentProbe.dimension) || "",
        selected_option: selectedOption || null
      })
    });

    if (!resp.ok) throw new Error("Diag step failed: " + resp.status);
    const data = await resp.json();

    // 逃生口"我自己说"：后端这一轮什么都没记、轮次也没推进，
    // 题目保持原样，只把光标交给下面那个自由文本框。
    if (data.await_free_text) {
      setOrbState("idle");
      showInterviewReadBack(data.read_back || "");
      // 一条档位都没选中：卡片不该继续亮着，等的是下面那段客户自己的话
      document.querySelectorAll("#diagOptions .option-card.selected")
        .forEach(c => c.classList.remove("selected"));
      const inp = $("customAnswerInput");
      if (inp) {
        inp.focus();
        if (inp.scrollIntoView) inp.scrollIntoView({ block: "nearest", behavior: "smooth" });
      }
      return;
    }

    // Update Live Workbench
    updateWorkbenchUI(data.tree, data.cot);

    if (data.status === "DIAGNOSIS_COMPLETE") {
      // 收尾文案只说这一轮真的发生了的事：问到 ≠ 每项都答出来了；问完就翻到台账。
      // 后端的 message 会把维度计数写进去（"n / 11 areas"），那是 PDF 的口径，界面不用。
      const closedAll = data.all_completed === true;
      if ($("diagReviewBanner")) {
        $("diagReviewBanner").textContent = closedAll
          ? "The questions are all asked"
          : "The interview time is used up — the report works on the confirmed evidence";
      }
      if ($("diagReviewNote")) {
        $("diagReviewNote").textContent = closedAll
          ? "Everything listed below is a fact you confirmed in this session. Anything you were not sure about stays an open item: counted neutrally, not deducted."
          : "Whatever has no confirmed answer is counted neutrally and is not deducted. The report is built only on the facts above.";
      }
      if ($("diagOptions")) $("diagOptions").innerHTML = "";
      setOrbState("idle");
      showInterviewReadBack(data.read_back || "");
      showDiagPhase("review");
      return;
    }

    // Render next probe
    if (data.next_probe) {
      renderDiagProbe(data.next_probe, data.current_turn || (state.currentTurn + 1));
    }

    // 回读排在渲染之后：渲染新问题时会清掉上一轮回读的那一行
    showInterviewReadBack(data.read_back || "");

  } catch (err) {
    console.error("Turn processing error:", err);
    alert("The reasoning step did not complete this time. We are falling back and trying again.");
  } finally {
    showDiagThinking(false);
  }
}

function updateWorkbenchUI(tree, cot) {
  if (!tree) return;
  state.wikiTree = tree;

  // 0. Update Live Enterprise Dossier Snapshot & Top Spatial HUD
  const dossier = (tree && tree.dossier) || {};
  const cName = dossier.company_name || state.companyName || "Not recorded";
  const cInd = dossier.industry || state.industry || "Not recorded";
  const cTeam = dossier.team_size || state.teamSize || "Not recorded";
  const cTurn = dossier.annual_turnover || state.annualTurnover || "Not recorded";
  const cChall = dossier.biggest_challenge || state.biggestChallenge || "Not recorded";
  const cObj = dossier.growth_objective || state.growthObjective || "Not recorded";

  if ($("snapCompany")) $("snapCompany").textContent = "Company: " + cName;
  if ($("snapIndustry")) $("snapIndustry").textContent = "Industry: " + cInd;
  if ($("snapTeam")) $("snapTeam").textContent = "Size: " + cTeam;
  if ($("snapTurnover")) $("snapTurnover").textContent = "Turnover: " + cTurn;
  if ($("snapChallenge")) $("snapChallenge").textContent = "Main problem: " + (cChall.length > 18 ? cChall.slice(0, 18) + "..." : cChall);
  if ($("snapObjective")) $("snapObjective").textContent = "Year goal: " + (cObj.length > 18 ? cObj.slice(0, 18) + "..." : cObj);

  updateTopHud();

  // 1. 这一轮确认了几条事实。
  // 取证状态只认后端树的 is_verified 标记，界面不自己判断"问过"算不算"已确认"
  // ——问到但答不出的既不算确认，也不算缺失。客户界面只报数，不搬"11 个维度"这套框架。
  let confirmedCount = 0;
  (tree.dimensions || []).forEach(d => { if (d.is_verified === true) confirmedCount++; });
  (tree.ars_factors || []).forEach(f => { if (f.is_verified === true) confirmedCount++; });

  state.exploredCount = confirmedCount;
  if ($("diagExploreCount")) {
    $("diagExploreCount").textContent = confirmedCount
      ? `Confirmed facts: ${confirmedCount}`
      : "Nothing confirmed yet";
  }

  // 就绪度门禁：分数要到定稿才算，只有真算出来且低于基线才切光球状态
  const currentDmsScore = (tree.dms_score === undefined || tree.dms_score === null)
    ? null : tree.dms_score;
  if (currentDmsScore !== null && currentDmsScore < 40) setOrbState("hardlock");

  // Live Knowledge Topology Network update
  renderKnowledgeGraph(tree);

  // 4. 4-step CoT display
  if (cot) {
    renderCotSteps(cot);
  }
}

let cotSequence = 0;
const COT_STEP_DELAY_MS = 240;

function renderCotSteps(cot) {
  let steps = [];
  if (Array.isArray(cot)) {
    steps = [
      { id: 1, text: cot[0] ? (cot[0].thought || cot[0].summary) : "", confirmed: Boolean(cot[0] && cot[0].confirmed) },
      { id: 2, text: cot[1] ? (cot[1].thought || cot[1].summary) : "", confirmed: Boolean(cot[1] && cot[1].confirmed) },
      { id: 3, text: cot[2] ? (cot[2].thought || cot[2].summary) : "", confirmed: Boolean(cot[2] && cot[2].confirmed) },
      { id: 4, text: cot[3] ? (cot[3].thought || cot[3].summary) : "", confirmed: Boolean(cot[3] && cot[3].confirmed) }
    ];
  } else if (cot && typeof cot === "object") {
    steps = [
      { id: 1, text: cot.mode_fact || (cot.step1_deconstruction && cot.step1_deconstruction.summary) || "", confirmed: false },
      { id: 2, text: cot.bleeding_inference || (cot.step2_bleeding && cot.step2_bleeding.summary) || "", confirmed: false },
      { id: 3, text: cot.guardrail_reflection || (cot.step3_critique && cot.step3_critique.summary) || "", confirmed: false },
      { id: 4, text: cot.action_decision || (cot.step4_decision && cot.step4_decision.summary) || "", confirmed: false }
    ];
  }
  if (!steps.length) return;

  // 每次回答都重新流一遍；seq 保证后一次的渲染不会被上一次的延时回调覆写
  const seq = ++cotSequence;
  steps.forEach(s => {
    const txtEl = $("cotText" + s.id);
    const itemEl = $("cotStep" + s.id);
    if (txtEl) txtEl.textContent = "";
    if (itemEl) itemEl.classList.remove("active", "cot-shown", "cot-confirmed");
  });

  steps.forEach((s, idx) => {
    setTimeout(() => {
      if (seq !== cotSequence) return;
      const txtEl = $("cotText" + s.id);
      const itemEl = $("cotStep" + s.id);
      if (txtEl && s.text) txtEl.textContent = s.text;
      if (!itemEl) return;
      steps.forEach(prev => {
        const prevEl = $("cotStep" + prev.id);
        if (prevEl) prevEl.classList.remove("active");
      });
      itemEl.classList.add("cot-shown", "active");
      // 对勾只给"这一步的话确实有在场的证据撑着"的那些；没确认的留着序号读作未完成
      if (s.confirmed) itemEl.classList.add("cot-confirmed");
    }, COT_STEP_DELAY_MS * idx);
  });
}

async function finalizeAssessmentSession(assumptionOverrides) {
  try {
    const finalResp = await fetch("/api/diag/finalize", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: state.sessionId,
        assumptions: assumptionOverrides || null
      })
    });

    if (finalResp.ok) {
      state.assessResult = await finalResp.json();
    } else {
      await runFallbackAssessment();
    }
  } catch (e) {
    console.error("Finalize call error:", e);
    await runFallbackAssessment();
  }

  goTo(4);
}

async function runFallbackAssessment() {
  try {
    // 第 ③ 步没跑完不等于"客户没有备份、客户全在员工手机里"：
    // 未采集的字段一律不发，后端会按中性值计入并在报告上标注未采集。
    const payload = {
      company_name: state.companyName,
      industry: state.industry,
      team_size: state.teamSize,
      annual_turnover: state.annualTurnover,
      website_status: state.websiteUrl ? state.websiteStatus : null
    };

    const resp = await fetch("/api/assess", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    if (resp.ok) {
      state.assessResult = await resp.json();
    }
  } catch (err) {
    console.error("Fallback assess failed:", err);
  }
}

// ─── Live Knowledge Topology Network (Stage 3 Center Panel) ───────────────────

function initKnowledgeGraph() {
  const container = $("knowledgeGraphContainer");
  if (!container) return;
  container.innerHTML = '<canvas id="topologyCanvas" style="width:100%; height:100%; display:block;"></canvas>';
  const canvas = $("topologyCanvas");
  if (canvas) {
    canvas.width = container.clientWidth || 360;
    canvas.height = container.clientHeight || 160;
  }
  renderKnowledgeGraph(state.wikiTree);
}

function renderKnowledgeGraph(tree) {
  const canvas = $("topologyCanvas");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  const w = canvas.width;
  const h = canvas.height;

  const dims = [
    { code: "web", name: "Website", x: 0.18, y: 0.35, verified: false },
    { code: "cloud", name: "Cloud", x: 0.50, y: 0.22, verified: false },
    { code: "crm", name: "CRM", x: 0.82, y: 0.35, verified: false },
    { code: "cyber", name: "CyberSec", x: 0.30, y: 0.72, verified: false },
    { code: "data", name: "Data/AI", x: 0.70, y: 0.72, verified: false }
  ];

  if (tree && tree.dimensions) {
    tree.dimensions.forEach(d => {
      const match = dims.find(m => m.code === d.dimension_code);
      if (match) match.verified = Boolean(d.is_verified);
    });
  }

  // Draw connecting links
  ctx.clearRect(0, 0, w, h);
  ctx.strokeStyle = "rgba(0, 140, 255, 0.30)";
  ctx.lineWidth = 1.5;

  const links = [
    [0, 1], [1, 2], [1, 3], [1, 4], [3, 4], [0, 3]
  ];

  links.forEach(([i, j]) => {
    ctx.beginPath();
    ctx.moveTo(dims[i].x * w, dims[i].y * h);
    ctx.lineTo(dims[j].x * w, dims[j].y * h);
    ctx.stroke();
  });

  // Draw dimension nodes
  dims.forEach(d => {
    const nx = d.x * w;
    const ny = d.y * h;

    if (d.verified) {
      ctx.beginPath();
      ctx.arc(nx, ny, 12, 0, Math.PI * 2);
      ctx.fillStyle = "rgba(48, 209, 88, 0.25)";
      ctx.fill();
    }

    ctx.beginPath();
    ctx.arc(nx, ny, 6, 0, Math.PI * 2);
    ctx.fillStyle = d.verified ? "#30d158" : "#64748b";
    ctx.fill();

    ctx.font = "10px -apple-system, BlinkMacSystemFont, sans-serif";
    ctx.fillStyle = d.verified ? "#38bdf8" : "#94a3b8";
    ctx.textAlign = "center";
    ctx.fillText(d.name, nx, ny - 10);
  });
}

// ─── Multimodal Voice Input & Waveform & Noise Filter (Stage 3) ───────────────

let isVoiceRecording = false;
let speechRecognizer = null;
let audioAnimId = null;

function toggleVoiceRecording() {
  if (isVoiceRecording) {
    stopVoiceRecording();
  } else {
    startVoiceRecording();
  }
}

function startVoiceRecording() {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  const btn = $("btnMicRecord");
  const micBtnText = $("micBtnText");

  if (!SpeechRecognition) {
    const transcript = prompt("This browser does not allow voice input here. Type what you would have said (Cradilot will strip the filler and keep the facts):");
    if (transcript) {
      filterSpeechNoise(transcript);
    }
    return;
  }

  try {
    speechRecognizer = new SpeechRecognition();
    speechRecognizer.lang = "zh-CN";
    speechRecognizer.continuous = false;
    speechRecognizer.interimResults = false;

    speechRecognizer.onstart = () => {
      isVoiceRecording = true;
      setOrbState("listening");
      if (btn) btn.classList.add("recording");
      if (micBtnText) micBtnText.textContent = "Listening... (click to stop)";
      startWaveformAnimation();
    };

    speechRecognizer.onresult = (event) => {
      if (event.results && event.results[0] && event.results[0][0]) {
        const transcript = event.results[0][0].transcript;
        filterSpeechNoise(transcript);
      }
    };

    speechRecognizer.onerror = (event) => {
      console.warn("Speech recognition notice:", event.error);
      stopVoiceRecording();
    };

    speechRecognizer.onend = () => {
      stopVoiceRecording();
    };

    speechRecognizer.start();
  } catch (err) {
    console.error("Failed to start speech recognition:", err);
    stopVoiceRecording();
  }
}

function stopVoiceRecording() {
  isVoiceRecording = false;
  if (speechRecognizer) {
    try { speechRecognizer.stop(); } catch (e) {}
    speechRecognizer = null;
  }
  const btn = $("btnMicRecord");
  const micBtnText = $("micBtnText");
  if (btn) btn.classList.remove("recording");
  if (micBtnText) micBtnText.textContent = "";
  stopWaveformAnimation();
  setOrbState("idle");
}

function startWaveformAnimation() {
  const canvas = $("audioWaveformCanvas");
  if (!canvas) return;
  // 先亮起来再量宽度：display:none 的元素量出来是 0
  canvas.classList.add("active");
  canvas.width = canvas.clientWidth || 320;
  canvas.height = canvas.clientHeight || 32;
  const ctx = canvas.getContext("2d");
  let step = 0;

  function draw() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.lineWidth = 2;
    ctx.strokeStyle = "rgba(0, 85, 255, 0.85)";
    ctx.beginPath();

    const slice = canvas.width / 40;
    for (let i = 0; i <= 40; i++) {
      const x = i * slice;
      const y = (canvas.height / 2) + Math.sin(i * 0.4 + step) * 10 * Math.sin(step * 0.5);
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }
    ctx.stroke();
    step += 0.15;
    audioAnimId = requestAnimationFrame(draw);
  }
  draw();
}

function stopWaveformAnimation() {
  if (audioAnimId) {
    cancelAnimationFrame(audioAnimId);
    audioAnimId = null;
  }
  const canvas = $("audioWaveformCanvas");
  if (canvas) {
    canvas.classList.remove("active");
    const ctx = canvas.getContext("2d");
    ctx.clearRect(0, 0, canvas.width, canvas.height);
  }
}

async function filterSpeechNoise(rawText) {
  if (!rawText || !rawText.trim()) return;
  setOrbState("analyzing");
  const inp = $("customAnswerInput");
  if (inp) inp.value = "Cleaning up what you said: " + rawText;

  try {
    const resp = await fetch("/api/speech/filter-noise", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        raw_text: rawText,
        session_id: state.sessionId
      })
    });
    if (!resp.ok) throw new Error("Noise filter error: " + resp.status);
    const data = await resp.json();
    if (inp) {
      inp.value = data.clean_text || rawText;
    }
  } catch (err) {
    console.error("Noise filter error:", err);
    if (inp) inp.value = rawText;
  } finally {
    setOrbState("idle");
  }
}

// ─── Sales Lead Dispatch Modal (One-click CRM Integration) ─────────────────────

function openSalesLeadModal() {
  const modal = $("salesLeadModal");
  if (!modal) return;

  if ($("salesContactName") && !$("salesContactName").value && state.companyName) {
    $("salesContactName").value = state.companyName + " — person in charge";
  }

  const statusBox = $("salesModalStatus");
  if (statusBox) statusBox.style.display = "none";

  modal.classList.add("is-open");
}

function closeSalesLeadModal() {
  const modal = $("salesLeadModal");
  if (modal) modal.classList.remove("is-open");
}

async function submitSalesLeadModal() {
  const name = $("salesContactName") ? $("salesContactName").value.trim() : "";
  const phone = $("salesContactPhone") ? $("salesContactPhone").value.trim() : "";
  const email = $("salesContactEmail") ? $("salesContactEmail").value.trim() : "";
  const time = $("salesCallbackTime") ? $("salesCallbackTime").value : "afternoon";
  const notes = $("salesNotes") ? $("salesNotes").value.trim() : "";
  const statusBox = $("salesModalStatus");
  const submitBtn = $("btnSubmitSalesLead");

  if (!name || !phone || !email) {
    alert("Please fill in the name of the person in charge, the WhatsApp number and the company email address.");
    return;
  }

  if (submitBtn) {
    submitBtn.disabled = true;
    submitBtn.textContent = "Sending to the consultant...";
  }

  try {
    const resp = await fetch("/api/sales/dispatch-lead", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: state.sessionId,
        contact_name: name,
        phone: phone,
        email: email,
        preferred_time: time,
        notes: notes
      })
    });

    if (!resp.ok) throw new Error("Dispatch lead failed: " + resp.status);
    const data = await resp.json();

    if (statusBox) {
      statusBox.style.display = "block";
      statusBox.style.background = "rgba(48, 209, 88, 0.15)";
      statusBox.style.color = "#15803d";
      statusBox.style.border = "1px solid rgba(48, 209, 88, 0.3)";
      statusBox.textContent = "Booking received. Record number: " + (data.lead_id || "LEAD-DISPATCHED") + ". A " + BRAND.vendor + " specialist will call you in the time slot you chose.";
    }

    setTimeout(() => {
      closeSalesLeadModal();
      if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.textContent = "Send to the consultant now";
      }
    }, 2000);

  } catch (err) {
    console.error("Submit sales lead modal error:", err);
    if (statusBox) {
      statusBox.style.display = "block";
      statusBox.style.background = "rgba(239, 68, 68, 0.12)";
      statusBox.style.color = "#b91c1c";
      statusBox.style.border = "1px solid rgba(239, 68, 68, 0.3)";
      statusBox.textContent = "That did not go through. Please try again, or call " + BRAND.vendor + " directly.";
    }
    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.textContent = "Send to the consultant now";
    }
  }
}

// ─── Stage 4: Scorecard & Business Bleeding Radar (Previously Stage 8) ────────

function initStage4Scorecard() {
  const res = state.assessResult;
  if (!res) return;

  const dms = res.dms || {};
  const ars = res.ars || {};

  // Company title
  if ($("s8Company")) {
    $("s8Company").textContent = state.companyName + " — full digital health report";
  }
  renderDataBasisBanner();

  // DMS score
  const dmsScore = dms.overall_score || 0;
  if ($("dmsNumber")) $("dmsNumber").textContent = Math.round(dmsScore);
  if ($("dmsGauge")) {
    $("dmsGauge").style.width = dmsScore + "%";
    if (dmsScore < 40) $("dmsGauge").classList.add("warn");
    else $("dmsGauge").classList.remove("warn");
  }

  const tier = dms.tier || "Not enough evidence from this run to place a tier";
  const tierBadge = $("dmsTierBadge");
  if (tierBadge) {
    tierBadge.textContent = tier;
    if (dmsScore < 40)       tierBadge.className = "score-tier vulnerable";
    else if (dmsScore < 70)  tierBadge.className = "score-tier transition";
    else                     tierBadge.className = "score-tier mature";
  }

  // 6-Dimension Grid
  const grid = $("dimensionGrid");
  if (grid) {
    grid.innerHTML = "";
    const dims = dms.dimensions || {};
    const dimLabels = {
      website: "Website and security",
      cloud: "Safe copies of your data",
      crm: "Sales pipeline and customer records",
      marketing: "Marketing and follow-up tracking",
      cybersecurity: "Email trust and impersonation defence",
      ai_adoption: "AI working around the clock"
    };
    const weightOf = key => {
      const w = (dms.weights || {})[key];
      return w ? Math.round(w * 100) + "% of the score" : "";
    };

    Object.entries(dims).forEach(([key, val]) => {
      const card = el("div", "dim-card card-3d");
      card.appendChild(el("div", "dim-name", dimLabels[key] || key));

      const headRow = el("div", "dim-card-head");
      headRow.appendChild(el("div", "dim-stars", val.stars || ""));
      headRow.appendChild(el("div", "dim-score", Math.round(val.score || 0)));
      const source = val.evidence_source || "";
      if (source) {
        headRow.appendChild(el("span", "dim-source dim-source-" + sourceClass(source), source));
      }
      card.appendChild(headRow);

      if (val.details) card.appendChild(el("div", "dim-details", val.details));
      const weight = weightOf(key);
      if (weight) card.appendChild(el("div", "dim-weight", weight));
      grid.appendChild(card);
    });
  }

  // ARS score & Hard-lock defense
  const arsScore = ars.final_score !== undefined ? ars.final_score : (ars.raw_score || 0);
  if ($("arsNumber")) $("arsNumber").textContent = Math.round(arsScore);
  if ($("arsGauge")) $("arsGauge").style.width = arsScore + "%";

  // 简报 Step 3 点名的五个就绪度因子：算过就要摊给客户看是凭什么算的
  const arsLabels = {
    leadership: "Owner commitment",
    data_availability: "One shared database",
    employee_skills: "Staff readiness",
    digital_workflow: "Handovers between roles",
    process_maturity: "Written procedures"
  };
  const arsGrid = $("arsFactorGrid");
  if (arsGrid) {
    arsGrid.innerHTML = "";
    Object.entries(ars.sub_scores || {}).forEach(([key, f]) => {
      const card = el("div", "dim-card card-3d");
      card.appendChild(el("div", "dim-name", arsLabels[key] || key));

      const headRow = el("div", "dim-card-head");
      headRow.appendChild(el("div", "dim-score", Math.round(f.score || 0)));
      const basis = f.basis === "verified_fact" ? "You stated" : "Inferred";
      headRow.appendChild(el("span", "dim-source dim-source-" + sourceClass(basis), basis));
      card.appendChild(headRow);

      if (f.note) card.appendChild(el("div", "dim-details", f.note));
      if (f.weight) card.appendChild(el("div", "dim-weight", Math.round(f.weight * 100) + "% of the score"));
      if (f.evidence_quote) card.title = 'You said: "' + f.evidence_quote + '"';
      arsGrid.appendChild(card);
    });
  }

  const isLocked = ars.is_hard_locked || dmsScore < 40;
  if ($("hardlockAlert")) {
    if (isLocked) {
      if ($("arsGauge")) $("arsGauge").classList.add("warn");
      $("hardlockAlert").classList.remove("hidden");
    } else {
      if ($("arsGauge")) $("arsGauge").classList.remove("warn");
      $("hardlockAlert").classList.add("hidden");
    }
  }

  // Populate financial loss
  populateLossBreakdown(res);

  // Stream strategic AI analysis
  streamDmsInsight(dms, isLocked);
}

function populateLossBreakdown(res) {
  const tree = res.wiki_tree || {};
  // 优先呈现证据驱动引擎输出的痛点（带原话引用），退回时使用 wiki 已锁证痛点；
  // 金额只来自 apply_loss_model，wiki 侧不再自带数字。
  const painPoints = (res.pain_points && res.pain_points.length > 0)
    ? res.pain_points
    : (tree.pain_points || []);

  const amountOf = p => (p.loss_myr === null || p.loss_myr === undefined || p.loss_myr === "")
    ? null : Number(p.loss_myr);
  const totalLoss = painPoints.reduce((sum, p) => sum + (amountOf(p) || 0), 0);

  if ($("totalLossDisplay")) {
    $("totalLossDisplay").textContent = totalLoss > 0
      ? "RM " + totalLoss.toLocaleString("en-MY", { minimumFractionDigits: 2, maximumFractionDigits: 2 })
      : "No money figure from this run";
  }

  const detailedContainer = $("painListDetailed");
  if (!detailedContainer) return;

  if (painPoints.length > 0) {
    detailedContainer.innerHTML = painPoints.map(p => {
      const amt = amountOf(p);
      return `
      <div style="margin-bottom: 8px; padding-bottom: 6px; border-bottom: 1px dashed rgba(255,59,48,0.20);">
        <div style="display: flex; justify-content: space-between;">
          <strong style="color: var(--blue-deep); font-size: 13px;">${p.title}</strong>
          ${amt
            ? `<span style="color: var(--crimson); font-weight: 700;">RM ${amt.toLocaleString("en-MY")} under the stated assumptions</span>`
            : `<span style="color: var(--text-tertiary); font-size: 11px;">${p.loss_basis || "no separate money figure"}</span>`}
        </div>
        <div style="color: var(--text-secondary); margin-top: 2px;">${p.evidence || p.root_cause || ""}</div>
        ${p.quote ? `<div style="color: var(--text-tertiary); margin-top: 2px; font-size: 11px;">In your own words: ${p.quote}</div>` : ""}
      </div>
    `}).join("");
  } else {
    detailedContainer.innerHTML = `
      <div style="color: var(--text-secondary); padding: 6px 0;">This interview did not confirm any blocker in the way you work. Cradilot will not invent a risk or an amount just to fill the list.</div>
    `;
  }
}

async function streamDmsInsight(dms, isLocked) {
  const seq = (state.insightSeq || 0) + 1;
  state.insightSeq = seq;
  if ($("dmsInsightLoading")) $("dmsInsightLoading").classList.remove("hidden");
  if ($("dmsInsightCursor")) $("dmsInsightCursor").classList.remove("hidden");
  if ($("dmsInsight")) $("dmsInsight").textContent = "";

  const dimensions = {};
  Object.entries(dms.dimensions || {}).forEach(([k, v]) => {
    dimensions[k] = { stars: v.stars, details: v.details || "", evidence: v.evidence_source || "" };
  });

  const promptAnswers = `Company: ${state.companyName}, Industry: ${state.industry}, Team size: ${state.teamSize}, Turnover: ${state.annualTurnover}`;

  try {
    await streamSSE("/api/chat/dms-insight", {
      company_name: state.companyName,
      industry: state.industry,
      dms_score: dms.overall_score,
      dms_tier: dms.tier || "",
      dimensions,
      user_answers: promptAnswers
    }, (chunk) => {
      if (state.insightSeq !== seq) return;          // 后发的流会覆盖，旧流不得再写入
      if ($("dmsInsight")) $("dmsInsight").textContent += chunk;
      state.dmsInsightText += chunk;
    });
  } catch (e) {
    console.warn("DMS insight stream unavailable, falling back to deterministic summary:", e);
    if (state.insightSeq === seq && $("dmsInsight")) {
      $("dmsInsight").textContent = deterministicDmsSummary(dms);
    }
  } finally {
    if (state.insightSeq === seq) {
      if ($("dmsInsightLoading")) $("dmsInsightLoading").classList.add("hidden");
      if ($("dmsInsightCursor")) $("dmsInsightCursor").classList.add("hidden");
    }
  }
}

function deterministicDmsSummary(dms) {
  // 全部句子只由本次真实算出的维度分与维度理由拼成，不预设立场
  const dims = Object.entries(dms.dimensions || {}).map(([k, v]) => ({ key: k, ...v }));
  const sorted = dims.slice().sort((a, b) => (a.score || 0) - (b.score || 0));
  const weakest = sorted.filter(d => (d.score || 0) < 70).slice(0, 2);
  const tier = dms.tier || "Not enough evidence from this run to place a tier";
  const bits = [`${state.companyName || "Your company"} scored ${Math.round(dms.overall_score || 0)} out of 100 on digital maturity in this run. ${tier}.`];
  if (weakest.length === 0) {
    bits.push("All six areas are already at 70 or above, so there is no gap in the basics that needs closing first.");
  } else {
    weakest.forEach(d => {
      bits.push(`${d.key} scored ${Math.round(d.score || 0)} (${d.evidence_source || "evidence source not stated"}): ${d.details || ""}`);
    });
  }
  bits.push("The above is the calculated result. The local language model was not reached in this run, so nothing beyond what was computed has been added.");
  return bits.join(" ");
}

// ─── Stage 5: Roadmap, ROI and the solution cart ──────

function initStage5Roadmap() {
  const res = state.assessResult;
  if (!res) return;

  const roi  = res.roi || {};
  const cart = res.cart || [];

  // ROI Hero metrics —— 数字全部来自 roi_engine 的确定性计算；None 表示"待报价"，不补任何默认值
  const dash = "—";
  const money = v => (v === null || v === undefined || v === "")
    ? dash : "RM " + Number(v).toLocaleString("en-MY", { maximumFractionDigits: 0 });

  const roiPct = (roi.roi_percentage === null || roi.roi_percentage === undefined)
    ? null : Number(roi.roi_percentage);
  // 比率被扣住时（待报价项没进分母），hero 改放已经算得出的年度收益
  const hero = $("roiPct");
  const heroLabel = $("roiHeroLabel");
  if (hero) {
    hero.textContent = roiPct !== null ? Math.round(roiPct) + "%"
      : (roi.total_benefits ? money(roi.total_benefits) : dash);
  }
  if (heroLabel) {
    heroLabel.textContent = roiPct !== null
      ? "First-year return on investment, based on the assumptions listed below"
      : (roi.cost_basis === "no_benefit_basis"
        ? "The baseline items were not collected in this run, so no return on investment is given"
        : "Yearly gain from the assumptions listed below (the return on investment is calculated once the pricing is complete)");
  }
  if ($("roiNetGain")) $("roiNetGain").textContent = money(roi.net_gain);
  if ($("roiInvestment")) $("roiInvestment").textContent = money(roi.vendor_annual_cost);
  if ($("roiLaborSavings")) $("roiLaborSavings").textContent = money(roi.annual_labor_savings);
  if ($("roiLeadRecovery")) $("roiLeadRecovery").textContent = money(roi.annual_salvaged_revenue);
  if ($("roiBasisNote")) $("roiBasisNote").textContent = roi.benchmark_note || "";

  renderRoiAssumptions(roi);
  renderDataBasisBanner();

  // 12-month Action Roadmap
  populateRoadmap(res);

  // Cart
  populateCart(cart);
}

const DATA_BASIS_TITLES = {
  interview_partial: "Basis of this data: the interview was only part finished",
  partial: "Basis of this data: only some of the current-state items were collected",
  basic_only: "Basis of this data: steps 1 and 2 only, plus the website inspection"
};

// 未采集的项按中性值计入，不写出来就会被读成"实测过且没问题"。
function renderDataBasisBanner() {
  const meta = (state.assessResult && state.assessResult.metadata) || {};
  const note = meta.data_basis_note || "";
  ["dataBasisBanner4", "dataBasisBanner5"].forEach(id => {
    const box = $(id);
    if (!box) return;
    box.innerHTML = "";
    if (!note) { box.hidden = true; return; }
    box.appendChild(el("div", "data-basis-title",
      DATA_BASIS_TITLES[meta.data_basis] || "About the data behind these figures"));
    box.appendChild(el("div", "data-basis-note", note));
    box.hidden = false;
  });
}

// ROI 的四个输入数字机检测不到：填过的就是自填，没填的是系统取的保守假设。
// 把出处摆在台面上并允许当场改写，比让评委以为这些是测量值安全得多。
const ROI_ASSUMPTION_FIELDS = [
  ["saved_hours_per_week", "hours / week", "number", "0.5"],
  ["missed_orders_per_month", "orders / month", "number", "1"],
  ["order_margin_myr", "RM / order", "number", "10"],
  ["monthly_salary_myr", "RM / month", "number", "100"]
];

function renderRoiAssumptions(roi) {
  const box = $("roiAssumptions");
  const actions = $("roiAssumptionActions");
  const hint = $("roiAssumptionHint");
  const model = roi && roi.assumptions;
  if (!box || !actions) return;

  if (!model || !model.values || Object.keys(model.values).length === 0) {
    box.hidden = true;
    actions.hidden = true;
    return;
  }

  box.innerHTML = "";
  const title = el("div", "roi-assumption-title", "Assumptions used (you can change these, then recalculate)");
  box.appendChild(title);

  ROI_ASSUMPTION_FIELDS.forEach(([key, unit, type, step]) => {
    const value = model.values[key];
    if (value === null || value === undefined) return;
    const row = el("div", "roi-assumption-row");
    const label = el("span", "roi-assumption-label", (model.labels || {})[key] || key);
    const input = document.createElement("input");
    input.className = "roi-assumption-input";
    input.type = type;
    input.step = step;
    input.min = "0";
    input.value = String(value);
    input.dataset.assumptionKey = key;
    const unitTag = el("span", "roi-assumption-unit", unit);
    const source = (model.sources || {})[key] || "";
    const badge = el("span",
      "roi-assumption-src" + (source.indexOf("Entered by you") >= 0 ? " src-filled" : " src-assumed"),
      source);
    row.append(label, input, unitTag, badge);
    box.appendChild(row);
  });

  actions.hidden = false;
  box.hidden = false;
  if (hint) hint.textContent = "";

  const btn = $("roiRecalcBtn");
  if (btn) {
    // 每次重渲染都换掉监听器，避免叠加出多次请求
    const next = btn.cloneNode(true);
    btn.parentNode.replaceChild(next, btn);
    next.addEventListener("click", async () => {
      const overrides = {};
      box.querySelectorAll(".roi-assumption-input").forEach(inp => {
        const v = parseFloat(inp.value);
        if (!isNaN(v) && v > 0) overrides[inp.dataset.assumptionKey] = v;
      });
      if (hint) hint.textContent = "Recalculating with the new assumptions...";
      next.disabled = true;
      try {
        const resp = await fetch("/api/diag/finalize", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ session_id: state.sessionId, assumptions: overrides })
        });
        if (resp.ok) {
          state.assessResult = await resp.json();
          initStage5Roadmap();
          if (hint) hint.textContent = "Recalculated with your numbers.";
        } else {
          if (hint) hint.textContent = "Recalculation failed: " + resp.status;
        }
      } catch (e) {
        if (hint) hint.textContent = "Recalculation failed: the network or the backend did not answer.";
      } finally {
        next.disabled = false;
      }
    });
  }
}

function renderSolutionSummary(card, sol) {
  const box = el("div", "solution-summary");
  box.appendChild(el("div", "ss-title", "The whole package — from the website inspection"));
  if (sol.note) box.appendChild(el("div", "ss-note", sol.note));
  (sol.conclusions || []).forEach(c => {
    const row = el("div", "ss-row rate-" + String(c.rate || "na").toLowerCase());
    row.appendChild(el("span", "ss-rate", String(c.rate || "N/A")));
    row.appendChild(el("span", "ss-name", c.title || ""));
    row.appendChild(el("span", "ss-result", c.result || ""));
    box.appendChild(row);
  });
  const prods = el("div", "ss-products");
  (sol.products || []).forEach(p => {
    const one = el("span", "ss-product");
    one.appendChild(el("b", "", p.name || p.sku || ""));
    one.appendChild(el("span", "ss-price", " " + (p.price_label || "")));
    prods.appendChild(one);
  });
  if ((sol.products || []).length) box.appendChild(prods);
  card.appendChild(box);
}

// 推荐引擎的比较层：简报要的"explain WHY"就印在这里，金额一律用后端算好的 price_label
function stripLead(text, leads) {
  let body = String(text || "").trim();
  leads.forEach(lead => {
    if (body.indexOf(lead) === 0) body = body.slice(lead.length);
  });
  return body.charAt(0).toUpperCase() + body.slice(1);
}

function renderOptionMatrix(card, p) {
  const blocks = p.option_matrix || [];
  if (!blocks.length) return;

  const CHOSEN_LEADS = ["Chosen: ", "Recommended, even though we cannot sell it to you: ",
    "Recommended, and it costs you nothing from us: "];
  const box = el("div", "phase-options");
  box.appendChild(el("div", "phase-opt-title", "Options we compared for this phase"));
  blocks.forEach(blk => {
    if (blk.question) box.appendChild(el("div", "phase-opt-q", blk.question));
    const chosen = blk.chosen || {};
    const bought = blk.purchase !== false;
    const row = el("div", "phase-opt-row " + (bought ? "phase-opt-chosen" : "phase-opt-alt"));
    row.appendChild(el("span", "phase-opt-name", bought
      ? ("We picked: " + (chosen.product_name || "") + (chosen.price_label ? (" — " + chosen.price_label) : ""))
      : ("We recommend: " + (chosen.product_name || "") + " — not something we can bill you for")));
    const why = stripLead(chosen.why, CHOSEN_LEADS);
    if (why) row.appendChild(el("div", "phase-opt-why", why));
    box.appendChild(row);
    (blk.also_considered || []).forEach(alt => {
      const sold = alt.purchasable !== false;
      const diy = alt.price_state === "no_purchase";
      const line = el("div", "phase-opt-row phase-opt-alt");
      const lead = sold ? "Also compared: " : (diy ? "Compared, and nothing to buy: " : "Not sold here: ");
      const price = (sold || diy) && alt.price_label ? (" — " + alt.price_label) : "";
      line.appendChild(el("span", "phase-opt-name", lead + (alt.product_name || "") + price));
      if (alt.why_not) line.appendChild(el("div", "phase-opt-why", stripLead(alt.why_not, ["Not this time: "])));
      box.appendChild(line);
    });
  });
  if (p.option_matrix_note) box.appendChild(el("div", "phase-opt-note", p.option_matrix_note));
  card.appendChild(box);
}

function roadmapOf(res) {
  const rec = res.recommendation || {};
  const list = res.roadmap || rec.roadmap || rec.phases || [];
  return Array.isArray(list) ? list : [];
}

function populateRoadmap(res) {
  const container = $("roadmapPhases");
  if (!container) return;
  container.innerHTML = "";

  const phases = roadmapOf(res);
  if (phases.length === 0) {
    container.appendChild(el("div", "phase-empty",
      "No phase plan came out of this session. The blueprint will not pad the page with template cards."));
    if ($("roadmapLoading")) $("roadmapLoading").classList.add("hidden");
    renderTimelineCanvas([]);
    return;
  }

  phases.forEach((p, i) => {
    const card = el("div", "phase-card card-3d");
    card.id = "phaseCard" + i;
    card.appendChild(el("div", "phase-number", String(i + 1).padStart(2, "0")));
    card.appendChild(el("div", "phase-label",
      (p.phase || p.phase_title || ("Phase " + (i + 1))) + (p.timeline ? (" · " + p.timeline) : "")));
    if (p.solution_summary) {
      renderSolutionSummary(card, p.solution_summary);
    } else if (i === 0) {
      card.appendChild(el("div", "ss-empty",
        "No website inspection result backs this session, so the package below is built from "
        + "what you told us in the interview alone."));
    }

    (p.modules || []).forEach(m => {
      card.appendChild(el("div", "phase-action", "• " + m));
    });

    (p.budget_lines || []).forEach(l => {
      const row = el("div", "phase-cost");
      row.appendChild(el("span", "phase-cost-name", l.product_name || l.sku));
      row.appendChild(el("span", "phase-cost-val",
        "RM " + Number(l.annual_myr || 0).toLocaleString("en-MY", { minimumFractionDigits: 2 })));
      card.appendChild(row);
    });
    (p.pricing_pending || []).forEach(t => {
      card.appendChild(el("div", "phase-cost-pending", "• " + t));
    });
    (p.third_party_notes || []).forEach(t => {
      card.appendChild(el("div", "phase-cost-pending", "• " + t));
    });

    if (p.budget_myr) {
      card.appendChild(el("div", "phase-total",
        BRAND.vendor + " products for this phase, yearly total: RM " + Number(p.budget_myr).toLocaleString("en-MY",
          { minimumFractionDigits: 2 }) +
        (p.seats_used ? (" (priced on " + p.seats_used + " seats)") : "")));
    }
    renderOptionMatrix(card, p);
    if (p.acceptance) {
      card.appendChild(el("div", "phase-accept", "How you check it is done: " + p.acceptance));
    }
    if (p.roi_milestone) {
      card.appendChild(el("div", "phase-roi", p.roi_milestone));
    }
    if (p.hard_locked) {
      card.appendChild(el("div", "phase-locked", "This phase is on hold: it does not start until the phase before it has been checked off"));
    }
    container.appendChild(card);
  });

  if ($("roadmapLoading")) $("roadmapLoading").classList.add("hidden");
  renderTimelineCanvas(phases);
}

// 时间轴画布：节点内容全部来自上面同一份路线图，不再预置任何模块名
function renderTimelineCanvas(phases) {
  for (let i = 1; i <= 3; i++) {
    const node = $("tlNode" + i);
    if (!node) continue;
    const p = phases[i - 1];
    node.classList.remove("phase-locked-node");
    const badge = node.querySelector(".node-badge");
    const time = node.querySelector(".node-time");
    const title = node.querySelector(".node-title");
    const modules = node.querySelector(".node-modules");
    const chip = node.querySelector(".node-roi-chip");
    const gate = node.querySelector(".node-gate-tag");

    if (!p) {
      node.classList.add("node-empty");
      if (badge) badge.textContent = "Phase " + i;
      if (time) time.textContent = "Not scheduled";
      if (title) title.textContent = "No data for this phase";
      if (modules) modules.textContent = "The blueprint did not produce content for this phase";
      if (chip) chip.textContent = "—";
      if (gate) gate.textContent = "—";
      continue;
    }
    if (badge) badge.textContent = "Phase " + i;
    if (time) {
      const roiWindow = p.timeline || "";
      // 第 2、3 阶段的回报窗口本身就是月份区间，再标一次是重复；只有第 1 阶段
      // "ROI 2-4 周"与"第 1-3 月"不是同一件事，才把实施月份补上去。
      const norm = (s) => String(s || "").toLowerCase().replace(/months?/, "m").replace(/\s+/g, "");
      const runs = p.months && norm(p.months) !== norm(roiWindow) ? ("runs " + p.months) : "";
      time.textContent = [roiWindow, runs].filter(Boolean).join(" · ");
    }
    if (title) title.textContent = p.phase_title || p.phase || "";
    if (modules) {
      modules.innerHTML = "";
      (p.tasks || []).forEach(t => {
        const line = el("div", "node-module-line", "• " + (t.title || ""));
        modules.appendChild(line);
      });
      if (!(p.tasks || []).length) {
        modules.textContent = "Nothing to add in this phase";
      }
    }
    if (chip) {
      chip.textContent = p.budget_myr
        ? ("RM " + Number(p.budget_myr).toLocaleString("en-MY", { maximumFractionDigits: 0 }) + " a year")
        : "No publicly priced item in this phase";
    }
    if (gate) gate.textContent = p.hard_locked ? "On hold: starts after the first two phases are checked off" : "Can start now";
    if (p.hard_locked) node.classList.add("phase-locked-node");
  }
}

function focusPhaseCard(idx) {
  for (let i = 1; i <= 3; i++) {
    const node = $("tlNode" + i);
    if (node) {
      if (i === idx + 1) node.classList.add("active-node");
      else node.classList.remove("active-node");
    }
  }

  const targetCard = $("phaseCard" + idx);
  if (targetCard) {
    targetCard.scrollIntoView({ behavior: "smooth", block: "center" });
    targetCard.style.borderColor = "var(--blue-primary)";
    targetCard.style.boxShadow = "0 0 0 3px rgba(0, 85, 255, 0.25)";
    setTimeout(() => {
      targetCard.style.borderColor = "";
      targetCard.style.boxShadow = "";
    }, 2000);
  }
}

function populateCart(cart) {
  const cartList = $("cartList");
  if (!cartList) return;
  cartList.innerHTML = "";
  let total = 0;

  if (cart && cart.length > 0) {
    cart.forEach(item => {
      const row = el("div", "cart-item");
      const name = el("div", "cart-item-name", item.product_name || item.sku);
      const pr = Number(item.promotional_price_myr || item.regular_price_myr || 0);
      const price = el("div", "cart-item-price", "RM " + pr.toLocaleString("en-MY", { minimumFractionDigits: 2 }));
      row.append(name, price);
      cartList.appendChild(row);
      total += pr;
    });
  } else {
    const empty = el("div", "cart-empty",
      "There is no publicly priced item to recommend from this run. A " + BRAND.vendor + " account manager prices "
      + "the package against your actual seat and module count, so no products or amounts are listed in advance.");
    cartList.appendChild(empty);
  }

  $("cartTotal").textContent = "RM " + total.toLocaleString("en-MY", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

// ─── PDF Blueprint Generation ──────────────────────────────────────────────────

async function downloadPdf(targetBtnId = "downloadPdfBtn") {
  let res = state.assessResult;
  if (!res && state.sessionId) {
    try {
      const finResp = await fetch("/api/diag/finalize", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: state.sessionId })
      });
      if (finResp.ok) {
        res = await finResp.json();
        state.assessResult = res;
      }
    } catch (e) {
      console.warn("Auto-finalize for PDF error:", e);
    }
  }

  if (!res) {
    alert("Finish the assessment first, so there is something to put in the blueprint.");
    return;
  }

  const btn = $(targetBtnId) || $("downloadPdfBtn");
  const originalText = btn ? btn.textContent : "Download this blueprint as a PDF";
  if (btn) {
    btn.textContent = "Building your blueprint PDF...";
    btn.disabled = true;
  }

  try {
    const desk = consultantDeskValues();
    const payload = Object.assign({}, res, {
      metadata: Object.assign({}, res.metadata, {
        consultant_notes: desk.consultant_notes,
        assigned_to: desk.assigned_to
      })
    });
    const resp = await fetch("/api/pdf/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    if (!resp.ok) throw new Error("PDF generation failed: " + resp.status);

    const blob = await resp.blob();
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement("a");
    a.href     = url;
    a.download = "Cradilot_Blueprint_" + (state.companyName || "SME").replace(/\s+/g, "_") + ".pdf";
    a.click();
    URL.revokeObjectURL(url);

    if (btn) btn.textContent = "Blueprint PDF downloaded";
    setTimeout(() => {
      if (btn) {
        btn.textContent = originalText;
        btn.disabled = false;
      }
    }, 4000);

  } catch (e) {
    console.error("PDF download failed:", e);
    if (btn) {
      btn.textContent = "The PDF took too long — please try again";
      btn.disabled = false;
    }
  }
}

// ─── Sales Lead Submission & Consultation Booking ──────────────────────────────

function toggleLeadForm() {
  const form = $("leadForm");
  if (form) form.classList.toggle("hidden");
}

// 顾问备注与指派：同一份内容要同时进销售档案与下载的 PDF，否则顾问打电话前看不到客户拿到的那份
function consultantDeskValues() {
  return {
    consultant_notes: (($("consultantNotes") && $("consultantNotes").value) || "").trim(),
    assigned_to: (($("assignedTo") && $("assignedTo").value) || "").trim()
  };
}

async function saveConsultantDesk() {
  const hint = $("consultantDeskHint");
  const desk = consultantDeskValues();
  if (!desk.consultant_notes && !desk.assigned_to) {
    if (hint) hint.textContent = "Both the notes and the assignment are empty, so there is nothing to save.";
    return;
  }
  if (!state.leadId) {
    if (hint) hint.textContent = "Saved here. It goes into the record when the booking is sent.";
    return;
  }
  if (hint) hint.textContent = "Saving...";
  try {
    const resp = await fetch("/api/sales/update-lead-status", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        lead_id: state.leadId,
        consultant: desk.assigned_to,
        consultant_notes: desk.consultant_notes
      })
    });
    if (!resp.ok) throw new Error("HTTP " + resp.status);
    const data = await resp.json();
    if (hint) {
      hint.textContent = "Saved to record " + state.leadId
        + (data.assigned_to ? " (assigned to: " + data.assigned_to + ")" : "")
        + ", status: " + (data.status || "updated");
    }
  } catch (e) {
    console.error("Consultant desk update failed:", e);
    if (hint) hint.textContent = "Save failed: the sales record service did not answer.";
  }
}

async function submitLead() {
  const name  = ($("contactName").value || "").trim();
  const phone = ($("contactPhone").value || "").trim();
  const email = ($("contactEmail").value || "").trim() || "lead@example.com";

  if (!name)  { alert("Please type your name."); $("contactName").focus(); return; }
  if (!phone) { alert("Please type your phone number (WhatsApp)."); $("contactPhone").focus(); return; }

  const res = state.assessResult;
  if (!res) { alert("The assessment result is missing. Please send the booking again."); return; }

  try {
    const resp = await fetch("/api/sales/submit-lead", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        assessment_data: res,
        contact_info: {
          contact_name:  name,
          contact_phone: phone,
          contact_email: email,
          company_name:  state.companyName,
          industry:      state.industry,
          team_size:     state.teamSize,
          annual_turnover: state.annualTurnover
        },
        notes: state.dmsInsightText.substring(0, 300),
        consultant_notes: consultantDeskValues().consultant_notes,
        assigned_to: consultantDeskValues().assigned_to
      })
    });

    if (!resp.ok) throw new Error("Submit lead failed: " + resp.status);
    const data = await resp.json();
    state.leadId = data.lead_id || "";

    $("leadForm").innerHTML =
      '<div style="text-align:center; padding: 24px;">' +
      '<div class="stage-label" style="margin-bottom: 8px; color: #1a8a35;">Booking sent</div>' +
      '<p style="font-size:15px; color: var(--text-primary); line-height:1.6;">' +
      'Thank you, ' + name + '. A ' + BRAND.vendor + ' digital consultant will call you within 24 hours.' +
      '</p>' +
      '<p style="font-size:12px; color: var(--text-tertiary); margin-top: 8px;">Record number: ' + data.lead_id + '</p>' +
      '</div>';

  } catch (e) {
    console.error("Lead submission failed:", e);
    alert("That did not go through. Please try again, or call " + BRAND.vendor + " directly.");
  }
}

function resetAssessment() {
  state.companyName = "";
  state.industry = "";
  state.teamSize = "";
  state.annualTurnover = "";
  state.biggestChallenge = "";
  state.currentTools = "";
  state.growthObjective = "";
  state.websiteUrl = "";
  state.websiteStatus = "none";
  state.sessionId = "";
  state.assessResult = null;
  state.leadId = "";
  if ($("consultantNotes")) $("consultantNotes").value = "";
  if ($("assignedTo")) $("assignedTo").value = "";
  state.currentTurn = 1;
  state.exploredCount = 0;
  state.diagPhase = "ask";

  if ($("companyName")) $("companyName").value = "";
  if ($("websiteUrlInput")) $("websiteUrlInput").value = "";
  if ($("customChallengeInput")) $("customChallengeInput").value = "";
  if ($("customToolsInput")) $("customToolsInput").value = "";
  if ($("customObjectiveInput")) $("customObjectiveInput").value = "";

  // Reset dynamically generated options in step 1
  if ($("options1_2")) $("options1_2").innerHTML = "";
  if ($("options1_3")) $("options1_3").innerHTML = "";
  if ($("options1_4")) $("options1_4").innerHTML = "";
  if ($("options1_5")) $("options1_5").innerHTML = "";
  if ($("options1_6")) $("options1_6").innerHTML = "";
  if ($("options1_7")) $("options1_7").innerHTML = "";
  initStep1Live();
  showStep1Sub(1);

  // Clear probe options
  if ($("diagOptions")) $("diagOptions").innerHTML = "";

  goTo(0);
}

// ─── SSE Streaming Helper ──────────────────────────────────────────────────────

async function streamSSE(endpoint, body, onChunk) {
  const resp = await fetch(endpoint, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body)
  });

  if (!resp.ok) throw new Error("SSE endpoint error: " + resp.status);

  const reader = resp.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop();

    for (const line of lines) {
      if (line.startsWith("data: ")) {
        const payload = line.slice(6);
        if (payload === "[DONE]") return;
        const text = payload.replace(/\\n/g, "\n");
        if (text) onChunk(text);
      }
    }
  }
}

// ─── Boot & Event Listeners ────────────────────────────────────────────────────

function boot() {
  updateProgress(0);
  loadIndustryCatalog();
  initStep1Live();

  const nameInput = $("companyName");
  if (nameInput) {
    nameInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        submitCompanyNameLive();
      }
    });
  }

  const urlInput = $("websiteUrlInput");
  if (urlInput) {
    urlInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        runWebsiteScraper();
      }
    });
  }

  const customAnswerInput = $("customAnswerInput");
  if (customAnswerInput) {
    customAnswerInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        submitCustomDiagAnswer();
      }
    });
  }

  document.querySelectorAll(".stage").forEach((s, i) => {
    if (i !== 0) {
      s.style.display = "none";
      s.classList.remove("active");
    }
  });
}

document.addEventListener("DOMContentLoaded", boot);

