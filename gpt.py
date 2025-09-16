import os
import re
from typing import Optional
try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv(override=True)
except Exception:
    pass

from utils import normalize_sql, validate_sql_safe


SYSTEM_PROMPT = (
    "You are a SQL expert that converts natural language queries into PostgreSQL SELECT statements. "
    "Return exactly ONE statement that only reads from the products table. "
    "Never include INSERT, UPDATE, DELETE, or DDL. CTEs are allowed for multi-family requests. "
    "Schema: products(id UUID, manufacturer_id UUID, sku TEXT, description TEXT, price NUMERIC, currency TEXT, active BOOLEAN, trained BOOLEAN, raw JSONB, created_at TIMESTAMP, updated_at TIMESTAMP, manufacturer_slug TEXT, search_text TEXT, product_number TEXT, family TEXT). "

    "BUSINESS RULES: "
    "(1) Always include WHERE active = true. "
    "(2) For single product type: return 1 cheapest record (ORDER BY price ASC LIMIT 1). "
    "(3) For multiple product types: use CTEs and UNION ALL, return 1 record from each family mentioned. "
    "(4) Family detection: Map user terms to these families generically (multi-family allowed via CTEs): "
    "    - Cameras: camera, cameras, bullet, dome, ptz, outdoor, indoor "
    "    - Recorder accessories: nvr, recorder, dvr, recording, mount "
    "    - Access: access, door, reader "
    "    - Audio and power accessories: audio, microphone, speaker, power accessory "
    "    - Software and licensing: software, license, licensing, vms license "
    "    - Power Supply: power supply, psu, adapter "
    "    - Recordings: recording, storage, hdd, ssd "
    "    - Video Management System: vms, video management "
    "    - Switches: switch, poe switch, 8 port, 16 port, 24 port "
    "    - Alarms: alarm, sensor "
    "    - Controllers: controller, keyboard, joystick. "
    "(5) Apply filters using ILIKE on text fields; wrap nullable fields using COALESCE(field,'') ILIKE ... For example: COALESCE(description,'') ILIKE '%outdoor%'. "
    "(6) IMPORTANT: manufacturer_slug is often NULL/empty. For brand filtering, use COALESCE(description,'') ILIKE '%axis%' (and optionally OR COALESCE(manufacturer_slug,'') ILIKE '%axis%'). Use similar logic for 'hanwha', 'i-pro', 'panasonic'. "
    "(7) Budget constraints: e.g., 'under 900 CAD' → price <= 900 AND currency = 'CAD'. "
    "(8) Exclusions: e.g., 'avoid PTZ' → COALESCE(description,'') NOT ILIKE '%ptz%'. "
    "(9) Always select CASE WHEN active THEN 'active' ELSE 'inactive' END AS status. "
    "(10) QUANTITY HANDLING: When user specifies quantities (e.g., '3x', '4 units', 'two cameras'), include quantity as a literal column: , [NUMBER] AS quantity. "
    "     Extract numbers from patterns like: '3x', '4 units', 'two', 'three', etc. Default quantity is 1 if not specified. "
    "(11) Important: SKU values NEVER contain spaces. Do NOT compare sku to a string with spaces. "
    "     Only use sku equality when the token is a compact code (e.g., '01017-001', 'WV-S2531LTN', 'AGS-H-R-2-60TB-SSD'). "
    "     If the user mentions a product name with spaces (e.g., 'AXIS FA4115 SENSOR UNIT'), match via manufacturer_slug and description ILIKE, not sku. "
    "(12) When targeting a specific family, avoid accessories or unrelated items by adding exclusions based on the family. For example: "
    "     For Cameras: AND COALESCE(description,'') NOT ILIKE '%mount%' AND COALESCE(description,'') NOT ILIKE '%bracket%' AND COALESCE(description,'') NOT ILIKE '%sticker%' AND COALESCE(description,'') NOT ILIKE '%kit%' AND COALESCE(description,'') NOT ILIKE '%cover%'. "
    "     For Recorder accessories: AND COALESCE(description,'') NOT ILIKE '%cable%' AND COALESCE(description,'') NOT ILIKE '%connector%'. "
    "     For other families, apply similar logic to exclude accessories (e.g., for Switches, exclude non-switch items like cables or adapters). "

    "Return only well-formatted PostgreSQL SQL."
    "Note: The examples below are derived from actual products in your database, ensuring the generated SQL matches real data patterns and handles null manufacturer_slug fields correctly."
)


