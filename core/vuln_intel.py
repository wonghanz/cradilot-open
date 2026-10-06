"""
Cradilot Core - 已知漏洞与版本寿命情报关联 (Known-CVE / EOL correlation)

第 ② 步机检的"网络专家视角"来源。输入是官网指纹得到的 组件→版本，
输出是可逐条复述的情报结论：公开公告编号、严重度、官方修复版本、
是否已被列入 CISA 已知在利用清单、该版本线是否已停止安全维护。

数据源（2026-09-18/19 本机实测，全部免 key）
  · api.osv.dev/v1/query        GHSA 公告 + CVE 别名 + 严重度 + 修复版本，约 0.5s
  · endoflife.date/api/*.json   php / nginx / mysql / wordpress 各版本线的真实 EOL 日期
  · CISA KEV 全量 JSON          1715 条 / 1.7MB / 0.5s，用于标"已被实际利用"
  · api.wordpress.org           WP 核心当前版本、插件最新版本与最后更新时间

实测到的负面结论，直接决定了这里的边界（写错数据源等于结论全错）：
  · OSV 对 WordPress 核心与插件均无覆盖：{"name":"WordPress","ecosystem":"WordPress"}
    version 5.8.1 返回 0 条，而该版本明确有公开 CVE。因此 WordPress 一律走
    api.wordpress.org + endoflife.date，绝不向 OSV 查询后凭"0 命中"下"无漏洞"结论。
  · WPScan / Wordfence Intelligence 需注册 key，Patchstack 端点返回的是页面不是 JSON，
    NVD keywordSearch 用插件名会 0 命中且 burst 到第 8 次即 429。这些都不作为依赖。
  · securityheaders.com 的公开 API 已被 Snyk 下线，不可依赖。

诚实性约束：任一情报源不可达时返回 status="unverified"，
调用方不得把它折算成"未发现漏洞"，更不得折算成扣分。
"""

import json
import os
import re
import time
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional, Sequence, Tuple

import httpx

CACHE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "cache")
KEV_URL = ("https://www.cisa.gov/sites/default/files/"
           "feeds/known_exploited_vulnerabilities.json")
OSV_URL = "https://api.osv.dev/v1/query"
EOL_URL = "https://endoflife.date/api/{product}.json"
WP_PLUGIN_URL = "https://api.wordpress.org/plugins/info/1.2/"

LOOKUP_TIMEOUT_SECONDS = float(os.getenv("CRADILOT_VULN_TIMEOUT", "9.0"))
KEV_CACHE_TTL = 7 * 86400          # 在利用清单每天更新，本地缓存 7 天足够
EOL_CACHE_TTL = 30 * 86400
MAX_OSV_COMPONENTS = 12            # 单次审计对外查询上限，避免拖垮 5 分钟硬指标

# 停更多久算"该插件大概没人管了"。取 18 个月：WordPress 官方目录自身的活跃度门槛，
# 短于此值的告警在大马 SME 站上一律是噪音。
STALE_PLUGIN_MONTHS = 18

_SEVERITY_RANK = {"CRITICAL": 0, "HIGH": 1, "MODERATE": 2, "MEDIUM": 2,
                  "LOW": 3, "": 4}


# ─── 组件指纹：只从已经取回的 HTML/响应头里读，不额外发包 ──────────────────────
_VERSION = r"(\d+\.\d+(?:\.\d+)?)"

# 库版本只认资源路径里的版本号，绝不认 ?ver=。实测 wordpress.org 自身输出
# /wp-includes/js/jquery/jquery.min.js?ver=7.2-alpha-63675 —— 那个 ver 是 WP 核心版本，
# 当成 jQuery 版本去查公告，就会把完全不相干的 CVE 算到客户头上。
_ASSET_URL = re.compile(r"""(?:src|href)\s*=\s*["']([^"']+\.(?:js|css))["']""",
                        re.IGNORECASE)

