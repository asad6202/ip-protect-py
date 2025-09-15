import os
import re
from typing import Optional
from dotenv import load_dotenv

from openai import OpenAI

from utils import normalize_sql, validate_sql_safe
from nl_parser import parse_query, build_sql_from_parsed


# Ensure .env values override any pre-existing env vars set in the shell/conda env
load_dotenv(override=True)


SYSTEM_PROMPT = (
    "You are a SQL expert that converts natural language queries into PostgreSQL SELECT statements. "
    "Return exactly ONE statement that only reads from the products table. "
    "Never include INSERT, UPDATE, DELETE, or DDL. CTEs are allowed for multi-family requests. "
    "Schema: products(id UUID, manufacturer_id UUID, sku TEXT, description TEXT, price NUMERIC, currency TEXT, active BOOLEAN, trained BOOLEAN, raw JSONB, created_at TIMESTAMP, updated_at TIMESTAMP, manufacturer_slug TEXT, search_text TEXT, product_number TEXT, family TEXT). "
    
    "BUSINESS RULES: "
    "(1) Always include WHERE active = true. "
    "(2) For single product type: return 1 cheapest record (LIMIT 1, ORDER BY price ASC). "
    "(3) For multiple product types: use CTE with UNION ALL, return 1 record from each family mentioned. "
    "(4) Map terms to families: 'camera(s)' → family = 'Cameras', 'nvr/recorder' → family = 'NVR', 'switch' → family = 'Switch'. "
    "(5) Apply filters using ILIKE on description: 'outdoor'/'indoor'/'bullet'/'dome'/'ptz'/'poe'/'ir 30m' etc. "
    "(6) Brand preferences: 'axis', 'hanwha', 'wisenet', 'i-pro', 'panasonic' via description ILIKE. "
    "(7) Budget constraints: 'under 900 CAD' → price <= 900 AND currency = 'CAD'. "
    "(8) Exclusions: 'avoid PTZ' → description NOT ILIKE '%ptz%'. "
    "(9) Always select CASE WHEN active THEN 'active' ELSE 'inactive' END AS status. "
    
    "Return only well-formatted SQL queries. Ensure queries are PostgreSQL-compliant. "
)