def _build_user_prompt(nl_query: str) -> str:
    """Few-shot prompt guiding the model to our target SQL patterns."""
    examples = [
        (
            'User query: "I need two outdoor cameras"',
            "SELECT sku, description, price, currency, family, CASE WHEN active THEN 'active' ELSE 'inactive' END AS status, 2 AS quantity FROM products WHERE active = true AND family = 'Cameras' AND COALESCE(description,'') ILIKE '%outdoor%' AND COALESCE(description,'') NOT ILIKE '%mount%' AND COALESCE(description,'') NOT ILIKE '%bracket%' AND COALESCE(description,'') NOT ILIKE '%sticker%' AND COALESCE(description,'') NOT ILIKE '%kit%' AND COALESCE(description,'') NOT ILIKE '%cover%' ORDER BY price ASC LIMIT 1;",
        ),
        (
            'User query: "Need 4 outdoor dome cameras with IR 30m and PoE. Add 1 NVR system with 16 channels. Include 1 PoE switch with 24 ports."',
            """WITH cameras AS (
            SELECT 
                'Camera' AS group_name,
                sku, description, price, currency, family, 
                CASE WHEN active THEN 'active' ELSE 'inactive' END AS status,
                4 AS quantity
            FROM products 
            WHERE active = true 
                AND family = 'Cameras' 
                AND COALESCE(description,'') ILIKE '%outdoor%'
                AND COALESCE(description,'') ILIKE '%dome%'
                AND COALESCE(description,'') ILIKE '%poe%'
                AND (
                COALESCE(description,'') ILIKE '%30m%' OR 
                COALESCE(description,'') ILIKE '%30 m%' OR 
                COALESCE(description,'') ILIKE '%30 meters%'
                )
                AND COALESCE(description,'') NOT ILIKE '%mount%'
                AND COALESCE(description,'') NOT ILIKE '%bracket%'
                AND COALESCE(description,'') NOT ILIKE '%sticker%'
                AND COALESCE(description,'') NOT ILIKE '%kit%'
                AND COALESCE(description,'') NOT ILIKE '%cover%'
            ORDER BY price ASC, sku ASC
            LIMIT 1
            ),
            nvr AS (
            SELECT 
                'NVR' AS group_name,
                sku, description, price, currency, family, 
                CASE WHEN active THEN 'active' ELSE 'inactive' END AS status,
                1 AS quantity
            FROM products 
            WHERE active = true 
                AND (family ILIKE '%recorder%' OR family ILIKE '%nvr%')
                AND COALESCE(description,'') ILIKE '%16 channel%'
            ORDER BY price ASC, sku ASC
            LIMIT 1
            ),
            switch AS (
            SELECT 
                'PoE Switch' AS group_name,
                sku, description, price, currency, family, 
                CASE WHEN active THEN 'active' ELSE 'inactive' END AS status,
                1 AS quantity
            FROM products 
            WHERE active = true 
                AND (family ILIKE '%recorder%' OR family ILIKE '%switch%' OR family ILIKE '%network%')
                AND COALESCE(description,'') ILIKE '%poe%' 
                AND (
                COALESCE(description,'') ILIKE '%24 port%' OR 
                COALESCE(description,'') ILIKE '%24-port%'
                )
            ORDER BY price ASC, sku ASC
            LIMIT 1
            )
            SELECT * FROM cameras
            UNION ALL
            SELECT * FROM nvr
            UNION ALL
            SELECT * FROM switch;""",
        ),
        (
            'User query: "2MP outdoor bullet camera with motorized zoom"',
            "SELECT sku, description, price, currency, family, CASE WHEN active THEN 'active' ELSE 'inactive' END AS status, 1 AS quantity FROM products WHERE active = true AND family = 'Cameras' AND COALESCE(description,'') ILIKE '%outdoor%' AND COALESCE(description,'') ILIKE '%bullet%' AND COALESCE(description,'') ILIKE '%2mp%' AND COALESCE(description,'') ILIKE '%motorized%' AND COALESCE(description,'') NOT ILIKE '%mount%' AND COALESCE(description,'') NOT ILIKE '%bracket%' AND COALESCE(description,'') NOT ILIKE '%sticker%' AND COALESCE(description,'') NOT ILIKE '%kit%' AND COALESCE(description,'') NOT ILIKE '%cover%' ORDER BY price ASC LIMIT 1;",
        ),
        (
            'User query: "Indoor pendant kit for AXIS M3006"',
            "SELECT sku, description, price, currency, family, CASE WHEN active THEN 'active' ELSE 'inactive' END AS status, 1 AS quantity FROM products WHERE active = true AND family = 'Recorder accessories' AND COALESCE(description,'') ILIKE '%indoor%' AND COALESCE(description,'') ILIKE '%pendant%' AND COALESCE(description,'') ILIKE '%axis%' AND COALESCE(description,'') ILIKE '%m3006%' AND COALESCE(description,'') NOT ILIKE '%cable%' AND COALESCE(description,'') NOT ILIKE '%connector%' ORDER BY price ASC LIMIT 1;",
        ),
        (
            'User query: "3 year EPIC WebRTC license for camera"',
            "SELECT sku, description, price, currency, family, CASE WHEN active THEN 'active' ELSE 'inactive' END AS status, 1 AS quantity FROM products WHERE active = true AND family = 'Software and licensing' AND COALESCE(description,'') ILIKE '%webrtc%' AND COALESCE(description,'') ILIKE '%license%' AND COALESCE(description,'') ILIKE '%3 year%' ORDER BY price ASC LIMIT 1;",
        ),
    ]

    shots = []
    for q, sql in examples:
        shots.append(f"{q}\nSQL:\n{sql}")
    return "\n\n".join(shots) + f"\n\nUser query: \"{nl_query}\"\nSQL:"


