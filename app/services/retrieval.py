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
        "outdoor camera", "indoor camera", "day/night camera", "day night camera",
        "thermal camera", "thermal network camera", "fixed dome camera", "advanced dome camera"
    ],
    "nvr":    ["nvr", "recorder", "network video recorder", "digital video recorder", "server", "video server"],
    "switch": ["switch", "network switch", "poe switch", "ethernet switch"],
}
# Stronger bans to keep out accessories/licenses/mounts/etc.
FAMILY_BAN = {
    "camera": [
        "adapter", "charger", "license", "software", "relay", "battery", "power supply",
        "housing", "cover", "smoked dome", "cap", "weather cap",
        "sunshade", "sun shade", "sunshield", "shroud", "skin", "bubble", "clear dome",
        "stand", "joystick", "encoder", "decoder",
        "appliance", "kit", "recessed", "dome cover", "rack mount", "mount kit",
        "cable", "cables", "connector", "connectors", "wire", "wires", "cord", "cords",
        "spare part", "spare", "replacement", "accessory", "accessories"
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
    # Power over Ethernet variants
    "poe":     ["poe", "poe+", "power over ethernet", "power over ethernet+", "poe plus", "poe+", "802.3af", "802.3at", "ethernet power", "network power"],
    "poe+":    ["poe+", "poe plus", "802.3at", "802.3af+", "high power poe", "poe plus", "poe+", "ethernet power plus"],
    
    # Infrared/Night vision variants
    "ir-30m":  ["ir 30m", "ir-30m", "infrared 30m", "infrared 30 m", "exir 30m", "ir30m", "ir 30", "30m ir", "30m infrared", "night vision 30m", "night vision 30 m", "30m night", "ir range 30m", "30m range", "30 meter ir", "30 meter infrared"],
    "ir-60m":  ["ir 60m", "ir-60m", "infrared 60m", "infrared 60 m", "exir 60m", "ir60m", "ir 60", "60m ir", "60m infrared", "night vision 60m", "night vision 60 m", "60m night", "ir range 60m", "60m range", "60 meter ir", "60 meter infrared"],
    
    # Location variants
    "outdoor": ["outdoor", "outdoors", "outside", "external", "exterior", "ip66", "ip67", "ip68", "weatherproof", "weather resistant", "weather-resistant", "waterproof", "water resistant", "water-resistant", "weather sealed", "weather-sealed", "outdoor rated", "outdoor-rated", "exterior grade", "exterior-grade", "outdoor use", "outdoor use", "for outdoor", "outdoor camera", "outdoor security", "outdoor surveillance"],
    "indoor":  ["indoor", "indoors", "inside", "internal", "interior", "indoor use", "for indoor", "indoor camera", "indoor security", "indoor surveillance", "home use", "office use", "indoor only", "indoor-only"],
    
    # Vandal resistance variants
    "vandal":  ["vandal", "vandalism", "vandal resistant", "vandal-resistant", "vandal proof", "vandal-proof", "anti-vandal", "antivandal", "ik10", "ik 10", "ik10 rating", "ik 10 rating", "vandal protection", "tamper resistant", "tamper-resistant", "tamper proof", "tamper-proof"],
    
    # Audio variants
    "audio":   ["audio", "microphone", "mic", "microphone", "sound", "audio recording", "audio capture", "built-in mic", "built-in microphone", "integrated mic", "integrated microphone", "two-way audio", "two way audio", "bidirectional audio", "speaker", "speakers", "audio output", "audio input"],
    
    # Resolution variants
    "4k":      ["4k", "4k uhd", "4k ultra hd", "4k ultra hd", "uhd", "ultra hd", "ultra high definition", "4k resolution", "4k video", "4k recording", "4k camera", "4k surveillance", "4k security", "3840x2160", "2160p", "4k@30fps", "4k@60fps"],
    "1080p":   ["1080p", "1080 p", "full hd", "fhd", "full high definition", "full high definition", "1080p hd", "1080p high definition", "1080p resolution", "1080p video", "1080p recording", "1080p camera", "1080p surveillance", "1080p security", "1920x1080", "1080i", "1080p@30fps", "1080p@60fps"],
    "720p":    ["720p", "720 p", "hd", "high definition", "720p hd", "720p high definition", "720p resolution", "720p video", "720p recording", "720p camera", "720p surveillance", "720p security", "1280x720", "720i", "720p@30fps", "720p@60fps"],
    
    # Camera type variants
    "dome":    ["dome", "dome camera", "dome security", "dome surveillance", "ceiling dome", "ceiling-mounted dome", "wall dome", "wall-mounted dome", "indoor dome", "outdoor dome", "dome style", "dome-style", "dome shaped", "dome-shaped", "hemispherical", "semi-hemispherical"],
    "bullet":  ["bullet", "bullet camera", "bullet security", "bullet surveillance", "bullet style", "bullet-style", "cylindrical", "tube camera", "tube style", "tube-style", "outdoor bullet", "indoor bullet", "wall bullet", "ceiling bullet", "bullet shaped", "bullet-shaped"],
    "ptz":     ["ptz", "p-t-z", "pan tilt zoom", "pan-tilt-zoom", "pan tilt", "pan-tilt", "ptz camera", "ptz security", "ptz surveillance", "motorized", "motorized camera", "remote control", "remote-controlled", "remote controlled", "controllable", "movable", "rotating", "swiveling", "tilting", "panning", "zooming"],
    "turret":  ["turret", "turret camera", "turret security", "turret surveillance", "turret style", "turret-style", "eyeball", "eyeball camera", "eyeball style", "eyeball-style", "mini dome", "mini-dome", "compact dome", "compact-dome", "small dome", "small-dome"],
    
    # Megapixel variants - comprehensive
    "1mp":     ["1mp", "1MP", "1 megapixel", "1mp resolution", "1 mp", "1 mega pixel", "1 mega-pixel", "1 mega pixel", "1mp camera", "1mp security", "1mp surveillance", "1mp hd", "1mp high definition"],
    "2mp":     ["2mp", "2MP", "2 megapixel", "2mp resolution", "2 mp", "2 mega pixel", "2 mega-pixel", "2 mega pixel", "2mp camera", "2mp security", "2mp surveillance", "2mp hd", "2mp high definition", "2mp@30fps", "2mp@60fps"],
    "3mp":     ["3mp", "3MP", "3 megapixel", "3mp resolution", "3 mp", "3 mega pixel", "3 mega-pixel", "3 mega pixel", "3mp camera", "3mp security", "3mp surveillance", "3mp hd", "3mp high definition", "3mp@30fps", "3mp@60fps"],
    "4mp":     ["4mp", "4MP", "4 megapixel", "4mp resolution", "4 mp", "4 mega pixel", "4 mega-pixel", "4 mega pixel", "4mp camera", "4mp security", "4mp surveillance", "4mp hd", "4mp high definition", "4mp@30fps", "4mp@60fps"],
    "5mp":     ["5mp", "5MP", "5 megapixel", "5mp resolution", "5 mp", "5 mega pixel", "5 mega-pixel", "5 mega pixel", "5mp camera", "5mp security", "5mp surveillance", "5mp hd", "5mp high definition", "5mp@30fps", "5mp@60fps"],
    "6mp":     ["6mp", "6MP", "6 megapixel", "6mp resolution", "6 mp", "6 mega pixel", "6 mega-pixel", "6 mega pixel", "6mp camera", "6mp security", "6mp surveillance", "6mp hd", "6mp high definition", "6mp@30fps", "6mp@60fps"],
    "8mp":     ["8mp", "8MP", "8 megapixel", "8mp resolution", "8 mp", "8 mega pixel", "8 mega-pixel", "8 mega pixel", "8mp camera", "8mp security", "8mp surveillance", "8mp hd", "8mp high definition", "8mp@30fps", "8mp@60fps"],
    "12mp":    ["12mp", "12MP", "12 megapixel", "12mp resolution", "12 mp", "12 mega pixel", "12 mega-pixel", "12 mega pixel", "12mp camera", "12mp security", "12mp surveillance", "12mp hd", "12mp high definition", "12mp@30fps", "12mp@60fps"],
    "16mp":    ["16mp", "16MP", "16 megapixel", "16mp resolution", "16 mp", "16 mega pixel", "16 mega-pixel", "16 mega pixel", "16mp camera", "16mp security", "16mp surveillance", "16mp hd", "16mp high definition", "16mp@30fps", "16mp@60fps"],
    "20mp":    ["20mp", "20MP", "20 megapixel", "20mp resolution", "20 mp", "20 mega pixel", "20 mega-pixel", "20 mega pixel", "20mp camera", "20mp security", "20mp surveillance", "20mp hd", "20mp high definition", "20mp@30fps", "20mp@60fps"],
    
    # Additional common search terms
    "wireless": ["wireless", "wifi", "wi-fi", "wifi camera", "wireless camera", "wifi security", "wireless security", "wifi surveillance", "wireless surveillance", "no cable", "cable free", "cable-free", "wireless network", "wifi network"],
    "wired":   ["wired", "cable", "cabled", "ethernet", "network cable", "cat5", "cat6", "cat5e", "cat6a", "rj45", "wired network", "cable connection", "ethernet connection"],
    "color":   ["color", "colour", "color night vision", "colour night vision", "color ir", "colour ir", "color infrared", "colour infrared", "full color", "full colour", "color recording", "colour recording", "color video", "colour video"],
    "bw":      ["bw", "black white", "black and white", "black & white", "monochrome", "grayscale", "grey scale", "gray scale", "b&w", "black/white", "mono"],
    "day":     ["day", "daytime", "day time", "day vision", "daylight", "day light", "bright light", "sunlight", "sun light", "day mode", "daytime mode"],
    "night":   ["night", "nighttime", "night time", "night vision", "night mode", "nighttime mode", "dark", "darkness", "low light", "low-light", "lowlight", "no light", "zero light", "starlight", "star light"],
    "motion":  ["motion", "motion detection", "motion sensor", "motion sensing", "motion activated", "motion-activated", "motion trigger", "motion triggered", "motion alert", "motion alarm", "movement", "movement detection", "movement sensor", "movement sensing"],
    "recording": ["recording", "record", "records", "recorded", "video recording", "audio recording", "continuous recording", "24/7 recording", "24 7 recording", "always recording", "constant recording", "permanent recording", "storage", "stored", "saved"],
    "live":    ["live", "live view", "live viewing", "live feed", "live stream", "live streaming", "real time", "real-time", "realtime", "live monitoring", "live surveillance", "live security", "remote viewing", "remote view", "remote access"],
    "zoom":    ["zoom", "zooming", "zoomed", "optical zoom", "digital zoom", "zoom lens", "zoom capability", "zoom function", "zoom feature", "magnification", "magnify", "close up", "close-up", "telephoto", "wide angle", "wide-angle", "wideangle"],
    "lens":    ["lens", "lenses", "focal length", "focal length", "mm lens", "millimeter lens", "fixed lens", "fixed focal", "varifocal", "vari-focal", "auto focus", "autofocus", "auto-focus", "manual focus", "manual-focus"],
    "mount":   ["mount", "mounting", "mounted", "bracket", "brackets", "mounting bracket", "mounting hardware", "ceiling mount", "wall mount", "pole mount", "corner mount", "universal mount", "adjustable mount", "fixed mount"],
    "storage": ["storage", "sd card", "sd-card", "micro sd", "micro-sd", "memory card", "local storage", "cloud storage", "nvr", "dvr", "recorder", "recording device", "storage device", "hard drive", "harddisk", "hard disk"],
    "alarm":   ["alarm", "alerts", "alert", "notification", "notifications", "alarm system", "alert system", "warning", "warnings", "siren", "sirens", "buzzer", "buzzers", "chime", "chimes"],
    "smart":   ["smart", "intelligent", "ai", "artificial intelligence", "smart detection", "smart analytics", "smart features", "smart camera", "smart security", "smart surveillance", "advanced", "advanced features", "advanced detection"],
    "budget":  ["budget", "cheap", "inexpensive", "affordable", "low cost", "low-cost", "lowcost", "economical", "value", "value for money", "cost effective", "cost-effective", "costeffective"],
    "premium": ["premium", "high end", "high-end", "high end", "professional", "pro", "commercial", "enterprise", "business", "industrial", "heavy duty", "heavy-duty", "heavy duty", "rugged", "durable", "reliable"],
    "compact": ["compact", "small", "mini", "miniature", "tiny", "small form", "small-form", "smallform", "space saving", "space-saving", "spacesaving", "discrete", "discreet", "unobtrusive", "hidden", "concealed"],
    "visible": ["visible", "obvious", "deterrent", "deterrent camera", "deterrent security", "deterrent surveillance", "warning", "warning camera", "warning security", "warning surveillance", "noticeable", "prominent", "conspicuous"],
}

WEIGHTS = {
    "token_hit": 3.0,
    "family_hit": 2.0,
    "ban_penalty": -6.0,
    "brand_pref": 2.0,
    "brand_avoid": -2.0,
    "budget_fit": 1.0,
    "over_budget_penalty": -1e9,
    "price_penalty": 0.01,  # Penalty per dollar to favor cheaper cameras
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
    async def _simple_camera_search(self, want: Dict[str, Any], variants: List[str], limit: int = 200) -> List[Dict[str, Any]]:
        """Simplified camera search for megapixel requirements that works reliably."""
        where_conditions = ["active = true"]
        location = (want.get("location") or "").lower()
        
        # Extract megapixel tokens
        mp_tokens = [v for v in variants if any(mp in v.lower() for mp in ['mp', 'megapixel'])]
        
        # Require camera keywords
        where_conditions.append("(LOWER(description) LIKE '%camera%' OR LOWER(description) LIKE '%dome%' OR LOWER(description) LIKE '%bullet%' OR LOWER(description) LIKE '%turret%')")
        
        # If outdoor requested, require outdoor indicators
        if location == "outdoor":
            where_conditions.append("(LOWER(description) LIKE '%outdoor%' OR LOWER(description) LIKE '%ip66%' OR LOWER(description) LIKE '%ip67%')")
        
        # Require megapixel specification
        if mp_tokens:
            mp_conditions = []
            for mp_token in mp_tokens:
                mp_conditions.append(f"LOWER(description) LIKE '%{mp_token}%'")
            where_conditions.append("(" + " OR ".join(mp_conditions) + ")")
        
        # Exclude obvious accessories
        where_conditions.append("LOWER(description) NOT LIKE '%mount%'")
        where_conditions.append("LOWER(description) NOT LIKE '%bracket%'")
        where_conditions.append("LOWER(description) NOT LIKE '%holder%'")
        where_conditions.append("LOWER(description) NOT LIKE '%housing%'")
        
        sql = f"""
            SELECT sku, description, price, currency, family, active
            FROM products
            WHERE {' AND '.join(where_conditions)}
            ORDER BY price ASC NULLS LAST, sku ASC
            LIMIT {int(limit)}
        """
        
        rows = await self.conn.fetch(sql)
        results = [dict(r) for r in rows]
        
        # Apply scoring to prioritize exact matches
        def score(row: Dict[str, Any]) -> float:
            d = (row.get("description") or "").lower()
            price = float(row.get("price") or 0)
            s = 0.0
            
            # Start with a high base score for all valid results
            s = 100.0
            
            # Score based on token matches
            hits = sum(1 for v in variants if v in d)
            s += 3.0 * hits
            
            # Boost for exact MP matches
            mp_hits = sum(1 for mp_token in mp_tokens if mp_token in d)
            s += 10.0 * mp_hits
            
            # Very strong price preference (lower is better)
            # Subtract the actual price to heavily favor cheaper cameras
            s -= price / 10.0  # Strong penalty for expensive cameras
            
            return s
        
        scored = sorted(results, key=score, reverse=True)
        return scored[:10]

    async def deterministic_search(self, want: Dict[str, Any], limit: int = 200) -> List[Dict[str, Any]]:
        raw_family = want.get("family")
        fam = _normalize_family(raw_family, want)
        fam_l = (fam or "").lower()

        tokens = _collect_tokens(want)
        variants = _expand_variants(tokens)

        # For camera searches with megapixel requirements, use a simpler, more reliable approach
        if fam_l == "camera" and any('mp' in v.lower() for v in variants):
            return await self._simple_camera_search(want, variants, limit)
        
        # For all camera searches, use the simplified approach to avoid SQL complexity issues
        if fam_l == "camera":
            return await self._simple_camera_search_with_brand(want, variants, limit)

        must_any = FAMILY_MUST.get(fam_l or "", [])
        bans = FAMILY_BAN.get(fam_l or "", [])

        where: List[str] = ["active = true"]
        params: List[Any] = []
        p = 0
        
        # Add family filter to ensure we get the right product type
        # For cameras, be more flexible since actual cameras might be in other families
        if fam_l == "camera":
            # For cameras, look in multiple families that might contain actual cameras
            where.append("(LOWER(family) = 'cameras' OR LOWER(family) = 'audio and power accessories' OR LOWER(family) = 'recorder accessories' OR LOWER(family) = 'power supply' OR LOWER(family) = 'software and licensing')")
        elif fam_l:
            p += 1
            params.append(fam_l)
            where.append(f"LOWER(family) = ${p}")

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
                "mp @", "mp resolution", "megapixel", "fps", "degree", "mm fixed focal", "ir distance", "fov", "day & night", "ip67", "ik10",
                "mp at", "mp with", "mp and", "mp for", "mp camera", "mp dome", "mp bullet", "mp turret"
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
                camera_spec_sql.append(f"LOWER(description) LIKE ${p}")
            
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
            
            # Boost score for megapixel matches
            mp_tokens = [v for v in variants if any(mp in v.lower() for mp in ['mp', 'megapixel'])]
            if mp_tokens and fam_l == "camera":
                mp_hits = sum(1 for mp_token in mp_tokens if mp_token in d)
                if mp_hits > 0:
                    s += 10.0 * mp_hits  # High boost for exact MP matches
            
            # Apply price penalty to favor cheaper cameras for vague requests
            # Only apply if this is a vague camera request (no specific features)
            is_vague_camera = (fam_l == "camera" and 
                             not want.get("features") and 
                             not want.get("formFactor") and
                             not any(mp in v.lower() for v in variants for mp in ['mp', 'megapixel']))
            
            if is_vague_camera:
                s -= WEIGHTS["price_penalty"] * price  # Penalty increases with price
            
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

    async def _simple_camera_search_with_brand(self, want: Dict[str, Any], variants: List[str], limit: int) -> List[Dict[str, Any]]:
        """
        Simplified camera search that works around SQL complexity issues.
        """
        # Get brand preferences
        pref, avoid = _brand_lists(want)
        
        # Build a simple SQL query that looks for actual cameras
        sql = """
            SELECT sku, description, price, currency, family, active
            FROM products
            WHERE active = true
            AND (LOWER(family) = 'cameras' OR LOWER(family) = 'audio and power accessories' OR LOWER(family) = 'recorder accessories' OR LOWER(family) = 'power supply' OR LOWER(family) = 'software and licensing')
            AND (LOWER(description) LIKE 'network camera%' OR LOWER(description) LIKE 'ip camera%' OR LOWER(description) LIKE 'cctv camera%' OR LOWER(description) LIKE 'surveillance camera%' OR LOWER(description) LIKE 'dome camera%' OR LOWER(description) LIKE 'bullet camera%' OR LOWER(description) LIKE 'ptz camera%' OR LOWER(description) LIKE 'turret camera%' OR LOWER(description) LIKE 'outdoor camera%' OR LOWER(description) LIKE 'indoor camera%' OR LOWER(description) LIKE 'thermal camera%' OR LOWER(description) LIKE 'advanced dome camera%')
            ORDER BY price ASC NULLS LAST, sku ASC
            LIMIT 50
        """
        
        rows = await self.conn.fetch(sql)
        results = [dict(row) for row in rows]
        
        # Filter by brand preferences
        if pref:
            results = [r for r in results if any(brand in (r.get("description") or "").lower() for brand in pref)]
        
        if avoid:
            results = [r for r in results if not any(brand in (r.get("description") or "").lower() for brand in avoid)]
        
        # Filter out accessories - exclude items that are clearly accessories
        accessory_keywords = [
            'mount', 'bracket', 'housing', 'cover', 'adapter', 'charger', 'license', 'software',
            'relay', 'battery', 'power supply', 'cable', 'connector', 'wire', 'cord',
            'spare part', 'spare', 'replacement', 'accessory', 'accessories', 'kit',
            'wiper', 'casing', 'holder', 'plate', 'bracket', 'stand', 'joystick',
            'microphone', 'speaker', 'encoder', 'decoder', 'appliance', 'recessed',
            'dome cover', 'rack mount', 'mount kit', 'sunshade', 'sun shield',
            'sunshield', 'shroud', 'skin', 'bubble', 'clear dome', 'cap', 'weather cap'
        ]
        
        # Only exclude if the description is primarily about accessories
        filtered_results = []
        for r in results:
            desc = (r.get("description") or "").lower()
            
            # Check if this is clearly a camera (must be a camera, not an accessory for cameras)
            is_camera = any(desc.startswith(camera_term) for camera_term in [
                'network camera', 'ip camera', 'cctv camera', 'surveillance camera',
                'dome camera', 'bullet camera', 'ptz camera', 'turret camera',
                'outdoor camera', 'indoor camera', 'thermal camera', 'advanced dome camera'
            ])
            
            # Check if this is primarily an accessory (starts with accessory terms)
            is_accessory = any(desc.startswith(accessory_term) for accessory_term in [
                'mount', 'bracket', 'housing', 'cover', 'adapter', 'charger', 'license', 'software',
                'relay', 'battery', 'power supply', 'cable', 'connector', 'wire', 'cord',
                'spare part', 'spare', 'replacement', 'accessory', 'accessories', 'kit',
                'wiper', 'casing', 'holder', 'plate', 'stand', 'joystick',
                'microphone', 'speaker', 'encoder', 'decoder', 'appliance', 'recessed',
                'dome cover', 'rack mount', 'mount kit', 'sunshade', 'sun shield',
                'sunshield', 'shroud', 'skin', 'bubble', 'clear dome', 'cap', 'weather cap'
            ])
            
            # Only include if it's clearly a camera and not an accessory
            if is_camera and not is_accessory:
                filtered_results.append(r)
        
        results = filtered_results
        
        # Score and filter by token matches
        def score(row: Dict[str, Any]) -> float:
            d = (row.get("description") or "").lower()
            price = float(row.get("price") or 0)
            hits = sum(1 for v in variants if v in d)
            s = 0.0
            s += WEIGHTS["token_hit"] * hits
            s += WEIGHTS["brand_pref"] * sum(1 for b in pref if b in d)
            s += WEIGHTS["brand_avoid"] * sum(1 for b in avoid if b in d)
            
            # Apply price penalty to favor cheaper cameras for vague requests
            is_vague_camera = (not want.get("features") and 
                             not want.get("formFactor") and
                             not any(mp in v.lower() for v in variants for mp in ['mp', 'megapixel']))
            
            if is_vague_camera:
                s -= WEIGHTS["price_penalty"] * price
            
            return s
        
        scored = sorted(results, key=score, reverse=True)
        
        # Filter by minimum token hits and enforce specific feature requirements
        filtered = []
        for r in scored:
            d = (r.get("description") or "").lower()
            hits = sum(1 for v in variants if v in d)
            
            # Check if camera meets minimum token requirements
            if hits < MIN_TOKEN_HITS:
                continue
            
            # Enforce specific feature requirements
            meets_requirements = True
            
            # Check for PoE requirement
            if 'poe' in [f.lower() for f in want.get('features', [])]:
                has_poe = any(poe_term in d for poe_term in ['poe', 'poe+', 'power over ethernet', '802.3af', '802.3at'])
                if not has_poe:
                    meets_requirements = False
            
            # Check for IR 30m requirement
            if 'ir-30m' in [f.lower() for f in want.get('features', [])]:
                has_ir_30m = any(ir_term in d for ir_term in ['ir 30m', 'ir-30m', 'infrared 30m', '30m ir', 'ir range 30m', '30 meter ir'])
                if not has_ir_30m:
                    meets_requirements = False
            
            # Check for IR illumination requirement
            if 'ir-illumination' in [f.lower() for f in want.get('features', [])]:
                has_ir_illumination = any(ir_term in d for ir_term in ['ir illumination', 'ir-illumination', 'infrared illumination', 'night vision', 'night-vision', 'ir led', 'ir lighting'])
                if not has_ir_illumination:
                    meets_requirements = False
            
            # Check for outdoor requirement
            if want.get('location') == 'outdoor':
                has_outdoor = any(outdoor_term in d for outdoor_term in ['outdoor', 'ip66', 'ip67', 'weatherproof', 'weather resistant'])
                if not has_outdoor:
                    meets_requirements = False
            
            # Check for dome requirement
            if want.get('formFactor') == 'dome':
                has_dome = any(dome_term in d for dome_term in ['dome camera', 'dome'])
                if not has_dome:
                    meets_requirements = False
            
            if meets_requirements:
                filtered.append(r)
        
        return filtered[:limit]

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
        
        # Always allow search for NVR/server and switch families (they are valid products even without specific features)
        if fam in ["nvr", "switch"]:
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
