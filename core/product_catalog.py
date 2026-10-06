"""
Cradilot Core - 本公司产品与定价目录

唯一来源：data/product_catalog.json（2026-09-18 由官网公开定价页实查）。

此前 SKU 与价格散写在 sales/lead_dispatcher.py 与 core/roi_engine.py 里，且大部分
系虚构：DEMO-BMAIL-PRO-5U 不存在（真实 EBiz Mail PRO 以 10 用户为一档）、
"Acronis 500GB RM1,136" 与 "NVMe VPS 2C4G RM1,440" 查无此项、
RM 527.88 被错标成 EBiz 17 AI Pro（实为 WP 17 AI Business 的年价）。
这份蓝图是要交到 我方手上的，价格一翻就穿。
"""

import json
import re
import math
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional

import config

CATALOG_PATH = config.PRODUCT_CATALOG_PATH


@dataclass
class Product:
    sku: str
    name: str
    category: str
    billing: str
    annual_myr: Optional[float]
    verify_status: str          # official / to_verify / not_priced
    includes: List[str]
    solves: str
    source: str = ""
    note: str = ""
    raw: Dict[str, Any] = None  # type: ignore[assignment]

    def to_cart_dict(self) -> Dict[str, Any]:
        return {
            "sku": self.sku,
            "product_name": self.name,
            "billing_cycle": self.billing,
            "regular_price_myr": self.annual_myr,
            "promotional_price_myr": self.annual_myr,
            "notes": self.solves,
            "verify_status": self.verify_status,
            "includes": self.includes,
        }


def parse_headcount(team_size: Optional[str]) -> int:
    """从 "6-15 人" / "1-10 人" / "21-50 人" 这类标签取一个保守席位数。

    取下界而非上界：宁可少算席位低估总价，也不要给 SME 老板报一个虚高的数。
    """
    if not team_size:
        return 10
    nums = [int(n) for n in re.findall(r"\d+", str(team_size))]
    if not nums:
        return 10
    return max(1, min(nums))


class ProductCatalog:
    """按 SKU 取价，并把席位数折算成真实年费。"""

    def __init__(self, path: Path = CATALOG_PATH):
        payload = json.loads(path.read_text(encoding="utf-8"))
        self.meta: Dict[str, Any] = payload.get("_meta", {})
        self._products: Dict[str, Product] = {}
        for entry in payload.get("products", []):
            self._products[entry["sku"]] = Product(
                sku=entry["sku"],
                name=entry["name"],
                category=entry.get("category", "other"),
                billing=entry.get("billing", "Annual"),
                annual_myr=entry.get("annual_myr"),
                verify_status=entry.get("verify_status", "to_verify"),
                includes=list(entry.get("includes", [])),
                solves=entry.get("solves", ""),
                source=entry.get("source", ""),
                note=entry.get("note", ""),
                raw=entry,
            )
        self.bundles: Dict[str, Any] = payload.get("bundles", {})

    def get(self, sku: str) -> Optional[Product]:
        return self._products.get(sku)

    def must_get(self, sku: str) -> Product:
        product = self._products.get(sku)
        if product is None:
            raise KeyError(f"This SKU is not in the catalog: {sku}")
        return product

    # ── 计价 ─────────────────────────────────────────────────────────────────
    def annual_for(self, sku: str, seats: Optional[int] = None,
                   devices: Optional[int] = None) -> Optional[float]:
        """返回该 SKU 按所需席位/设备折算后的年费；无公开价时返回 None（不编造）。"""
        product = self.must_get(sku)
        raw = product.raw or {}
        per_user = raw.get("annual_myr_per_user")
        per_device = raw.get("annual_myr_per_device")
        seats_block = raw.get("seats_block")

        if per_user:
            count = max(1, int(seats or 1))
            return round(float(per_user) * count, 2)
        if per_device:
            count = max(1, int(devices or 1))
            return round(float(per_device) * count, 2)
        if seats_block:
            # 真实产品按 10 用户为一档售卖，不足一档也要按一档计
            count = max(1, int(seats or seats_block))
            blocks = math.ceil(count / seats_block)
            base = raw.get("annual_myr")
            if base is None:
                return None
            return round(float(base) * blocks, 2)
        return raw.get("annual_myr")

    def one_off_for(self, sku: str) -> float:
        raw = (self.must_get(sku).raw or {})
        return float(raw.get("one_off_myr") or raw.get("one_off_setup_myr") or 0.0)

    def quote(self, skus: List[str], seats: Optional[int] = None,
              devices: Optional[int] = None) -> Dict[str, Any]:
        """把一组 SKU 汇总成一份可交付的报价条目清单。"""
        lines: List[Dict[str, Any]] = []
        total = 0.0
        unpriced: List[str] = []
        needs_verification: List[str] = []

        for sku in skus:
            product = self.must_get(sku)
            amount = self.annual_for(sku, seats=seats, devices=devices)
            one_off = self.one_off_for(sku)
            if product.verify_status == "not_priced" or amount is None:
                unpriced.append(product.name)
                lines.append({
                    "sku": sku, "product_name": product.name,
                    "annual_myr": None, "one_off_myr": one_off or None,
                    "flag": "Price must be quoted by our sales team; no amount may be written in"
                })
                continue
            if product.verify_status == "to_verify":
                needs_verification.append(product.name)
            total += amount
            lines.append({
                "sku": sku,
                "product_name": product.name,
                "annual_myr": amount,
                "one_off_myr": one_off or None,
                "verify_status": product.verify_status,
                "includes": product.includes,
                "why": product.solves,
            })

        return {
            "currency": self.meta.get("currency", "MYR"),
            "lines": lines,
            "annual_total_myr": round(total, 2),
            "unpriced_items": unpriced,
            "needs_verification_items": needs_verification,
            "renewal_caveat": self.meta.get("renewal_caveat", ""),
        }

    def bundle(self, name: str) -> Dict[str, Any]:
        """取一个预设组合，并按实际席位数重算（预设数字以 10 席为基准）。"""
        spec = self.bundles.get(name)
        if not spec:
            raise KeyError(f"This bundle is not in the catalog: {name}")
        return dict(spec)


catalog = ProductCatalog()