def _extract_skus_and_eans(nl_query: str) -> tuple[list[str], list[str]]:
    """Extract probable SKUs and EAN/UPC-like numbers from the user's text.

    - SKUs: tokens with at least one hyphen or slash and a mix of letters/digits (e.g., 01017-001, WV-X15300-V3L, AGS-H-R-2-60TB-SSD)
    - EAN/UPC: 12-14 continuous digits
    """
    if not nl_query:
        return [], []
    text = nl_query.upper()

    # Extract SKUs (allow A-Z, 0-9, and -_/)
    sku_candidates = re.findall(r"\b[A-Z0-9]{2,}[A-Z0-9\-/]{1,}[A-Z0-9]{1,}\b", text)
    skus: list[str] = []
    for tok in sku_candidates:
        # Heuristics: must include a hyphen or slash and at least one digit
        if ("-" in tok or "/" in tok) and re.search(r"\d", tok):
            # Avoid matching plain numbers with a trailing hyphen pattern
            skus.append(tok)

    # Extract potential EAN/UPC numbers (12-14 digits)
    eans = re.findall(r"\b\d{12,14}\b", nl_query)

    # Deduplicate while preserving order
    def _dedup(seq: list[str]) -> list[str]:
        seen: set[str] = set()
        out: list[str] = []
        for s in seq:
            if s not in seen:
                seen.add(s)
                out.append(s)
        return out

    return _dedup(skus), _dedup(eans)


