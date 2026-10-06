"""
Cradilot Core - 网站形态识别 (Site Signals & Level Classification)

为什么要这一层
──────────────
248 项检查全对每个站跑，既慢又蠢：没有登录框的站去查 IDOR，没有购物车的站去查
支付绕过，最后报告又长又空。用户给的原则是"看到什么功能，就开启对应模块"。

本模块只做一件事：从**已经抓到的首页 HTML 与响应头**里判断这个站具备哪些功能特征
（零额外请求），再据此定 L1-L5 层级。判定结果决定 data/audit_checklist.json 里
哪些条目"适用"、哪些条目直接 not_applicable（并写明因为没看到什么而不适用）。

不猜、不脑补：每个信号都留下它命中的原文片段（evidence），PDF 与界面都能回答
"凭什么说我有 API"。没命中就是没有，且这是"不适用"而不是"不合格"。
"""

from typing import Any, Dict, List, Optional, Tuple
import re

# 信号名 -> (说明, 命中的正则)。说明会被拼进"这项为什么不适用"里给客户看，所以是英文；
# 正则里的中文备选保持不动，中文站照样要能命中。
SIGNAL_PATTERNS: Dict[str, Tuple[str, str]] = {
    "login_form": ("a login entry point or password field",
                   r'type\s*=\s*["\']password|/login\b|log\s*in|sign\s*in|my\s*account|客户登录'),
    "register_form": ("a self-service registration link",
                      r'register\b|sign\s*up|create\s*(an?\s*)?account|注册'),
    "account_portal": ("a member area, console or dashboard",
                        r'/account\b|/dashboard\b|client\s*area|member\s*area|customer\s*portal|dashboard'),
    "form_present": ("any form on the page", r'<\s*form\b'),
    "lead_form": ("an enquiry or contact form",
                  r'<\s*form\b[^>]*(contact|enquir|inquir|quote|request|get-?in-?touch|callback)|'
                  r'name\s*=\s*["\'](subject|message|company|phone|enquiry|inquiry)'),
    "search_or_query": ("site search or a query parameter",
                        r'type\s*=\s*["\']search|/search\b|\?[sq]=|action\s*=\s*["\'][^"\']*\?'),
    "url_param_present": ("a link parameter that can steer a redirect or load target",
                          r'[?&](url|redirect|redirect_to|next|return(url)?|target|dest(ination)?|go)\s*='),
    "file_param_present": ("a parameter that names a file or page path",
                           r'[?&](file|path|page|include|doc|template|download|lang)\s*='),
    "upload_form": ("a file upload control", r'type\s*=\s*["\']file|enctype\s*=\s*["\']multipart'),
    "user_generated_content": ("visitor-writable content such as comments or reviews",
                               r'\bcomment[s]?\b|#comments|reviews?\b|forum|/member/|/profile/'),
    "url_fetch_feature": ("a parameter that makes the server fetch an external address",
                          r'[?&](fetch|proxy|url|src|image_?url|endpoint|load|u)\s*='),
    "api_surface": ("API endpoints called by the front end",
                    r'["\']/api/|/rest/v\d|/wp-json/|/graphql\b|api\.[a-z0-9.-]+/|\.php\?(action|api)\b'),
    "api_xml": ("an XML or SOAP interface", r'\.xml\b|soap|application/(?:soap\+)?xml'),
    "js_bundle_present": ("bundled front-end scripts", r'src\s*=\s*["\'][^"\']+\.(?:m?js)(?:\?|$|")'),
    "webhook_present": ("a webhook callback endpoint", r'/webhook\b|webhook_?url'),
    "cloud_storage_url": ("an object-storage address referenced by the page",
                          r's3[.-][a-z0-9-]+\.amazonaws\.com|\.blob\.core\.windows\.net|'
                          r'storage\.googleapis\.com|\.digitaloceanspaces\.com|\.r2\.dev'),
    "cms_wordpress": ("a WordPress installation",
                      r'wp-content|wp-includes|generator"\s*content\s*=\s*"WordPress'),
    "cms_drupal_joomla": ("a Drupal or Joomla installation",
                          r'/sites/default/files|Joomla|Drupal\.settings'),
    "store_platform": ("an e-commerce storefront platform",
                       r'woocommerce|wp-json/wc/|shopify|magento|opencart|BigCommerce|wix-store'),
    "checkout_present": ("a cart or checkout flow",
                         r'/cart\b|/checkout\b|add-?to-?cart|/product/\b|\bRM\s?\d+\s*(only|now)|buy\s*now'),
    "payment_widget": ("a payment provider component",
                       r'paypal|stripe|molpay|ip?p?ay|razerx?|razorpay|billplz|econs?olidated|'
                       r'cardnumber|credit ?card form'),
    "chat_widget": ("a live chat or AI assistant widget",
                    r'intercom|drift\.com|tawk\.to|crisp\.chat|zdassets|zopim|gorgias|livechat|'
                    r'tidio|jivochat|manychat|botpress|\bchat-?widget\b'),
    "ga4": ("Google Analytics 4 or gtag", r'googletagmanager\.com/gtag/js\?id=G-|gtag\(\s*[\'"]config'),
    "gtm": ("Google Tag Manager", r'googletagmanager\.com/gtm\.js'),
    "meta_pixel": ("the Meta pixel", r'connect\.facebook\.net/[a-z]+/fbevents\.js|fbq\(\s*[\'"]init'),
    "structured_data": ("JSON-LD structured data", r'<script[^>]*application/ld\+json'),
    "llms_txt_link": ("a link to llms.txt", r'llms\.txt'),
    "what_they_sell": ("a product, service or price listing",
                       r'(?i)\b(products?|services?|solutions?|pricing|catalogue|catalog)\b|RM\s?\d'),
    "who_for": ("a statement of who the service is for",
                r'(?i)\b(for|tailored|serving)\b[^<]{0,80}\b(owners?|business|contractors?|'
                r'students?|homeowners?|factories?|trade|B2B|SME)s?\b'),
    "quantified_results": ("numbers that back a claim",
                           r'\d+\s*(years?|clients?|projects?|orders?|installs?|%|\+)'),
    "certifications": ("a certification or licence",
                       r'(?i)\b(ISO\s?\d+|CIDB|SIRIM|MESTI|SSM|licence|license|certified|'
                       r'certification)\b'),
    "customer_logos": ("client or partner brands shown",
                       r'(?i)(our\s+clients|trusted\s+by|brands?\s+we|partners?)'
                       r'|<img[^>]+alt="[^"]*(client|partner|brand)'),
    "case_studies": ("case studies or completed projects",
                     r'(?i)\b(case stud|project gallery|our work|portfolio|installation)s?\b'),
    "testimonials": ("customer testimonials", r'(?i)\b(testimonial|what our|reviews?|feedback)s?\b'),
    "awards": ("an award or third-party recognition",
               r'(?i)\b(award[- ]winning|awarded|best of|winner of|recognized|recognised|'
               r'top\s?\d+\s*(provider|vendor|supplier)|rated|star(-rated)?|ranking)s?\b'),
    "contact_channel": ("a direct contact channel",
                        r'tel:|mailto:|wa\.me|whatsapp|\+?60\s?1\d[\s-]?\d{3}'),
    "whatsapp_cta": ("a WhatsApp click-to-chat link", r'wa\.me/|api\.whatsapp\.com|whatsapp'),
    "quote_request": ("a request-a-quote entry point",
                      r'(?i)(request|ask for|get)\s*a?\s*(quote|quotation|price list)'),
    "privacy_policy": ("a privacy policy link", r'(?i)privacy\s*(policy|notice)'),
    "terms_published": ("a terms of service link", r'(?i)terms\s*(of|and)?\s*(use|service|sale)'),
    "cookie_notice": ("a cookie or consent notice",
                      r'(?i)cookie\s*(consent|policy|notice)|onetrust|cookiebot'),
    "company_registration": ("a company registration number",
                             r'(?i)(SSM|company|registration|roc)\s*(no|number|#|:)?\s*\.?\s*[0-9]{6,12}'),
    "physical_address": ("a physical street address",
                         r'(?i)\b(lot\s?\d+|jalan\s|jln\s|lorong\s|taman\s|sek(?:sys|s)?\s?\d+|'
                         r'section\s\d+|address\b)[a-z0-9 ,#/\.\-]{4,}'
                         r'(,\s*(w\.?p\.?|selangor|pulau pinang|johor|perak|negeri sembilan|melaka|'
                         r'pahang|kedah|kelantan|terengganu|sabah|sarawak|labuan|malaysia))?'),
    "iot_surface": ("a device, firmware or IoT interface",
                    r'(?i)\b(mqtt|zigbee|z-?wave|esp32|tuya|loRa)\b|'
                    r'firmware\s?(update|version|ota)|over-?the-?air|device\s?(pairing|management|console)|'
                    r'/api/device|sensor\s?network'),
    "websocket": ("a WebSocket channel", r'wss?://|new WebSocket\('),
    "ai_agent_surface": ("an autonomous agent or tool-calling capability",
                         r'(?i)\b(ai agent|autonomous|function call|tool use|agentic)\b'),
    "openapi_doc": ("machine-readable API documentation",
                    r'(?i)(swagger-ui|openapi\.(ya?ml|json)|/docs/?(api)?|redoc)'),
    "multilingual": ("multiple language versions", r'(?i)(lang="ms|lang="en|hreflang|bahasa)'),
}