def _build_user_prompt(nl_query: str) -> str:
    """Few-shot prompt guiding the model to our target SQL patterns."""
    examples = [
        (
            'User query: "I need two outdoor cameras"',
            "SELECT sku, description, price, currency, family, CASE WHEN active THEN 'active' ELSE 'inactive' END AS status FROM products WHERE active = true AND family = 'Cameras' AND description ILIKE '%outdoor%' ORDER BY price ASC LIMIT 1;",
        ),
        (
            'User query: "Need 4 outdoor dome cameras with IR 30m and PoE. Add 1 NVR system with 16 channels. Include 1 PoE switch with 24 ports."',
            """WITH cameras AS (
            SELECT sku, description, price, currency, family, CASE WHEN active THEN 'active' ELSE 'inactive' END AS status
            FROM products WHERE active = true AND family = 'Cameras' 
            AND description ILIKE '%outdoor%' AND description ILIKE '%dome%' AND description ILIKE '%poe%' 
            AND description ILIKE '%ir%' AND description ILIKE '%30m%' ORDER BY price ASC LIMIT 1
            ), nvr AS (
            SELECT sku, description, price, currency, family, CASE WHEN active THEN 'active' ELSE 'inactive' END AS status
            FROM products WHERE active = true AND family = 'NVR' 
            AND description ILIKE '%16 channel%' ORDER BY price ASC LIMIT 1
            ), switch AS (
            SELECT sku, description, price, currency, family, CASE WHEN active THEN 'active' ELSE 'inactive' END AS status
            FROM products WHERE active = true AND family = 'Switch' 
            AND description ILIKE '%poe%' AND description ILIKE '%24 port%' ORDER BY price ASC LIMIT 1
            )
            SELECT * FROM cameras UNION ALL SELECT * FROM nvr UNION ALL SELECT * FROM switch;""",
        ),
        (
            'User query: "5 outdoor dome cameras with IR 60m, PoE. Prefer Axis, no PTZ. Max $900 each."',
            "SELECT sku, description, price, currency, family, CASE WHEN active THEN 'active' ELSE 'inactive' END AS status FROM products WHERE active = true AND family = 'Cameras' AND description ILIKE '%outdoor%' AND description ILIKE '%dome%' AND description ILIKE '%poe%' AND description ILIKE '%ir%' AND description ILIKE '%60m%' AND description ILIKE '%axis%' AND description NOT ILIKE '%ptz%' AND price <= 900 ORDER BY price ASC LIMIT 1;",
        ),
        (
            'User query: "3x 01001-001 and 2x 01017-001"',
            "SELECT sku, description, price, currency, family, CASE WHEN active THEN 'active' ELSE 'inactive' END AS status FROM products WHERE sku IN ('01001-001','01017-001') ORDER BY price ASC LIMIT 10;",
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


def _sanitize_like_literal(value: str) -> str:
    """Very conservative LIKE literal sanitizer: keep only [a-z0-9-/]."""
    value = value.lower()
    return re.sub(r"[^a-z0-9\-/]", "", value)


def _build_sku_ean_sql(skus: list[str], eans: list[str], limit_cap: int) -> str:
    """Construct a single SQL statement that returns exact SKU matches first,
    then fuzzy SKU/EAN matches, ordered by closeness then price.

    This uses only the `products` table and stays within read-only constraints.
    """
    tokens = [_sanitize_like_literal(s) for s in skus if s]
    tokens = [t for t in tokens if t]
    eans_sanitized = [re.sub(r"[^0-9]", "", e) for e in eans if e]

    parts: list[str] = []

    if tokens:
        # Exact matches via case-insensitive equality
        token_list = ",".join([f"'{t}'" for t in tokens])
        exact = (
            "SELECT NULL::text AS group_name, sku, description, price, currency, family, CASE WHEN active THEN 'active' ELSE 'inactive' END AS status, 0 AS rnk "
            "FROM products "
            "WHERE active = true AND lower(sku) IN (" + token_list + ")"
        )
        parts.append(exact)

        # Fuzzy matches, excluding exact ones
        fuzzy_ors: list[str] = []
        for t in tokens:
            no_dash = t.replace("-", "")
            fuzzy_ors.extend([
                f"lower(sku) LIKE '{t}%'",
                f"lower(sku) LIKE '%{t}%'",
                f"replace(lower(sku),'-','') LIKE '{no_dash}%'",
                f"replace(lower(sku),'-','') LIKE '%{no_dash}%'",
                f"description ILIKE '%{t}%'",
            ])
        if eans_sanitized:
            for e in eans_sanitized:
                fuzzy_ors.append(f"description ILIKE '%{e}%'")

        fuzzy_where = " OR ".join(fuzzy_ors) if fuzzy_ors else "FALSE"
        fuzzy = (
            "SELECT NULL::text AS group_name, sku, description, price, currency, family, CASE WHEN active THEN 'active' ELSE 'inactive' END AS status, "
            "   CASE\n"
            + "\n".join(
                [
                    # Lower rank values indicate closer match
                    "       WHEN lower(sku) = '" + t + "' THEN 1",
                    "       WHEN lower(sku) LIKE '" + t + "%' THEN 2",
                    "       WHEN replace(lower(sku),'-','') LIKE '" + t.replace("-", "") + "%' THEN 2",
                    "       WHEN lower(sku) LIKE '%" + t + "%' THEN 3",
                    "       WHEN replace(lower(sku),'-','') LIKE '%" + t.replace("-", "") + "%' THEN 3",
                ]
            )
            + ("       ELSE 4 END AS rnk " if tokens else "       4 AS rnk ")
            + "FROM products "
            + "WHERE active = true AND (" + fuzzy_where + ") "
            + "AND lower(sku) NOT IN (" + token_list + ")"
        )
        parts.append(fuzzy)
    else:
        # Only EANs provided – search in description
        if eans_sanitized:
            like_ors = " OR ".join([f"description ILIKE '%{e}%'" for e in eans_sanitized])
            parts.append(
                "SELECT NULL::text AS group_name, sku, description, price, currency, family, CASE WHEN active THEN 'active' ELSE 'inactive' END AS status, 0 AS rnk "
                "FROM products WHERE active = true AND (" + like_ors + ")"
            )

    if not parts:
        # Should not happen, but return a safe minimal query
        return "SELECT NULL::text AS group_name, sku, description, price, currency, family, CASE WHEN active THEN 'active' ELSE 'inactive' END AS status FROM products WHERE 1=0 LIMIT 10"

    union_sql = " UNION ALL ".join(parts)
    final_sql = union_sql + " ORDER BY rnk ASC, price ASC LIMIT " + str(max(1, limit_cap))
    return final_sql




def generate_sql_from_nl(nl_query: str) -> Optional[str]:
    """Use GPT-4o to translate NL to safe SELECT SQL. Returns None if failed."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not set")

    client = OpenAI(api_key=api_key)

    # Fast-path: exact identifiers (SKUs / EAN like) in the query
    skus, eans = _extract_skus_and_eans(nl_query)
    if skus or eans:
        sql = _build_sku_ean_sql(skus, eans, limit_cap=10)
        sql = normalize_sql(sql)
        error = validate_sql_safe(sql)
        if error:
            return None
        return sql

    # Rule-based parsing pass (deterministic filters)
    try:
        parsed = parse_query(nl_query)
        if parsed and parsed.used_rule_based:
            rule_sql = build_sql_from_parsed(parsed)
            if rule_sql:
                rule_sql = normalize_sql(rule_sql)
                err = validate_sql_safe(rule_sql)
                if not err:
                    return rule_sql
    except Exception:
        # Fail silently and continue to LLM fallback
        pass

    # Use GPT-4o to generate SQL directly
    response = client.chat.completions.create(
        model="gpt-4o",
        # model="gpt-5",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": _build_user_prompt(nl_query)},
        ],
        temperature=0,
        max_tokens=1000,
        # max_completion_tokens=1000,
    )

    text = response.choices[0].message.content if response.choices else None
    if not text:
        return None

    # Extract SQL: remove code fences and labels
    cleaned = text.strip()
    if cleaned.lower().startswith("sql:"):
        cleaned = cleaned[4:].strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        lines = [line for line in cleaned.splitlines() if line.strip()]
        if lines and lines[0].strip().lower() == "sql":
            lines = lines[1:]
        cleaned = "\n".join(lines)

    sql = cleaned.strip()
    
    # Basic validation and normalization
    sql = normalize_sql(sql)
    error = validate_sql_safe(sql)
    if error:
        return None
    return sql