def _build_smart_sku_sql(skus: list[str], eans: list[str], limit_cap: int) -> str:
    """Enhanced SKU matching: exact SKU first, then search in description if not found."""
    tokens = [re.sub(r"[^a-z0-9\-/]", "", s.lower()) for s in skus if s]
    tokens = [t for t in tokens if t]
    eans_sanitized = [re.sub(r"[^0-9]", "", e) for e in eans if e]

    parts: list[str] = []

    if tokens:
        # Exact SKU matches first
        token_list = ",".join([f"'{t}'" for t in tokens])
        exact = (
            "SELECT sku, description, price, currency, family, CASE WHEN active THEN 'active' ELSE 'inactive' END AS status, 1 AS quantity, 0 AS rnk "
            "FROM products WHERE active = true AND lower(sku) IN (" + token_list + ")"
        )
        parts.append(exact)

        # If SKU not found, search in description (key enhancement per user request)
        desc_matches = []
        for t in tokens:
            desc_matches.append(f"COALESCE(description,'') ILIKE '%{t}%'")
        if desc_matches:
            desc_sql = (
                "SELECT sku, description, price, currency, family, CASE WHEN active THEN 'active' ELSE 'inactive' END AS status, 1 AS quantity, 1 AS rnk "
                "FROM products WHERE active = true AND (" + " OR ".join(desc_matches) + ") "
                "AND lower(sku) NOT IN (" + token_list + ")"
            )
            parts.append(desc_sql)

    # EAN search in description
    if eans_sanitized:
        ean_matches = [f"COALESCE(description,'') ILIKE '%{e}%'" for e in eans_sanitized]
        parts.append(
            "SELECT sku, description, price, currency, family, CASE WHEN active THEN 'active' ELSE 'inactive' END AS status, 1 AS quantity, 2 AS rnk "
            "FROM products WHERE active = true AND (" + " OR ".join(ean_matches) + ")"
        )

    if not parts:
        return "SELECT sku, description, price, currency, family, CASE WHEN active THEN 'active' ELSE 'inactive' END AS status, 1 AS quantity FROM products WHERE 1=0 LIMIT 10"

    union_sql = " UNION ALL ".join(parts)
    return union_sql + " ORDER BY rnk ASC, price ASC LIMIT " + str(max(1, limit_cap))