# 页面上直接写出来的密钥形态：命中即 CRITICAL，因为"发布"就已经是泄露。
SECRET_PATTERNS: Dict[str, str] = {
    "Google API key": r'AIza[0-9A-Za-z_\-]{35}',
    "AWS access key": r'AKIA[0-9A-Z]{16}',
    "Stripe live key": r'sk_live_[0-9a-zA-Z]{24,}',
    "OpenAI key": r'sk-[A-Za-z0-9]{20,}',
    "Slack token": r'xox[baprs]-[0-9A-Za-z-]{10,}',
    "Private key block": r'-----BEGIN (?:RSA |EC |OPENSSH |)PRIVATE KEY',
    "Connection string": r'(?:mongodb|mysql|postgres(?:ql)?|mssql)://[^"\'\s:]+:[^"\'\s@]+@',
}

# 层级门槛：从最具体的形态往下退，第一个命中的就是本站层级。
_LEVEL_RULES: List[Tuple[int, str, Tuple[str, ...]]] = [
    (5, "AI / IoT / cloud platform", ("iot_surface", "ai_agent_surface")),
    (4, "E-commerce (cart, checkout, payments)", ("checkout_present", "store_platform")),
    (3, "SaaS or portal (accounts, APIs, dashboards)", ("account_portal", "api_surface", "websocket")),
    (2, "Interactive website (login / forms / CMS)",
     ("login_form", "lead_form", "form_present", "cms_wordpress", "cms_drupal_joomla", "search_or_query")),
]