# (标签, ecosystem, OSV 包名, 作用于单个资源路径的正则, 主版本约束)
_OSV_ASSETS: Tuple[Tuple[str, str, str, str, Optional[str]], ...] = (
    # migrate 与 jquery 是两个包：顺序在前 + 负向断言，双保险防串号
    ("jQuery Migrate", "npm", "jquery-migrate", r"jquery-migrate[^0-9a-z]?" + _VERSION, None),
    ("jQuery", "npm", "jquery", r"jquery(?!-migrate)[^0-9a-z]?" + _VERSION, None),
    ("Bootstrap", "npm", "bootstrap", r"bootstrap[^0-9a-z]?" + _VERSION, None),
    ("Moment.js", "npm", "moment", r"moment(?:\.timezone)?[^0-9a-z]?" + _VERSION, None),
    ("Swiper", "npm", "swiper", r"swiper[^0-9a-z]?(?:bundle[^0-9a-z]?)?" + _VERSION, None),
    ("AngularJS", "npm", "angular", r"angular[^0-9a-z]?" + _VERSION, None),
    ("Vue", "npm", "vue", r"vue(?:\.runtime)?[^0-9a-z]?" + _VERSION, None),
    # Font Awesome 5.0 改了包名：用错名字查到 0 条，会被当成"该组件无漏洞"
    ("Font Awesome", "npm", "@fortawesome/fontawesome-free",
     r"font-?awesome[^0-9a-z]?" + _VERSION, ">=5"),
    ("Font Awesome", "npm", "font-awesome", r"font-?awesome[^0-9a-z]?" + _VERSION, "<5"),
)

# 服务端软件：OSV 无覆盖，用 endoflife.date 判版本线是否已停维护
_EOL_PRODUCTS: Tuple[Tuple[str, str, str, str], ...] = (
    # (标签, endoflife slug, 取值来源, 正则)
    ("PHP", "php", "header:x-powered-by", r"php[ /]?v?" + _VERSION),
    ("nginx", "nginx", "header:server", r"nginx/" + _VERSION),
    ("WordPress", "wordpress", "html", r"<meta[^>]+generator[^>]+wordpress[/ ]?" + _VERSION),
    ("WordPress", "wordpress", "html", r"wordpress\.org/\?v=" + _VERSION),
    ("WordPress", "wordpress", "html", r"wp-includes/[a-z/.\-]+\.(?:js|css)\?ver=" + _VERSION),
)

_HEADER_SOURCES = {"header:x-powered-by": "x-powered-by", "header:server": "server"}


def _to_version(text: str) -> Tuple[int, ...]:
    parts = re.match(r"(\d+)\.(\d+)(?:\.(\d+))?", str(text or "").strip())
    if not parts:
        return ()
    return tuple(int(x) for x in parts.groups() if x)


def compare_versions(a: str, b: str) -> int:
    """-1 / 0 / 1。缺位按 0 补齐，"6.7" 与 "6.7.0" 视为相等。"""
    va, vb = _to_version(a), _to_version(b)
    n = max(len(va), len(vb))
    va += (0,) * (n - len(va))
    vb += (0,) * (n - len(vb))
    return (va > vb) - (va < vb)


def _major_ok(version: str, requirement: Optional[str]) -> bool:
    """包名会随大版本改名（Font Awesome 5.0），查错包会 0 命中并被当成"无漏洞"。"""
    if not requirement:
        return True
    major = _to_version(version)[:1]
    if not major:
        return False
    req = re.match(r"(>=|<)\s*(\d+)", requirement)
    if not req:
        return False
    bound = int(req.group(2))
    return major[0] >= bound if req.group(1) == ">=" else major[0] < bound


def fingerprint_components(html: str,
                           headers: Optional[Dict[str, str]] = None,
                           extra_blobs: Sequence[str] = ()) -> List[Dict[str, Any]]:
    """
    从被动取回的内容里抽取"组件 + 版本"。

    extra_blobs 用于传入 /feed/ 等非首页响应体——WP 的 <generator> 在那里比在首页更稳。
    只读已下载内容，不因此函数产生任何新请求。
    """
    headers = headers or {}
    blob = "\n".join([html or "", *extra_blobs])[:400_000]
    found: Dict[Tuple[str, str, str], Dict[str, Any]] = {}

    asset_paths = []
    for url in _ASSET_URL.findall(blob):
        path = url.split("?", 1)[0].split("#", 1)[0]
        asset_paths.append(urllib.parse.unquote(path))

    for label, eco, pkg, pattern, major_req in _OSV_ASSETS:
        for path in asset_paths:
            hit = re.search(pattern, path, re.IGNORECASE)
            if not hit:
                continue
            version = hit.group(1)
            if not _major_ok(version, major_req):
                continue
            found.setdefault((label, eco, pkg),
                             {"label": label, "ecosystem": eco, "package": pkg,
                              "version": version,
                              "evidence": hit.group(0)[:70],
                              "source": "asset_fingerprint"})
            break

    for label, slug, origin, pattern in _EOL_PRODUCTS:
        if origin in _HEADER_SOURCES:
            text = headers.get(_HEADER_SOURCES[origin], "")
        else:
            text = blob
        hit = re.search(pattern, text or "", re.IGNORECASE)
        if hit:
            key = (label, "eol", slug)
            found.setdefault(key, {"label": label, "ecosystem": None, "package": slug,
                                  "version": hit.group(1),
                                  "evidence": hit.group(0)[:80],
                                  "source": "eol_line"})
    return list(found.values())