def _rule_based_sql(nl_query: str) -> Optional[str]:
    """Very simple deterministic fallback for brand/family queries when no LLM and no SKU/EAN.

    Heuristics covered:
    - family detection: cameras
    - brand detection: axis, hanwha, i-pro/panasonic
    - basic attributes: outdoor, indoor, dome, bullet, ptz, poe, ir, distances (e.g., 30m, 60m)
    - exclusions: phrases like 'no ptz', 'without ptz'
    - budget: 'under 900', 'max 1200'
    - quantity: extract first occurrence; default 1
    """
    if not nl_query:
        return None
    text = nl_query.lower()

    # Quantity
    qty = 1
    # patterns like '3x', '3 x', 'x3', '3 units'
    m = re.search(r"(?:^|\s)(\d+)\s*(?:x|units?|pcs?|pieces?)\b|\bx\s*(\d+)\b", text)
    if m:
        qty = int((m.group(1) or m.group(2) or "1").strip())
    else:
        # number words
        words = {
            "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
            "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
        }
        for w, v in words.items():
            if re.search(rf"\b{w}\b", text):
                qty = v
                break

    # Family detection (generic)
    family_synonyms: dict[str, list[str]] = {
        "Cameras": ["camera", "cameras", "bullet", "dome", "ptz", "outdoor", "indoor"],
        "Recorder accessories": ["nvr", "recorder", "dvr", "recordings?", "mount"],
        "Access": ["access", "door", "reader"],
        "Audio and power accessories": ["audio", "microphone", "speaker", "power accessory"],
        "Software and licensing": ["software", "license", "licensing", "vms license"],
        "Power Supply": ["power supply", "psu", "adapter"],
        "Recordings": ["recording", "storage", "hdd", "ssd"],
        "Video Management System": ["vms", "video management"],
        "Switches": ["switch", "poe switch", "8 port", "16 port", "24 port"],
        "Alarms": ["alarm", "sensor"],
        "Controllers": ["controller", "keyboard", "joystick"],
    }
    requested_families: list[str] = []
    for fam, syns in family_synonyms.items():
        for s in syns:
            if re.search(rf"\b{s}\b", text):
                requested_families.append(fam)
                break
    # de-dup
    requested_families = list(dict.fromkeys(requested_families))

    # Brand
    brand_clauses: list[str] = []
    if "axis" in text:
        brand_clauses.append("(COALESCE(description,'') ILIKE '%axis%' OR COALESCE(manufacturer_slug,'') ILIKE '%axis%')")
    if "hanwha" in text:
        brand_clauses.append("(COALESCE(description,'') ILIKE '%hanwha%' OR COALESCE(manufacturer_slug,'') ILIKE '%hanwha%')")
    if "i-pro" in text or "ipro" in text or "i pro" in text or "panasonic" in text:
        brand_clauses.append("(COALESCE(description,'') ILIKE '%i-pro%' OR COALESCE(description,'') ILIKE '%panasonic%' OR COALESCE(manufacturer_slug,'') ILIKE '%i-pro%' OR COALESCE(manufacturer_slug,'') ILIKE '%panasonic%')")

    # Attributes
    attrs: list[str] = []
    for token in ["outdoor", "indoor", "dome", "bullet", "poe", "ir"]:
        if token in text:
            attrs.append(f"COALESCE(description,'') ILIKE '%{token}%'")
    # Distance like 30m / 60m
    dist = re.findall(r"\b(\d{2,3})\s*m\b", text)
    for d in dist:
        attrs.append(f"COALESCE(description,'') ILIKE '%{d}m%'")

    # Exclusions
    excludes: list[str] = []
    if re.search(r"no\s+ptz|without\s+ptz|avoid\s+ptz", text):
        excludes.append("COALESCE(description,'') NOT ILIKE '%ptz%'")

    # Family exclusions (generic per family)
    family_exclusions: dict[str, list[str]] = {
        "Cameras": ["mount", "bracket", "sticker", "kit", "cover"],
        "Recorder accessories": ["cable", "connector"],
        "Access": ["cable", "adapter"],
        "Audio and power accessories": ["cable", "connector"],
        "Software and licensing": [],  # No exclusions
        "Power Supply": ["cable", "adapter"],
        "Recordings": ["cable", "connector"],
        "Video Management System": [],  # No exclusions
        "Switches": ["cable", "adapter"],
        "Alarms": ["cable", "connector"],
        "Controllers": ["cable", "adapter"],
    }

    # Apply exclusions based on requested families
    for fam in requested_families:
        if fam in family_exclusions:
            for excl in family_exclusions[fam]:
                excludes.append(f"COALESCE(description,'') NOT ILIKE '%{excl}%'")

    # Budget
    price_clause = None
    m = re.search(r"\b(under|max|at most|up to|<=|less than)\s*\$?\s*(\d+(?:\.\d+)?)", text)
    if m:
        price_val = m.group(2)
        price_clause = f"price <= {price_val}"

    # Nothing to do
    if not (requested_families or brand_clauses or attrs or price_clause or excludes):
        return None

    # If no family matched, build a generic single SELECT
    if not requested_families:
        where_parts = ["active = true"]
        if brand_clauses:
            where_parts.append("(" + " OR ".join(brand_clauses) + ")")
        if attrs:
            where_parts.extend(attrs)
        if excludes:
            where_parts.extend(excludes)
        if price_clause:
            where_parts.append(price_clause)
        where_sql = " AND ".join(where_parts)
        sql = (
            "SELECT sku, description, price, currency, family, "
            "CASE WHEN active THEN 'active' ELSE 'inactive' END AS status, "
            f"{qty} AS quantity "
            f"FROM products WHERE {where_sql} ORDER BY price ASC LIMIT 1"
        )
        err = validate_sql_safe(sql)
        if err:
            return None
        return normalize_sql(sql)

    # Quantity per family from phrases like "2 cameras", "1 switch", etc.
    per_family_qty: dict[str, int] = {}
    for fam, syns in family_synonyms.items():
        for s in syns:
            m = re.search(rf"(\d+)\s+{s}\b", text)
            if m:
                per_family_qty[fam] = int(m.group(1))
                break
    # default to overall qty if none per family
    for fam in requested_families:
        if fam not in per_family_qty:
            per_family_qty[fam] = qty

    # Build CTEs
    ctes: list[str] = []
    union_parts: list[str] = []
    for idx, fam in enumerate(requested_families, start=1):
        cte_name = f"item{idx}"
        where_parts = ["active = true", f"family = '{fam}'"]
        if brand_clauses:
            where_parts.append("(" + " OR ".join(brand_clauses) + ")")
        if attrs:
            where_parts.extend(attrs)
        fam_excludes = list(excludes)
        if fam in family_exclusions:
            for excl in family_exclusions[fam]:
                fam_excludes.append(f"COALESCE(description,'') NOT ILIKE '%{excl}%'")
        if fam_excludes:
            where_parts.extend(fam_excludes)
        if price_clause:
            where_parts.append(price_clause)
        where_sql = " AND ".join(where_parts)
        cte_sql = (
            f"{cte_name} AS (\n"
            "SELECT sku, description, price, currency, family, CASE WHEN active THEN 'active' ELSE 'inactive' END AS status, "
            f"{per_family_qty[fam]} AS quantity\n"
            f"FROM products WHERE {where_sql} ORDER BY price ASC LIMIT 1\n)"
        )
        ctes.append(cte_sql)
        union_parts.append(f"SELECT * FROM {cte_name}")

    full_sql = "WITH " + ",\n".join(ctes) + "\n" + "\nUNION ALL\n".join(union_parts)
    err = validate_sql_safe(full_sql)
    if err:
        return None
    return normalize_sql(full_sql)