def detect_signals(html: str, headers: Optional[Dict[str, str]] = None) -> Dict[str, Dict[str, Any]]:
    """返回 {signal: {"present": bool, "note": 说明, "evidence": 命中片段}}。"""
    text = html or ""
    blob = text[:1_200_000]
    out: Dict[str, Dict[str, Any]] = {}
    for name, (note, pattern) in SIGNAL_PATTERNS.items():
        hit = re.search(pattern, blob)
        out[name] = {
            "present": bool(hit),
            "note": note,
            "evidence": _clip(hit.group(0)) if hit else "",
        }
    # 响应头能证实的形态：CDN/WAF 与服务器栈，不看正文
    hdrs = {str(k).lower(): str(v) for k, v in (headers or {}).items()}
    edge = any(t in (hdrs.get("server", "") + hdrs.get("cf-ray", "") + "".join(hdrs.get("set-cookie", "")))
               for t in ("cloudflare", "cf-ray", "__cf_bm", "akamai", "fastly", "sucuri", "x-wsrl"))
    if edge:
        out["edge_cdn"] = {"present": True, "note": "a CDN or edge network shown in the response headers",
                           "evidence": _clip(hdrs.get("server", "") or hdrs.get("cf-ray", ""))}
    else:
        out["edge_cdn"] = {"present": False, "note": "no CDN or edge network shown in the response headers", "evidence": ""}
    # 组合信号：清单里 CORS / 令牌这类判据只在"有接口或有登录态"的站上才该开
    api_or_login = [s for s in ("api_surface", "login_form") if out[s]["present"]]
    out["api_or_login"] = {
        "present": bool(api_or_login),
        "note": "an API endpoint or a login entry point",
        "evidence": ", ".join(out[s]["evidence"] for s in api_or_login if out[s]["evidence"]),
    }
    return out


def find_secrets(html: str) -> List[Dict[str, str]]:
    """页面里直接写出来的凭据。只读已抓到的内容，不请求任何私有路径。"""
    hits: List[Dict[str, str]] = []
    blob = (html or "")[:400_000]
    for label, pattern in SECRET_PATTERNS.items():
        m = re.search(pattern, blob)
        if m:
            hits.append({"kind": label, "masked": _mask(m.group(0))})
    return hits


def classify_level(signals: Dict[str, Dict[str, Any]]) -> Tuple[int, str, List[str]]:
    """定 L1-L5，并回带定级的依据（哪个信号命中）。"""
    for level, label, triggers in _LEVEL_RULES:
        fired = [t for t in triggers if signals.get(t, {}).get("present")]
        if fired:
            return level, label, fired
    return 1, "Basic website", []


def present_signals(signals: Dict[str, Dict[str, Any]]) -> List[str]:
    return sorted(k for k, v in signals.items() if v.get("present"))


def _clip(value: str, limit: int = 90) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    return text if len(text) <= limit else text[:limit - 1] + "…"


def _mask(value: str) -> str:
    text = str(value or "")
    if len(text) <= 12:
        return text[:2] + "****"
    return f"{text[:6]}…{text[-4:]} ({len(text)} chars)"