def extract_wordpress_plugins(html: str) -> List[Dict[str, str]]:
    """从页面资源路径里取插件与主题的 slug（不含版本——WP 的 ?ver= 多半是站点版本，
    拿它当插件版本会大面积误报，因此版本一律不猜，只判"是否停更/是否落后官方"）。"""
    out: Dict[str, Dict[str, str]] = {}
    for kind, pattern in (("plugin", r"/wp-content/plugins/([a-z0-9_\-\.]+)/"),
                          ("theme", r"/wp-content/themes/([a-z0-9_\-\.]+)/")):
        for slug in re.findall(pattern, (html or "")[:400_000], re.IGNORECASE):
            s = slug.strip().strip("-._").lower()
            if len(s) >= 2 and s not in out:
                out[s] = {"kind": kind, "slug": s}
    return list(out.values())[:24]


# ─── 本地缓存：演示断网也要能复述上次结论（并如实标注日期） ─────────────────────
def _cache_path(name: str) -> str:
    return os.path.join(CACHE_DIR, name)


def _read_cache(name: str, ttl: float) -> Tuple[Optional[Any], Optional[float]]:
    path = _cache_path(name)
    try:
        age = time.time() - os.path.getmtime(path)
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh), age
    except Exception:
        return None, None


def _write_cache(name: str, payload: Any) -> None:
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        with open(_cache_path(name), "w", encoding="utf-8") as fh:
            json.dump(payload, fh)
    except Exception:
        pass          # 缓存只是加速与离线兜底，写不进去不影响结论


def _get_json(url: str, params: Optional[Dict[str, Any]] = None) -> Any:
    with httpx.Client(timeout=LOOKUP_TIMEOUT_SECONDS, follow_redirects=True) as client:
        resp = client.get(url, params=params, headers={"accept": "application/json"})
        resp.raise_for_status()
        return resp.json()


def _post_json(url: str, payload: Dict[str, Any]) -> Any:
    with httpx.Client(timeout=LOOKUP_TIMEOUT_SECONDS) as client:
        resp = client.post(url, json=payload, headers={"accept": "application/json"})
        resp.raise_for_status()
        return resp.json()


# ─── CISA KEV：已被真实利用的漏洞清单 ─────────────────────────────────────────
def kev_index() -> Dict[str, Any]:
    """返回 {"by_cve": {cve小写: 条目}, "as_of": 目录版本, "from_cache": bool, "error": str|None}"""
    cached, age = _read_cache("kev.json", KEV_CACHE_TTL)
    if cached is not None and age is not None and age < KEV_CACHE_TTL:
        return _kev_build(cached, from_cache=True, age=age)
    try:
        data = _get_json(KEV_URL)
        _write_cache("kev.json", data)
        return _kev_build(data, from_cache=cached is not None,
                          age=age if cached is not None else 0.0)
    except Exception as exc:
        if cached is not None:
            return _kev_build(cached, from_cache=True, stale=True, age=age or 0.0)
        return {"by_cve": {}, "as_of": None, "total": 0, "from_cache": False,
                "stale": False, "error": f"{type(exc).__name__}: {exc}"}


def _kev_build(data: Dict[str, Any], from_cache: bool = False,
               age: float = 0.0, stale: bool = False) -> Dict[str, Any]:
    entries = data.get("vulnerabilities") or []
    return {
        "by_cve": {str(e.get("cveID", "")).lower(): e for e in entries if e.get("cveID")},
        "as_of": data.get("catalogVersion"),
        "total": data.get("count", len(entries)),
        "from_cache": from_cache,
        "cache_age_days": round(age / 86400, 1),
        "stale": stale,
        "error": None,
    }