def generate_sql_from_nl(nl_query: str) -> Optional[str]:
    """Translate NL to safe SELECT SQL.
    Strategy: LLM first → Enhanced SKU/EAN fallback → return None if all fail.
    """

    # 1) LLM-first (if key available)
    api_key = os.getenv("OPENAI_API_KEY")
    client = None
    if api_key:
        try:
            from openai import OpenAI  # type: ignore
            client = OpenAI(api_key=api_key)
        except Exception:
            client = None
    if client:
        model_name = os.getenv("OPENAI_MODEL", "gpt-4o")
        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": _build_user_prompt(nl_query)},
                ],
                temperature=0,
                max_tokens=1000,
            )
        except Exception:
            # Fallback to a smaller model
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": _build_user_prompt(nl_query)},
                ],
                temperature=0,
                max_tokens=1000,
            )
        text = response.choices[0].message.content if response.choices else None
        if text:
            cleaned = text.strip()
            if cleaned.lower().startswith("sql:"):
                cleaned = cleaned[4:].strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.strip("`")
                lines = [line for line in cleaned.splitlines() if line.strip()]
                if lines and lines[0].strip().lower() == "sql":
                    lines = lines[1:]
                cleaned = "\n".join(lines)

            sql = normalize_sql(cleaned.strip())
            if not validate_sql_safe(sql):
                return sql

    # 2) Enhanced SKU/EAN fallback with description search
    skus, eans = _extract_skus_and_eans(nl_query)
    if skus or eans:
        sql = _build_smart_sku_sql(skus, eans, limit_cap=10)
        sql = normalize_sql(sql)
        if not validate_sql_safe(sql):
            return sql

    # 3) Deterministic brand/family fallback
    rule_sql = _rule_based_sql(nl_query)
    if rule_sql and not validate_sql_safe(rule_sql):
        return rule_sql

    # Nothing worked
    return None


