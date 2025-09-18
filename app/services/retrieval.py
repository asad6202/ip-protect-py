"""
Deterministic product retrieval for quote generation (DB-agnostic fuzzy search).

- Family-aware: requires at least one family keyword (camera/nvr/switch) to appear
  and bans obvious accessories per family to avoid wrong matches.
- Token variant expansion: "ir-30m" ~ "infrared 30 m"; "poe+" ~ "802.3at".
- Scoring + minimum token hits: reduces random low-relevance rows.
- Partial success: returns top candidates even if not perfect matches.
- Asyncpg for the service path; optional sync helpers kept for completeness.
"""

from __future__ import annotations
import re
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy import text  # only used by optional sync helpers
import asyncpg

# -------------------------- Tunables / Business Rules -------------------------

FAMILY_MAP = {
    "camera": ["camera", "cameras", "dome", "bullet", "ptz", "turret", "sensor unit"],
    "nvr":    ["nvr", "recorder", "network video recorder", "server", "servers"],
    "switch": ["switch", "poe switch", "poe+ switch"],
}

FAMILY_MUST = {
    # Require actual camera keywords - be more specific to avoid accessories
    "camera": [
        "network camera", "ip camera", "cctv camera", "surveillance camera",
        "dome camera", "bullet camera", "ptz camera", "turret camera",
        "outdoor camera", "indoor camera", "day/night camera", "day night camera"
    ],
    "nvr":    ["nvr", "recorder", "network video recorder", "digital video recorder", "server", "video server"],
    "switch": ["switch", "network switch", "poe switch", "ethernet switch"],
}
# Stronger bans to keep out accessories/licenses/mounts/etc.
FAMILY_BAN = {
    "camera": [
        "adapter", "charger", "license", "software", "relay", "tamper", "battery", "power supply",
        "mount", "bracket", "housing", "cover", "smoked dome", "cap", "weather cap",
        "sunshade", "sun shade", "sunshield", "shroud", "skin", "bubble", "clear dome",
        "stand", "joystick", "microphone", "mic", "speaker", "encoder", "decoder",
        "appliance", "kit", "recessed", "dome cover", "rack", "rack mount", "mount kit"
    ],
    "nvr": [
        "adapter", "charger", "license", "software", "tamper", "battery",
        "mount", "bracket", "housing", "cover", "cap", "weather cap",
        "sunshade", "sun shade", "kit", "rack", "rack mount", "recorder mount"
    ],
    "switch": [
        "adapter", "charger", "license", "software", "battery",
        "mount", "bracket", "housing", "cover", "cap", "weather cap",
        "sunshade", "sun shade", "tamper", "joystick", "speaker", "microphone", "mic",
        "appliance", "kit", "rack", "rack mount", "recorder mount"
    ],
}

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

WEIGHTS = {
    "token_hit": 3.0,
    "family_hit": 2.0,
    "ban_penalty": -6.0,
    "brand_pref": 2.0,
    "brand_avoid": -2.0,
    "budget_fit": 1.0,
    "over_budget_penalty": -1e9,
}
MIN_TOKEN_HITS = 1
HARD_BUDGET_CAP = True

# ---------------------------- Helper functions --------------------------------

def _normalize_family(raw_family: Optional[str], want: Dict[str, Any]) -> Optional[str]:
    rf = (raw_family or "").lower()
    if rf:
        for fam, hints in FAMILY_MAP.items():
            if rf == fam or any(h in rf for h in hints):
                return fam
    probe = f"{(want.get('formFactor') or '').lower()} {(want.get('location') or '').lower()}".strip()
    for fam, hints in FAMILY_MAP.items():
        if any(h in probe for h in hints):
            return fam
    return None

def _expand_variants(tokens: List[str]) -> List[str]:
    out: List[str] = []
    for t in tokens:
        out.extend(TOKEN_VARIANTS.get(t.lower(), [t.lower()]))
    seen, uniq = set(), []
    for v in out:
        if v not in seen:
            seen.add(v); uniq.append(v)
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