def is_exploited(cve_id: Optional[str], kev: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not cve_id:
        return None
    return (kev.get("by_cve") or {}).get(str(cve_id).lower())


# ─── OSV：开源组件公开公告 ────────────────────────────────────────────────────
def _osv_one(component: Dict[str, Any]) -> Dict[str, Any]:
    try:
        data = _post_json(OSV_URL, {"package": {"name": component["package"],
                                                "ecosystem": component["ecosystem"]},
                                    "version": component["version"]})
        return {"component": component, "error": None, "vulns": data.get("vulns") or []}
    except Exception as exc:
        return {"component": component, "error": f"{type(exc).__name__}: {exc}",
                "vulns": []}


def osv_advisories(components: Sequence[Dict[str, Any]],
                   max_workers: int = 6) -> Dict[str, Any]:
    """
    查询开源组件的公开公告。只接受有明确版本号的组件——
    没有版本时查全量会把十年前的公告也算到客户头上，那是吓唬人不是做评估。
    """
    targets = [c for c in components
               if c.get("ecosystem") and c.get("version")][:MAX_OSV_COMPONENTS]
    if not targets:
        return {"available": False, "skipped": "no versioned open-source component was identified that could be looked up",
                "hits": [], "errors": [], "queried": []}

    hits: List[Dict[str, Any]] = []
    errors: List[str] = []
    queried: List[str] = []
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        for fut in as_completed([pool.submit(_osv_one, c) for c in targets]):
            res = fut.result()
            comp = res["component"]
            label = f"{comp['package']}@{comp['version']}"
            if res["error"]:
                errors.append(f"{label}: {res['error']}")
                continue
            queried.append(label)
            for v in res["vulns"]:
                aliases = [a for a in (v.get("aliases") or []) if str(a).startswith("CVE-")]
                fixed = _first_fixed(v, comp["version"])
                hits.append({
                    "id": v.get("id"),
                    "cve": aliases[0] if aliases else None,
                    "summary": (v.get("summary") or "").strip(),
                    "severity": ((v.get("database_specific") or {}).get("severity") or "").upper(),
                    "fixed_in": fixed,
                    "package": comp["package"],
                    "component_label": comp["label"],
                    "installed_version": comp["version"],
                })
    return {"available": bool(queried), "skipped": None if queried else "none of the lookups completed",
            "hits": hits, "errors": errors, "queried": queried}


def _first_fixed(vuln: Dict[str, Any], installed: str) -> Optional[str]:
    """取"大于当前版本的最早修复版本"，而不是公告里任意一个 fixed。"""
    candidates: List[str] = []
    for affected in vuln.get("affected") or []:
        for rng in affected.get("ranges") or []:
            for event in rng.get("events") or []:
                f = event.get("fixed")
                if f and _to_version(f):
                    candidates.append(f)
    newer = [c for c in candidates if compare_versions(c, installed) > 0]
    if not newer:
        return candidates[0] if candidates else None
    return sorted(newer, key=_to_version)[0]


# ─── endoflife.date：版本线是否已停止安全维护 ─────────────────────────────────
def _cycle_of(version: str) -> Optional[str]:
    parts = re.match(r"(\d+)\.(\d+)", str(version or ""))
    if parts:
        return f"{parts.group(1)}.{parts.group(2)}"
    major = re.match(r"(\d+)", str(version or ""))
    return major.group(1) if major else None


def eol_status(product: str, version: str) -> Dict[str, Any]:
    """
    返回 {"state": "eol"|"supported"|"unknown", "cycle", "eol_date", "latest", "error"}
    按版本线（major.minor）匹配；不猜、不用记忆里的日期。
    """
    cycle = _cycle_of(version)
    if not cycle:
        return {"state": "unknown", "reason": "the version number could not be parsed"}
    cached, age = _read_cache(f"eol_{product}.json", EOL_CACHE_TTL)
    if cached is None:
        try:
            cached = _get_json(EOL_URL.format(product=product))
            _write_cache(f"eol_{product}.json", cached)
        except Exception as exc:
            return {"state": "unknown", "error": f"{type(exc).__name__}: {exc}"}

    today = time.strftime("%Y-%m-%d")
    for entry in cached or []:
        if str(entry.get("cycle")) != str(cycle):
            continue
        eol = entry.get("eol")
        if eol in (False, None):
            return {"state": "supported", "cycle": cycle, "latest": entry.get("latest")}
        if isinstance(eol, (int, float)):      # 少数产品给的是年份
            eol = f"{int(eol)}-01-01"
        eol_str = str(eol)[:10]
        return {
            "state": "eol" if eol_str < today else "supported",
            "cycle": cycle, "eol_date": eol_str, "latest": entry.get("latest"),
            "cache_age_days": round(age / 86400, 1) if age else 0.0,
        }
    # 该版本线不在清单里：官方已不再为它发布任何更新
    return {"state": "eol", "cycle": cycle, "not_listed": True,
            "latest": (cached or [{}])[0].get("latest") if cached else None}


# ─── WordPress 专属：官方目录比对 ─────────────────────────────────────────────
def wordpress_plugin_status(slug: str, kind: str = "plugin") -> Dict[str, Any]:
    """
    比对官方目录的最新版与最后更新时间。这是 OSV/WPScan 之外唯一免 key 的可靠路径：
    OSV 对 WP 插件 0 覆盖，WPScan 要 key，所以这里判的是"还在不在维护、落后多少"，
    而不是断言某个具体 CVE。
    """
    action = "plugin_information" if kind == "plugin" else "theme_information"
    try:
        data = _get_json(WP_PLUGIN_URL,
                         {"action": action, "request[slug]": slug})
    except Exception as exc:
        return {"state": "unreachable", "slug": slug,
                "error": f"{type(exc).__name__}: {exc}"}
    if not isinstance(data, dict):
        return {"state": "error", "slug": slug, "reason": "the directory reply was not in the expected form"}
    if data.get("error") or not data.get("name"):
        # 不在官方目录 = 商业授权或自研：没有上游补丁通道也无法自动更新，
        # 这本身就是一条结论，不能与"目录没访问到"混为一谈。
        return {"state": "not_in_directory", "slug": slug}
    last = str(data.get("last_updated") or "")
    months = _months_since(last)
    return {
        "state": "stale" if (months or 0) > STALE_PLUGIN_MONTHS else "current",
        "slug": slug,
        "name": data.get("name"),
        "latest": data.get("version"),
        "tested_up_to": data.get("tested"),
        "last_updated": last.split(" ")[0] or None,
        "months_since_update": months,
        "active_installs": data.get("active_installs"),
    }


def _months_since(text: str) -> Optional[int]:
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", text or "")
    if not m:
        return None
    then = time.mktime((int(m.group(1)), int(m.group(2)), int(m.group(3)),
                        0, 0, 0, 0, 0, -1))
    return int((time.time() - then) // (86400 * 30.44))


# ─── 汇总 ─────────────────────────────────────────────────────────────────────
def build_report(html: str, headers: Dict[str, str],
                 extra_blobs: Sequence[str] = (),
                 wp_plugins: Optional[Sequence[Dict[str, str]]] = None) -> Dict[str, Any]:
    """
    一次机检的情报汇总。返回给 site_audit 组装成 findings——
    本模块只出事实，措辞与销售导向由调用方决定，便于单独测试。
    """
    components = fingerprint_components(html, headers, extra_blobs)
    osv = osv_advisories(components)
    kev = kev_index()

    hits: List[Dict[str, Any]] = []
    for h in osv["hits"]:
        entry = is_exploited(h.get("cve"), kev)
        h["known_exploited"] = bool(entry)
        if entry:
            h["kev_action_due"] = entry.get("dueDate")
            h["kev_required_action"] = entry.get("requiredAction")
            h["kev_ransomware"] = entry.get("knownRansomwareCampaignUse") == "Known"
        hits.append(h)
    hits.sort(key=lambda x: (_SEVERITY_RANK.get(x.get("severity") or "", 4),
                             0 if x.get("known_exploited") else 1))

    eol_checks: List[Dict[str, Any]] = []
    for comp in components:
        if comp.get("source") == "eol_line":
            status = eol_status(comp["package"], comp["version"])
            status["label"] = comp["label"]
            status["installed"] = comp["version"]
            eol_checks.append(status)

    return {
        "components": components,
        "osv_available": osv["available"],
        "osv_queried": osv["queried"],
        "osv_errors": osv["errors"],
        "osv_skipped": osv["skipped"],
        "hits": hits,
        "exploited": [h for h in hits if h.get("known_exploited")],
        "eol": eol_checks,
        "eol_lines_dead": [e for e in eol_checks if e.get("state") == "eol"],
        "wp_plugins": list(wp_plugins or []),
        "kev_as_of": kev.get("as_of"),
        "kev_stale": kev.get("stale"),
        "kev_error": kev.get("error"),
        "kev_total": kev.get("total"),
        "coverage_note": "The open-source advisory database does not cover WordPress core or its plugins; that part is judged by comparing against the official "
                         "released versions instead, so zero hits in the advisory database must never be read as no vulnerabilities.",
    }
