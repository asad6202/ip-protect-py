"""
Deterministic product retrieval for quote generation (DB-agnostic fuzzy search).

- Family-aware: requires at least one family keyword (camera/nvr/switch) to appear
  and bans obvious accessories per family to avoid wrong matches (e.g., chargers).
- Token variant expansion: "ir-30m" ~ "infrared 30 m"; "poe+" ~ "802.3at".
- Scoring + minimum token hits: reduces random low-relevance rows.
- Partial success: returns items found and `unfulfilled` for misses (no 404 here).
- No pgvector required; uses SQL LIKE/ILIKE. Add pg_trgm index for speed.

Usage:
  from app.services.retrieval import assemble_quote

  data = assemble_quote(db, extracted_intent)
  # returns: {"items": [...], "unfulfilled": [...], "total": float, "currency": str}

Assumptions:
- Table: products(sku, description, price, currency, family, status)
- `db` is a SQLAlchemy session
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy import text

# -------------------------- Tunables / Business Rules -------------------------

# Map various family hints to normalized families used for filtering
FAMILY_MAP = {
    "camera": ["camera", "cameras", "dome", "bullet", "ptz", "turret", "sensor unit"],
    "nvr":    ["nvr", "recorder", "network video recorder"],
    "switch": ["switch", "poe switch", "poe+ switch"],
    # add families if you want to expand later:
    # "mount":  ["mount", "bracket"],
    # "storage":["storage", "hdd", "ssd"],
}

# Words that MUST appear (any one of them) for that family to avoid mismatches
FAMILY_MUST = {
    "camera": ["camera", "dome", "bullet", "ptz", "turret"],
    "nvr":    ["nvr", "recorder"],
    "switch": ["switch"],
}

# Words that SHOULD NOT appear for that family (ban obvious accessories)
FAMILY_BAN = {
    "camera": ["adapter", "charger", "license", "software", "relay", "tamper", "battery", "power supply"],
    "nvr":    ["adapter", "charger", "license", "software", "tamper", "battery"],
    "switch": ["adapter", "charger", "license", "software", "battery", "mount", "bracket"],
}

# Feature/token variants to catch catalog wording differences
TOKEN_VARIANTS = {
    "poe":     ["poe", "poe+"],
    "poe+":    ["poe+", "802.3at"],
    "ir-30m":  ["ir 30m", "ir-30m", "infrared 30m", "infrared 30 m", "exir 30m"],
    "ir-60m":  ["ir 60m", "ir-60m", "infrared 60m", "infrared 60 m", "exir 60m"],
    "outdoor": ["outdoor", "ip66", "ip67", "weatherproof"],
    "indoor":  ["indoor"],
    "vandal":  ["vandal", "ik10"],
    "audio":   ["audio", "microphone"],
    "4k":      ["4k", "uhd"],
    "1080p":   ["1080p", "full hd", "fhd"],
    "dome":    ["dome"],
    "bullet":  ["bullet"],
    "ptz":     ["ptz"],
    "turret":  ["turret"],
}

# Scoring weights and thresholds
WEIGHTS = {
    "token_hit": 3.0,
    "family_hit": 2.0,
    "ban_penalty": -5.0,
    "brand_pref": 2.0,
    "brand_avoid": -2.0,
    "budget_fit": 1.0,
    "over_budget_penalty": -1e9,  # treat as hard cap if a strict budget is provided
}
MIN_TOKEN_HITS = 1  # require at least this many expanded-token hits to accept a candidate

# Hard budget cap? Set to True to exclude rows over budget, else they get large negative score
HARD_BUDGET_CAP = True

# ---------------------------- Helper functions --------------------------------

def _normalize_family(raw_family: Optional[str], want: Dict[str, Any]) -> Optional[str]:
    rf = (raw_family or "").lower()
    if rf:
        for fam, hints in FAMILY_MAP.items():
            if rf == fam or any(h in rf for h in hints):
                return fam
    # try infer from formFactor/location words
    probe = f"{(want.get('formFactor') or '').lower()} {(want.get('location') or '').lower()}".strip()
    for fam, hints in FAMILY_MAP.items():
        if any(h in probe for h in hints):
            return fam
    return None

def _expand_variants(tokens: List[str]) -> List[str]:
    out: List[str] = []
    for t in tokens:
        out.extend(TOKEN_VARIANTS.get(t.lower(), [t.lower()]))
    # unique preserve order
    seen, uniq = set(), []
    for v in out:
        if v not in seen:
            seen.add(v)
            uniq.append(v)
    return uniq

def _collect_tokens(want: Dict[str, Any]) -> List[str]:
    tokens: List[str] = []
    ff = (want.get("formFactor") or "").lower()
    loc = (want.get("location") or "").lower()
    if ff and ff != "any": tokens.append(ff)
    if loc and loc != "any": tokens.append(loc)
    for f in want.get("features") or []:
        if isinstance(f, str) and f.strip():
            tokens.append(f.strip().lower())
    return tokens

def _brand_lists(want: Dict[str, Any]) -> Tuple[List[str], List[str]]:
    pref = [b.lower() for b in (want.get("brandPreference") or []) if b]
    avoid = [b.lower() for b in (want.get("brandAvoid") or []) if b]
    return pref, avoid

# ----------------------------- Core retrieval ---------------------------------

def deterministic_search(db, want: Dict[str, Any], limit: int = 200) -> List[Dict[str, Any]]:
    """
    Fuzzy SQL search using LIKE with variant expansion, family must/ban words, budget filter,
    and re-scoring; returns up to `limit` rows (sorted by score descending).
    """
    raw_family = want.get("family")
    fam = _normalize_family(raw_family, want)

    tokens = _collect_tokens(want)
    variants = _expand_variants(tokens)

    must_any = FAMILY_MUST.get(fam or "", [])  # at least one must appear
    bans = FAMILY_BAN.get(fam or "", [])

    where: List[str] = ["status='active'"]
    params: Dict[str, Any] = {}

    # 'must' clause: at least one family indicator in description
    if must_any:
        must_sql = []
        for i, m in enumerate(must_any):
            k = f"m{i}"; params[k] = f"%{m}%"
            must_sql.append(f"LOWER(description) LIKE :{k}")
        where.append("(" + " OR ".join(must_sql) + ")")

    # 'ban' clause: exclude obvious accessories for that family
    for j, b in enumerate(bans):
        k = f"b{j}"; params[k] = f"%{b}%"
        where.append(f"LOWER(description) NOT LIKE :{k}")

    # Budget
    budget = want.get("budgetPerUnit") or {}
    if "amount" in budget and budget["amount"] is not None:
        params["maxp"] = float(budget["amount"])
        if HARD_BUDGET_CAP:
            where.append("price <= :maxp")  # hard filter
        # else: we don't filter; we penalize later in scoring

    # Soft token OR group
    like_or = []
    for i, v in enumerate(variants):
        k = f"v{i}"; params[k] = f"%{v}%"
        like_or.append(f"LOWER(description) LIKE :{k}")

    sql = f"""
      SELECT sku, description, price, currency, family, status
      FROM products
      WHERE {' AND '.join(where)}
      {" AND (" + " OR ".join(like_or) + ")" if like_or else ""}
      LIMIT {int(limit)}
    """

    rows = db.execute(text(sql), params).mappings().all()

    # Score and prune weak matches
    pref, avoid = _brand_lists(want)
    def score(row: Dict[str, Any]) -> float:
        d = (row.get("description") or "").lower()
        price = float(row.get("price") or 0)

        hits = sum(1 for v in variants if v in d)
        fam_hit = 1 if (not must_any or any(m in d for m in must_any)) else 0
        ban_hits = sum(1 for b in bans if b in d)
        s = 0.0
        s += WEIGHTS["token_hit"] * hits
        s += WEIGHTS["family_hit"] * fam_hit
        s += WEIGHTS["ban_penalty"] * ban_hits
        s += WEIGHTS["brand_pref"] * sum(1 for b in pref if b in d)
        s += WEIGHTS["brand_avoid"] * sum(1 for b in avoid if b in d)

        if "amount" in budget and budget["amount"] is not None:
            maxp = float(budget["amount"])
            if price <= maxp:
                s += WEIGHTS["budget_fit"]
            elif not HARD_BUDGET_CAP:
                s += WEIGHTS["over_budget_penalty"]  # huge negative
        return s

    # Sort by score
    scored = sorted(rows, key=score, reverse=True)

    # Enforce minimum hits and family match
    filtered: List[Dict[str, Any]] = []
    for r in scored:
        d = (r.get("description") or "").lower()
        hits = sum(1 for v in variants if v in d)
        fam_ok = (not must_any) or any(m in d for m in must_any)
        if hits >= MIN_TOKEN_HITS and fam_ok:
            filtered.append(r)

    # Fallback: if nothing meets threshold but we have rows, return top few anyway
    return filtered[:10] if filtered else scored[:5]

# ----------------------------- Quote assembly ---------------------------------

def _to_quote_item(row: Dict[str, Any], qty: int) -> Dict[str, Any]:
    unit = float(row["price"])
    subtotal = round(unit * qty, 2)
    return {
        "sku": row["sku"],
        "description": row["description"],
        "quantity": qty,
        "unit_price": unit,
        "currency": row["currency"],
        "subtotal": subtotal,
    }

def _ensure_accessories(db, selected: List[Dict[str, Any]], g: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Add NVR or Switch if globally requested but not present in selected items.
    Heuristic: choose cheapest matching family and simple LIKE on channels/ports.
    """
    out = list(selected)
    descs = " || ".join([(i.get("description") or "").lower() for i in out])

    # NVR
    if g.get("nvrChannels") and "nvr" not in descs and "recorder" not in descs:
        chan = int(g["nvrChannels"])
        row = db.execute(text("""
            SELECT * FROM products
            WHERE status='active' AND LOWER(description) LIKE '%nvr%' AND LOWER(description) LIKE :ch
            ORDER BY price ASC
            LIMIT 1
        """), {"ch": f"%{chan} channel%"}).mappings().first()
        if not row:
            row = db.execute(text("""
                SELECT * FROM products
                WHERE status='active' AND (LOWER(description) LIKE '%nvr%' OR LOWER(description) LIKE '%recorder%')
                ORDER BY price ASC
                LIMIT 1
            """)).mappings().first()
        if row:
            out.append(_to_quote_item(row, 1))

    # Switch
    if g.get("switchPorts") and "switch" not in descs:
        ports = int(g["switchPorts"])
        row = db.execute(text("""
            SELECT * FROM products
            WHERE status='active' AND LOWER(description) LIKE '%switch%' AND LOWER(description) LIKE :p
            ORDER BY price ASC
            LIMIT 1
        """), {"p": f"%{ports} port%"}).mappings().first()
        if not row:
            row = db.execute(text("""
                SELECT * FROM products
                WHERE status='active' AND LOWER(description) LIKE '%switch%'
                ORDER BY price ASC
                LIMIT 1
            """)).mappings().first()
        if row:
            out.append(_to_quote_item(row, 1))

    return out

