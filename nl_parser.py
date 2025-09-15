"""Lightweight rule-based NL -> filter extraction to reduce reliance on LLM.

This module parses common query patterns for the product catalog and returns
structured filters that can be deterministically compiled into safe SQL.

If parsing yields no actionable filters (e.g., highly complex comparative
requests), the caller can fall back to an LLM based generation path.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Set, Optional


# ---------------------------- Data Structures ---------------------------- #


@dataclass
class ParsedQuery:
    families: List[str] = field(default_factory=list)          # Canonical family names (as in DB)
    features: List[str] = field(default_factory=list)          # Positive feature tokens (description ILIKE)
    exclude_features: List[str] = field(default_factory=list)  # Negative feature tokens (NOT ILIKE)
    brands: List[str] = field(default_factory=list)            # manufacturer_slug values
    price_max: Optional[float] = None
    currency: Optional[str] = None
    used_rule_based: bool = False  # Indicates if anything meaningful detected

    def is_actionable(self) -> bool:
        return any([
            self.families, self.features, self.exclude_features,
            self.brands, self.price_max is not None
        ])


# ----------------------------- Vocabulary Maps --------------------------- #

# Canonical families present in dataset (observed from CSVs)
DATASET_FAMILIES = {
    "cameras": {"camera", "cameras", "bullet", "dome", "ptz"},
    # Use recorder accessories as a catch-all for mounts, brackets, recorders, and switches in our dataset
    "recorder accessories": {"nvr", "recorder", "dvr", "server", "mount", "bracket", "pole mount", "wall mount", "junction box", "switch"},
    "power supply": {"power supply", "power", "psu"},
    "access": {"access", "door", "rfid", "keypad"},
    "audio and power accessories": {"audio", "microphone", "speaker", "mic"},
    "software and licensing": {"software", "license", "licensing", "ai license"},
}

# Feature tokens -> raw substrings looked up via ILIKE
FEATURE_TOKENS = {
    "outdoor": ["outdoor"],
    "indoor": ["indoor"],
    "vandal": ["vandal"],
    "bullet": ["bullet"],
    "dome": ["dome"],
    "ptz": ["ptz"],
    "poe": ["poe", "hpoe"],
    "ir": [" ir", "ir "],  # generic IR mention (bounded by space to reduce noise)
    "ai": [" ai", "ai "],
}

# Brand / manufacturer slug mapping
BRAND_MAP = {
    "axis": "axis",
    "hanwha": "hanwha",
    "wisenet": "hanwha",  # brand synonym
    "i-pro": "i-pro",
    "ipro": "i-pro",
    "panasonic": "i-pro",  # i-PRO historically panasonic security
}

# Exclusion phrases (token -> underlying feature tokens to exclude)
EXCLUSION_PATTERNS = {
    r"no ptz": ["ptz"],
    r"avoid ptz": ["ptz"],
    r"without ptz": ["ptz"],
}


PRICE_PATTERN = re.compile(
    r"(?:under|below|less than|max(?:imum)?|<=?)\s*([$€£]?)(\d+(?:\.\d+)?)\s*(usd|cad|eur)?",
    re.IGNORECASE,
)
CURRENCY_NORMALIZE = {"$": None, "usd": "USD", "cad": "CAD", "eur": "EUR"}


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


def parse_query(text: str) -> ParsedQuery:
    parsed = ParsedQuery()
    if not text:
        return parsed
    original = text
    text = _normalize(text)

    # Families
    families_found: Set[str] = set()
    for family, triggers in DATASET_FAMILIES.items():
        for trig in triggers:
            if re.search(rf"\b{re.escape(trig)}s?\b", text):
                families_found.add(family)
                break

    # Features (positive)
    feature_hits: Set[str] = set()
    for canonical, variants in FEATURE_TOKENS.items():
        for variant in variants:
            if variant in f" {text} ":  # crude boundary
                feature_hits.add(canonical)
                break

    # Brands
    brands_found: Set[str] = set()
    for token, slug in BRAND_MAP.items():
        if re.search(rf"\b{re.escape(token)}\b", text):
            brands_found.add(slug)

    # Price + currency
    price_match = PRICE_PATTERN.search(text)
    if price_match:
        symbol, amount_str, cur = price_match.groups()
        try:
            parsed.price_max = float(amount_str)
        except ValueError:
            parsed.price_max = None
        cur_norm = cur.lower() if cur else CURRENCY_NORMALIZE.get(symbol)
        if cur_norm:
            parsed.currency = cur_norm.upper()

    # IR distance patterns e.g. "IR 30m" "IR 60m" -> treat as feature tokens '30m', '60m'
    ir_distance = re.findall(r"ir\s*(\d{2,3})m", text)
    for dist in ir_distance:
        feature_hits.add(f"{dist}m")

    # Zoom patterns like 20x, 30x appear, but also quantities like "3x". Heuristic: treat as zoom only if >= 10x
    zooms = re.findall(r"(\d{1,3})x", text)
    for z in zooms:
        try:
            if int(z) >= 10:
                feature_hits.add(f"{z}x")
        except ValueError:
            continue

    # Exclusions
    exclude_features: Set[str] = set()
    for pattern, feats in EXCLUSION_PATTERNS.items():
        if re.search(pattern, text):
            exclude_features.update(feats)

    # If user mentions only features / brand but no family, default to cameras (dominant use case)
    if not families_found and (feature_hits or brands_found):
        families_found.add("cameras")

    parsed.families = sorted(families_found)
    parsed.features = sorted(feature_hits)
    parsed.exclude_features = sorted(exclude_features)
    parsed.brands = sorted(brands_found)
    parsed.used_rule_based = parsed.is_actionable()
    return parsed


def build_sql_from_parsed(parsed: ParsedQuery) -> Optional[str]:
    """Compile a ParsedQuery into a safe SQL string limited to the products table.

    Business rules:
      - Always active = true
      - One cheapest record per family (LIMIT 1 ORDER BY price ASC)
      - Multi-family -> CTE per family + UNION ALL
    """
    if not parsed.is_actionable():
        return None

    def _escape(val: str) -> str:
        # Very conservative: keep alphanum, space, dash, underscore, x, m
        return re.sub(r"[^a-z0-9_\- x]", "", val.lower())

    # Map canonical features to actual ILIKE list
    def feature_predicates(feature: str) -> List[str]:
        if feature in FEATURE_TOKENS:
            variants = FEATURE_TOKENS[feature]
            return [f"description ILIKE '%{_escape(v)}%'" for v in variants]
        # dynamic features like 30m, 60m, 30x etc
        return [f"description ILIKE '%{_escape(feature)}%'"]

    selects: List[str] = []
    families = parsed.families or ["cameras"]  # fallback

    for fam in families:
        where_clauses = ["active = true"]
        where_clauses.append(f"family = '{fam.title()}'")  # Title-case matches CSV (e.g., Cameras)

        # Brand filter uses manufacturer_slug when available
        if parsed.brands:
            brand_list = ",".join([f"'{_escape(b)}'" for b in parsed.brands])
            where_clauses.append(f"manufacturer_slug IN ({brand_list})")

        # Positive features
        for feat in parsed.features:
            preds = feature_predicates(feat)
            # ALL variants must match? choose AND across variant group? We'll use OR inside parentheses
            if len(preds) == 1:
                where_clauses.append(preds[0])
            else:
                where_clauses.append("(" + " OR ".join(preds) + ")")

        # Exclusions
        for excl in parsed.exclude_features:
            where_clauses.append(f"description NOT ILIKE '%{_escape(excl)}%'")

        # Price
        if parsed.price_max is not None:
            where_clauses.append(f"price <= {parsed.price_max}")
        if parsed.currency:
            where_clauses.append(f"currency = '{parsed.currency}'")

        where_sql = " AND ".join(where_clauses)
        select_sql = (
            "SELECT sku, description, price, currency, family, CASE WHEN active THEN 'active' ELSE 'inactive' END AS status "
            f"FROM products WHERE {where_sql} ORDER BY price ASC LIMIT 1"
        )
        selects.append(select_sql)

    if len(selects) == 1:
        return selects[0]

    # Build CTE style similar to LLM examples for consistency
    ctes = []
    out_selects = []
    for idx, stmt in enumerate(selects, start=1):
        cte_name = re.sub(r"[^a-z]", "", families[idx - 1]) or f"f{idx}"
        cte_name = cte_name[:12]
        # strip leading SELECT ... FROM products WHERE
        m = re.search(r"FROM products WHERE (.*) ORDER BY", stmt)
        where_part = m.group(1) if m else "active = true"
        ctes.append(
            f"{cte_name} AS ( SELECT sku, description, price, currency, family, CASE WHEN active THEN 'active' ELSE 'inactive' END AS status FROM products WHERE {where_part} ORDER BY price ASC LIMIT 1 )"
        )
        out_selects.append(f"SELECT * FROM {cte_name}")

    return "WITH " + ", ".join(ctes) + " " + " UNION ALL ".join(out_selects)


__all__ = [
    "ParsedQuery",
    "parse_query",
    "build_sql_from_parsed",
]