# ----------------------------- Deterministic search (async) -------------------

class ProductRetrieval:
    """
    Async product retrieval service that combines deterministic search with vector search,
    plus a fast path for vague camera asks (cheapest physical camera).
    """

    def __init__(self, conn: asyncpg.Connection):
        self.conn = conn
    async def deterministic_search(self, want: Dict[str, Any], limit: int = 200) -> List[Dict[str, Any]]:
        raw_family = want.get("family")
        fam = _normalize_family(raw_family, want)
        fam_l = (fam or "").lower()

        tokens = _collect_tokens(want)
        variants = _expand_variants(tokens)

        must_any = FAMILY_MUST.get(fam_l or "", [])
        bans = FAMILY_BAN.get(fam_l or "", [])

        where: List[str] = ["active = true"]
        params: List[Any] = []
        p = 0

        # ---- MUST: at least one required family token ----
        if must_any:
            must_sql = []
            for m in must_any:
                p += 1
                params.append(f"%{m}%")
                must_sql.append(f"LOWER(description) LIKE ${p}")
            where.append("(" + " OR ".join(must_sql) + ")")

        # ---- Family-specific hard requirements from 'want' ----
        # Camera: enforce key requested traits so accessories don't slip in
        desc_constraints = []
        if fam_l == "camera":
            # CRITICAL: Must be an actual camera, not an accessory
            # Look for camera specifications that indicate actual cameras
            camera_spec_patterns = [
                "mp @", "megapixel", "fps", "degree", "mm fixed focal", "ir distance", "fov", "day & night", "ip67", "ik10"
            ]
            camera_spec_sql = []
            for pattern in camera_spec_patterns:
                p += 1
                params.append(f"%{pattern}%")
                camera_spec_sql.append(f"LOWER(description) LIKE ${p}")
            
            # Also look for specific camera type patterns but exclude accessories
            camera_type_patterns = [
                "bullet camera", "dome camera", "ptz camera", "turret camera",
                "network camera", "ip camera", "cctv camera", "surveillance camera"
            ]
            for pattern in camera_type_patterns:
                p += 1
                params.append(f"%{pattern}%")
                # Exclude common accessory keywords
                camera_spec_sql.append(f"(LOWER(description) LIKE ${p} AND LOWER(description) NOT LIKE '%for %' AND LOWER(description) NOT LIKE '%compatible with%' AND LOWER(description) NOT LIKE '%accessory%' AND LOWER(description) NOT LIKE '%mount%' AND LOWER(description) NOT LIKE '%bracket%' AND LOWER(description) NOT LIKE '%housing%' AND LOWER(description) NOT LIKE '%cover%' AND LOWER(description) NOT LIKE '%sunshade%' AND LOWER(description) NOT LIKE '%back box%' AND LOWER(description) NOT LIKE '%wiper%' AND LOWER(description) NOT LIKE '%replacement%' AND LOWER(description) NOT LIKE '%license%' AND LOWER(description) NOT LIKE '%software%' AND LOWER(description) NOT LIKE '%sticker%' AND LOWER(description) NOT LIKE '%support%' AND LOWER(description) NOT LIKE '%holder%' AND LOWER(description) NOT LIKE '%charging%' AND LOWER(description) NOT LIKE '%docking%' AND LOWER(description) NOT LIKE '%heater%' AND LOWER(description) NOT LIKE '%power supply%')")
            
            if camera_spec_sql:
                desc_constraints.append("(" + " OR ".join(camera_spec_sql) + ")")
            
            # If user asked for outdoor: require outdoor/ip66/ip67/weatherproof
            if (want.get("location") or "").lower() == "outdoor":
                outdoor_patterns = ["outdoor", "ip66", "ip67", "weatherproof", "weather proof", "nema4x", "nema 4x"]
                outdoor_sql = []
                for pattern in outdoor_patterns:
                    p += 1
                    params.append(f"%{pattern}%")
                    outdoor_sql.append(f"LOWER(description) LIKE ${p}")
                if outdoor_sql:
                    desc_constraints.append("(" + " OR ".join(outdoor_sql) + ")")
            
            # If tokens include poe
            if any(t in ("poe","poe+") for t in (want.get("features") or [])):
                desc_constraints.append("LOWER(description) LIKE '%poe%'")
            
            # If tokens include ir-30m (or other ir-XXm)
            ir_tok = next((t for t in (want.get("features") or []) if t.startswith("ir-")), None)
            if ir_tok:
                m = re.search(r"ir-(\d+)m", ir_tok)
                if m:
                    meters = m.group(1)
                    p += 1
                    params.append(f"%ir%{meters}m%")
                    desc_constraints.append(f"LOWER(description) LIKE ${p}")
            
            # If formFactor present - be more specific
            ff = (want.get("formFactor") or "").lower()
            if ff in ("dome","bullet","ptz","turret"):
                # Look for "dome camera", "bullet camera", etc. not just "dome"
                p += 1
                params.append(f"%{ff} camera%")
                desc_constraints.append(f"LOWER(description) LIKE ${p}")

        # NVR: enforce requiredChannels if present
        if fam_l == "nvr":
            req_ch = want.get("requiredChannels")
            if req_ch:
                # Flexible channel matching patterns
                desc_constraints.append("("
                    f"description ~* '\\b{req_ch}\\s*ch\\b' OR "  # "16ch"
                    f"description ~* '\\b{req_ch}\\s*[-\\s]*channel(s)?\\b' OR "  # "16 channel", "16-channel"
                    f"description ~* '\\b{req_ch}\\s*[-\\s]*ch\\b' OR "  # "16-ch"
                    f"description ~* '{req_ch}\\s+[a-zA-Z+\\-]*\\s+channel' OR "  # "16 PoE channels"
                    f"description ~* '\\b{req_ch}\\s*[a-zA-Z+\\-]*\\s*\\b' OR "  # "16port", "16-PoE"
                    f"sku ~* '(^|\\D){req_ch}(\\D|$)' OR "  # SKU patterns: DS-7616, XRN-1620
                    f"sku ~* '(^|\\D){req_ch}\\d{{2}}(\\D|$)'"  # SKU patterns: 1620, 7616, 2116
                ")")

        # Switch: must be PoE and enforce requiredPorts if present
        if fam_l == "switch":
            desc_constraints.append("LOWER(description) LIKE '%switch%'")
            desc_constraints.append("LOWER(description) LIKE '%poe%'")
            req_ports = want.get("requiredPorts")
            if req_ports:
                desc_constraints.append("("
                    f"description ~* '\\b{req_ports}\\s*[-\\s]*port(s)?\\b' OR "  # "24 port", "24-port", "24 ports"
                    f"description ~* '\\b{req_ports}-port\\b' OR "  # "24-port"
                    f"description ~* '\\b{req_ports}\\s*x\\b' OR "  # "24x"
                    f"description ~* '\\b{req_ports}\\s*[xX]\\s*\\b' OR "  # "24 x", "24X"
                    f"description ~* 'ports?\\s*[:=]\\s*{req_ports}' OR "  # "ports: 24", "port=24"
                    f"description ~* '{req_ports}\\s+[a-zA-Z+\\-]*\\s+port' OR "  # "24 PoE+ ports", "24-Gigabit ports"
                    f"description ~* '{req_ports}\\s+[a-zA-Z+\\-]*\\s+channel' OR "  # "24-port channel"
                    f"description ~* '\\b{req_ports}\\s*[a-zA-Z+\\-]*\\s*\\b' OR "  # "24port", "24PoE", "24-PoE"
                    f"sku ~* '(^|\\D){req_ports}(\\D|$)'"  # SKU patterns
                ")")

        if desc_constraints:
            where.extend(desc_constraints)

        # ---- BANS: exclude accessories, mounts, licenses, etc. ----
        for b in bans:
            p += 1
            params.append(f"%{b}%")
            where.append(f"LOWER(description) NOT LIKE ${p}")

        # ---- Budget (hard cap) ----
        budget = want.get("budgetPerUnit") or {}
        if "amount" in budget and budget["amount"] is not None:
            p += 1
            params.append(float(budget["amount"]))
            where.append(f"price <= ${p}")

        # ---- Brand preferences ----
        pref, avoid = _brand_lists(want)
        if pref:
            # If brand preferences are specified, prioritize them
            brand_sql = []
            for brand in pref:
                p += 1
                params.append(f"%{brand}%")
                brand_sql.append(f"LOWER(description) LIKE ${p}")
            if brand_sql:
                where.append("(" + " OR ".join(brand_sql) + ")")
        
        if avoid:
            # Exclude avoided brands
            for brand in avoid:
                p += 1
                params.append(f"%{brand}%")
                where.append(f"LOWER(description) NOT LIKE ${p}")

        # ---- Soft tokens (OR) to rank within the valid set ----
        like_or = []
        for v in variants:
            p += 1
            params.append(f"%{v}%")
            like_or.append(f"LOWER(description) LIKE ${p}")

        query = [f"SELECT sku, description, price, currency, family, active FROM products WHERE {' AND '.join(where)}"]
        if like_or:
            query.append("AND (" + " OR ".join(like_or) + ")")
        query.append("ORDER BY price ASC NULLS LAST, sku ASC")
        query.append(f"LIMIT {int(limit)}")
        sql = " ".join(query)

        rows = await self.conn.fetch(sql, *params)
        results = [dict(r) for r in rows]

        # ---- Scoring & pruning ----
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
            if "amount" in budget and budget["amount"] is not None and price <= float(budget["amount"]):
                s += WEIGHTS["budget_fit"]
            return s

        scored = sorted(results, key=score, reverse=True)

        filtered: List[Dict[str, Any]] = []
        for r in scored:
            d = (r.get("description") or "").lower()
            hits = sum(1 for v in variants if v in d)
            fam_ok = (not must_any) or any(m in d for m in must_any)
            if hits >= MIN_TOKEN_HITS and fam_ok:
                filtered.append(r)

        return filtered[:10] if filtered else scored[:5]

    async def vector_fallback(self, want: Dict[str, Any], prompt: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Vector-based search fallback using embeddings (optional).
        """
        try:
            from app.ai.embeddings import get_embedding
            emb = get_embedding(prompt)
            if not emb:
                return []
            sql = """
                SELECT sku, description, price, currency, family, active,
                       1 - (embedding <=> $1) as similarity
                FROM products
                WHERE active = true
                  AND embedding IS NOT NULL
                ORDER BY embedding <=> $1
                LIMIT $2
            """
            # Convert embedding list to string format for PostgreSQL
            emb_str = '[' + ','.join(map(str, emb)) + ']'
            rows = await self.conn.fetch(sql, emb_str, limit)
            return [dict(r) for r in rows]
        except Exception as e:
            print(f"Vector search failed: {e}")
            return []

    async def cheapest_camera(self) -> List[Dict[str, Any]]:
        """
        Return the absolute cheapest PHYSICAL camera (not licenses/mounts/etc.).
        """
        bans = FAMILY_BAN.get("camera", [])
        must_any = FAMILY_MUST.get("camera", ["camera", "dome", "bullet", "ptz", "turret"])

        not_like = " AND ".join([f"LOWER(description) NOT LIKE ${i+len(must_any)+1}" for i in range(len(bans))])
        must_like = " OR ".join([f"LOWER(description) LIKE ${i+1}" for i in range(len(must_any))])

        sql = f"""
            SELECT sku, description, price, currency, family, active
            FROM products
            WHERE active = true
              AND ({must_like})
              AND {not_like}
            ORDER BY price ASC NULLS LAST, sku ASC
            LIMIT 1
        """
        params = [f"%{m}%" for m in must_any] + [f"%{b}%" for b in bans]
        rows = await self.conn.fetch(sql, *params)
        return [dict(rows[0])] if rows else []

    async def search_products(self, want: Dict[str, Any], prompt: str) -> List[Dict[str, Any]]:
        """
        Main search method:
        - If explicit SKU, return it (exact match only)
        - If vague camera → cheapest physical camera
        - Else deterministic search
        - No fallback - return empty if no exact matches
        """
        # 1) Exact SKU? (Try exact match first, then description search)
        sku = (want.get("sku") or "").strip()
        if sku:
            # Try exact SKU match first
            sql = """
                SELECT sku, description, price, currency, family, active
                FROM products
                WHERE active = true AND sku = $1
                LIMIT 1
            """
            rows = await self.conn.fetch(sql, sku)
            if rows:
                return [dict(rows[0])]
            
            # Try partial SKU match (SKU contains the search term)
            sql = """
                SELECT sku, description, price, currency, family, active
                FROM products
                WHERE active = true AND sku LIKE $1
                LIMIT 1
            """
            rows = await self.conn.fetch(sql, f"%{sku}%")
            if rows:
                return [dict(rows[0])]
            
            # Try description match (SKU mentioned in description)
            sql = """
                SELECT sku, description, price, currency, family, active
                FROM products
                WHERE active = true AND LOWER(description) LIKE LOWER($1)
                ORDER BY 
                    CASE 
                        WHEN LOWER(description) LIKE LOWER($1 || '%') THEN 1
                        WHEN LOWER(description) LIKE LOWER('%' || $1 || '%') THEN 2
                        ELSE 3
                    END,
                    sku ASC
                LIMIT 1
            """
            rows = await self.conn.fetch(sql, f"%{sku}%")
            if rows:
                return [dict(rows[0])]
            
            # If specific SKU requested but not found anywhere, return empty
            return []

        # 2) Derive hard constraints from prompt if missing (so intent bugs can't break constraints)
        # First normalize the family, then use the normalized value
        raw_family = want.get("family")
        fam = _normalize_family(raw_family, want) or (want.get("family") or "").lower()
        want = dict(want)  # copy so we can add constraints
        if fam == "nvr" and not want.get("requiredChannels"):
            m = re.search(r"\b(\d{1,3})\s*chan(nel)?s?\b", prompt, flags=re.I)
            if m:
                want["requiredChannels"] = int(m.group(1))
        if fam == "switch" and not want.get("requiredPorts"):
            m = re.search(r"\b(\d{1,3})\s*port(s)?\b", prompt, flags=re.I)
            if m:
                want["requiredPorts"] = int(m.group(1))

        # 3) Vague camera → cheapest physical camera
        if (want.get("vague") is True) and (want.get("family", "").lower() == "camera"):
            cheapest = await self.cheapest_camera()
            if cheapest:
                return cheapest

        # 4) Deterministic search - but only if we have meaningful search criteria
        # Check if we have enough specific criteria to warrant a search
        has_specific_criteria = False
        
        # Always allow search for NVR/server family (they are valid products even without specific features)
        if fam == "nvr":
            has_specific_criteria = True
        
        # Check for specific features that would indicate a real search
        if want.get("features"):
            # Look for specific technical features
            specific_features = ["outdoor", "indoor", "poe", "poe+", "ir-30m", "ir-60m", "4k", "1080p", "vandal", "audio"]
            if any(feature in [f.lower() for f in want.get("features", [])] for feature in specific_features):
                has_specific_criteria = True
        
        # Check for form factor
        if want.get("formFactor") and want.get("formFactor").lower() in ["dome", "bullet", "ptz", "turret"]:
            has_specific_criteria = True
        
        # Check for location
        if want.get("location") and want.get("location").lower() in ["outdoor", "indoor"]:
            has_specific_criteria = True
        
        # Check for specific requirements
        if want.get("requiredChannels") or want.get("requiredPorts"):
            has_specific_criteria = True
        
        # Only search if we have specific criteria
        if not has_specific_criteria:
            return []
        
        results = await self.deterministic_search(want, limit=50)

        # 5) Vector fallback if few results (but not if we have hard constraints) - COMMENTED OUT
        # have_hard = (fam == "nvr" and want.get("requiredChannels")) or (fam == "switch" and want.get("requiredPorts"))
        # used_vector_fallback = False
        # if not have_hard and len(results) < 3:
        #     try:
        #         vf = await self.vector_fallback(want, prompt, limit=20)
        #         if vf:  # Only add results if vector fallback actually returned something
        #             seen = {r['sku'] for r in results}
        #             for r in vf:
        #                 if r['sku'] not in seen:
        #                     r['_used_vector_fallback'] = True  # Mark vector fallback items
        #                     results.append(r)
        #                     seen.add(r['sku'])
        #                     used_vector_fallback = True
        #     except Exception as e:
        #         # If vector fallback fails (e.g., embedding column doesn't exist), just skip it
        #         print(f"Vector fallback skipped: {e}")

        # Mark all results with fallback info
        for r in results:
            r['_used_vector_fallback'] = False  # Always false since fallback is disabled
            r['_used_any_fallback'] = False

        return results

# -------------------- Optional sync helpers (if you still use them) --------------------

def deterministic_search(db, want: Dict[str, Any], limit: int = 200) -> List[Dict[str, Any]]:
    # kept for compatibility if you still call assemble_quote() somewhere
    raw_family = want.get("family")
    fam = _normalize_family(raw_family, want)

    tokens = _collect_tokens(want)
    variants = _expand_variants(tokens)

    must_any = FAMILY_MUST.get(fam or "", [])
    bans = FAMILY_BAN.get(fam or "", [])

    where: List[str] = ["active = true"]
    params: Dict[str, Any] = {}

    if must_any:
        must_sql = []
        for i, m in enumerate(must_any):
            k = f"m{i}"; params[k] = f"%{m}%"
            must_sql.append(f"LOWER(description) LIKE :{k}")
        where.append("(" + " OR ".join(must_sql) + ")")

    for j, b in enumerate(bans):
        k = f"b{j}"; params[k] = f"%{b}%"
        where.append(f"LOWER(description) NOT LIKE :{k}")

    budget = want.get("budgetPerUnit") or {}
    if "amount" in budget and budget["amount"] is not None and HARD_BUDGET_CAP:
        params["maxp"] = float(budget["amount"])
        where.append("price <= :maxp")

    like_or = []
    for i, v in enumerate(variants):
        k = f"v{i}"; params[k] = f"%{v}%"
        like_or.append(f"LOWER(description) LIKE :{k}")

    sql = f"""
      SELECT sku, description, price, currency, family, active
      FROM products
      WHERE {' AND '.join(where)}
      {" AND (" + " OR ".join(like_or) + ")" if like_or else ""}
      ORDER BY price ASC NULLS LAST, sku ASC
      LIMIT {int(limit)}
    """
    rows = db.execute(text(sql), params).mappings().all()

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
        return s

    scored = sorted([dict(r) for r in rows], key=score, reverse=True)
    filtered: List[Dict[str, Any]] = []
    for r in scored:
        d = (r.get("description") or "").lower()
        hits = sum(1 for v in variants if v in d)
        fam_ok = (not must_any) or any(m in d for m in must_any)
        if hits >= MIN_TOKEN_HITS and fam_ok:
            filtered.append(r)

    return filtered[:10] if filtered else scored[:5]