def assemble_quote(db, extracted: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build a quote from an extracted intent.
    - Tries deterministic_search for each requested item
    - Allows partial success; collects unfulfilled requests
    - Adds NVR/Switch from global hints if missing
    """
    items_req = extracted.get("items") or []
    global_req = extracted.get("global") or {}

    results: List[Dict[str, Any]] = []
    unfulfilled: List[Dict[str, Any]] = []

    for want in items_req:
        qty = max(1, int(want.get("quantity") or 1))

        # If explicit SKU, try exact match first
        sku = (want.get("sku") or "").strip()
        if sku:
            row = db.execute(text("""
                SELECT sku, description, price, currency, family, status
                FROM products
                WHERE status='active' AND sku=:sku
                LIMIT 1
            """), {"sku": sku}).mappings().first()
            if row:
                results.append(_to_quote_item(row, qty))
                continue  # next want

        # Otherwise, deterministic fuzzy search
        candidates = deterministic_search(db, want)
        if not candidates:
            unfulfilled.append({"reason": "no_match", "request": want})
            continue

        top = candidates[0]
        results.append(_to_quote_item(top, qty))

    # Optionally infer accessories from global hints
    results = _ensure_accessories(db, results, global_req)

    if not results:
        # caller can choose to 404; here we just return explicit reason
        return {
            "items": [],
            "unfulfilled": unfulfilled or [{"reason": "no_matches_for_all_items"}],
            "total": 0.0,
            "currency": "USD",
        }

    currency = results[0]["currency"]
    total = round(sum(i["subtotal"] for i in results), 2)

    return {
        "items": results,
        "unfulfilled": unfulfilled,
        "total": total,
        "currency": currency,
        "notes": None,
    }
