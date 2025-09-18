"""
DB-agnostic intent extractor for CCTV product requests.

- Deterministic OpenAI call (temperature=0) + in-memory cache by prompt
- Falls back to a local heuristic parser if OpenAI is unavailable
- Normalizes features (poe/poe+, h265, ir-XXm, 4k/1080p, indoor/outdoor, vandal, audio)
- Extracts SKUs/EANs, quantities, budgets, brand prefs/avoids
- Adds 'vague' flag for camera-only asks (no SKU/form/location/features)
"""

from __future__ import annotations
import os
import re
import json
from typing import Any, Dict, List, Optional, Tuple
from dotenv import load_dotenv

try:
    from openai import OpenAI
except Exception:
    OpenAI = None  # type: ignore

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_INTENT_MODEL", "gpt-4o-mini")

# ------------------------------- Regexes --------------------------------------

EAN_RE   = re.compile(r"\b(?<!\d)(\d{13})(?!\d)\b")
UPC_RE   = re.compile(r"\b(?<!\d)(\d{12})(?!\d)\b")
SKU_RE   = re.compile(r"\b(?=[A-Za-z0-9_-]{3,40}\b)(?=.*[A-Za-z])(?=.*\d)[A-Za-z0-9_-]+\b")
QTY_PAIR = re.compile(r"\b(?:(?:qty|quantity|need|want)\s*)?(\d{1,3})\s*(?:x|\*)?\b", re.I)
IR_RE    = re.compile(r"\b(?:ir|infrared|exir)\s*[- ]?\s*(\d{1,3})\s*m\b", re.I)
MONEY_RE = re.compile(r"(?:(?:cap|budget|<=|under|max)\s*)?\$?\s*(\d{2,6})(?:\s*(usd|cad|eur|gbp|aed|pkr))?\b", re.I)
BRAND_RE = re.compile(r"\b(axis|hanwha|wisenet|ipro|hikvision|dahua|panasonic|sony|bosch|milesight|uniview|axis communications)\b", re.I)
AVOID_RE = re.compile(r"\b(avoid|no|except)\s+(ptz|axis|hanwha|hikvision|dahua|ipro)\b", re.I)

# ------------------------ Feature normalization -------------------------------

FEATURE_ALIASES: Dict[str, List[str]] = {
    "poe":        [r"\bpoe\b"],
    "poe+":       [r"\bpoe\+\b", r"\bpoeplus\b", r"\b802\.?3at\b"],
    "h265":       [r"\bh\.?265\b"],
    "h264":       [r"\bh\.?264\b"],
    "4k":         [r"\b4k\b", r"\buhd\b"],
    "1080p":      [r"\b1080p\b", r"\bfhd\b", r"\bfull\s*hd\b"],
    "720p":       [r"\b720p\b", r"\bhd\b"],
    "vandal":     [r"\bvandal\b", r"\bik10\b"],
    "audio":      [r"\baudio\b", r"\bmicrophone\b"],
    "wifi":       [r"\bwifi\b", r"\bwireless\b"],
    "varifocal":  [r"\bvarifocal\b"],
    "fixed":      [r"\bfixed\b"],
    "dome":       [r"\bdome\b"],
    "bullet":     [r"\bbullet\b"],
    "turret":     [r"\bturret\b"],
    "indoor":     [r"\bindoor\b"],
    "outdoor":    [r"\boutdoor\b", r"\bip66\b", r"\bip67\b", r"\bweather\s*proof\b"],
    "night-vision":[r"\bnight\s*vision\b", r"\bday\s*\/?\s*night\b"],
}

TOKEN_VARIANTS: Dict[str, List[str]] = {
    "poe": ["poe", "poe+"],
    "poe+": ["poe+", "802.3at"],
    "ir-30m": ["ir 30m", "ir-30m", "infrared 30m", "infrared 30 m", "exir 30m"],
    "ir-60m": ["ir 60m", "ir-60m", "infrared 60m", "infrared 60 m", "exir 60m"],
    "outdoor": ["outdoor", "ip66", "ip67", "weatherproof"],
    "indoor": ["indoor"],
    "vandal": ["vandal", "ik10"],
    "audio": ["audio", "microphone"],
    "4k": ["4k", "uhd"],
    "1080p": ["1080p", "full hd", "fhd"],
}

# ------------------------------ Vague camera flag -----------------------------

def _is_vague_camera_request(text: str, it: Dict[str, Any]) -> bool:
    """
    Vague if it asks for a camera but provides no concrete constraints:
    - no SKU
    - family == camera
    - no formFactor, no location, and no feature tokens
    """
    t = (text or "").lower()
    mentions_camera = any(w in t for w in ["camera", "cameras", "dome", "bullet", "turret", "ptz"])
    if not mentions_camera:
        return False
    if (it.get("sku") or "").strip():
        return False
    if (it.get("family") or "").lower() != "camera":
        return False
    if it.get("formFactor") or it.get("location"):
        return False
    feats = it.get("features") or []
    return len(feats) == 0

# ------------------------------ Helpers ---------------------------------------

def _norm_feature_token(raw: str) -> Optional[str]:
    if not raw:
        return None
    s = raw.strip().lower()
    m = IR_RE.search(s)
    if m:
        return f"ir-{m.group(1)}m"
    for canon, pats in FEATURE_ALIASES.items():
        for pat in pats:
            if re.search(pat, s, flags=re.I):
                return canon
    s = re.sub(r"[^a-z0-9\-\+]", "", s)
    return s or None

def normalize_features(features: List[str] | None) -> List[str]:
    out: List[str] = []
    for f in features or []:
        t = _norm_feature_token(f)
        if t and t not in out:
            out.append(t)
    return out

def expand_variants(tokens: List[str]) -> List[str]:
    out: List[str] = []
    for t in tokens:
        out.extend(TOKEN_VARIANTS.get(t, [t]))
    seen, uniq = set(), []
    for v in (x.lower() for x in out):
        if v not in seen:
            seen.add(v); uniq.append(v)
    return uniq

# ------------------------------ Heuristic parser ------------------------------

WORDS_TO_NUM = {"one":1,"two":2,"three":3,"four":4,"five":5,"six":6,"seven":7,"eight":8,"nine":9,"ten":10}

def _guess_family(text: str) -> Optional[str]:
    t = text.lower()
    if any(w in t for w in ["camera","cameras","dome","bullet","turret","ptz","sensor unit"]): return "camera"
    if "nvr" in t or "recorder" in t: return "nvr"
    if "switch" in t and "poe" in t: return "switch"
    if "mount" in t or "bracket" in t: return "mount"
    if "hdd" in t or "ssd" in t or "storage" in t: return "storage"
    if "cable" in t or "cat6" in t: return "cable"
    if "monitor" in t or "display" in t: return "monitor"
    return None

def _extract_budget(text: str) -> Optional[Dict[str, Any]]:
    m = MONEY_RE.search(text); 
    if not m: return None
    amt = float(m.group(1)); cur = (m.group(2) or "").upper() or "USD"
    return {"amount": amt, "currency": cur}

def _extract_brands(text: str) -> Tuple[List[str], List[str]]:
    prefs = [b.lower() for b in BRAND_RE.findall(text)]
    avoids: List[str] = []
    for m in AVOID_RE.finditer(text):
        avoids.append(m.group(2).lower())
    return sorted(set(prefs)), sorted(set(avoids))

def _extract_qty(text: str) -> int:
    t = text.lower()
    for w,n in WORDS_TO_NUM.items():
        if re.search(rf"\b{w}\b", t): return n
    m = QTY_PAIR.search(t)
    if m:
        try: return max(1, int(m.group(1)))
        except Exception: pass
    return 1

def _extract_skus(text: str) -> List[str]:
    skus = set()
    for m in EAN_RE.finditer(text): skus.add(m.group(1))
    for m in UPC_RE.finditer(text): skus.add(m.group(1))
    for m in SKU_RE.finditer(text): skus.add(m.group(0))
    return list(skus)

def heuristic_intent(user_text: str) -> Dict[str, Any]:
    t = user_text.strip()
    qty = _extract_qty(t)
    budget = _extract_budget(t)
    prefs, avoids = _extract_brands(t)
    family = _guess_family(t) or "other"

    feats: List[str] = []
    for canon, pats in FEATURE_ALIASES.items():
        for pat in pats:
            if re.search(pat, t, flags=re.I):
                feats.append(canon); break
    for m in IR_RE.finditer(t):
        feats.append(f"ir-{m.group(1)}m")
    feats = normalize_features(feats)

    skus = _extract_skus(t)
    items: List[Dict[str, Any]] = []

    if skus:
        for s in skus:
            it = {
                "quantity": qty,
                "sku": s,
                "family": family,
                "formFactor": None,
                "location": "outdoor" if "outdoor" in t.lower() else ("indoor" if "indoor" in t.lower() else None),
                "features": feats,
                "brandPreference": prefs,
                "brandAvoid": avoids,
                "budgetPerUnit": budget,
            }
            ch = re.search(r"\b(\d{1,3})\s*chan(nel)?s?\b", t, re.I)
            pr = re.search(r"\b(\d{1,3})\s*port(s)?\b", t, re.I)
            if (it.get("family") or "").lower() == "nvr" and ch:
                it["requiredChannels"] = int(ch.group(1))
            if (it.get("family") or "").lower() == "switch" and pr:
                it["requiredPorts"] = int(pr.group(1))
            it["prepared_filters"] = {
                "tokens": [],
                "expanded_tokens": [],
                "max_price": (it.get("budgetPerUnit") or {}).get("amount"),
                "brand_preference": it.get("brandPreference") or [],
                "brand_avoid": it.get("brandAvoid") or [],
            }
            it["vague"] = _is_vague_camera_request(t, it)
            items.append(it)
    else:
        it = {
            "quantity": qty,
            "sku": None,
            "family": family,
            "formFactor": ("dome" if "dome" in t.lower() else
                           "bullet" if "bullet" in t.lower() else
                           "ptz" if "ptz" in t.lower() else None),
            "location": "outdoor" if "outdoor" in t.lower() else ("indoor" if "indoor" in t.lower() else None),
            "features": feats,
            "brandPreference": prefs,
            "brandAvoid": avoids,
            "budgetPerUnit": budget,
        }
        ch = re.search(r"\b(\d{1,3})\s*chan(nel)?s?\b", t, re.I)
        pr = re.search(r"\b(\d{1,3})\s*port(s)?\b", t, re.I)
        if (it.get("family") or "").lower() == "nvr" and ch:
            it["requiredChannels"] = int(ch.group(1))
        if (it.get("family") or "").lower() == "switch" and pr:
            it["requiredPorts"] = int(pr.group(1))
        tokens: List[str] = []
        for k in ("formFactor","location"):
            v = (it.get(k) or "").strip().lower()
            if v and v != "any":
                tokens.append(v)
        tokens.extend(it.get("features") or [])
        it["prepared_filters"] = {
            "tokens": tokens,
            "expanded_tokens": expand_variants(tokens),
            "max_price": (it.get("budgetPerUnit") or {}).get("amount"),
            "brand_preference": it.get("brandPreference") or [],
            "brand_avoid": it.get("brandAvoid") or [],
        }
        it["vague"] = _is_vague_camera_request(t, it)
        items.append(it)

    g: Dict[str, Any] = {}
    ch = re.search(r"\b(\d{1,3})\s*chan(nel)?s?\b", t, re.I)
    if ch: g["nvrChannels"] = int(ch.group(1))
    pr = re.search(r"\b(\d{1,3})\s*port(s)?\b", t, re.I)
    if pr: g["switchPorts"] = int(pr.group(1))
    if "avoid ptz" in t.lower(): g["avoidPtz"] = True

    return {"items": items, "global": g}

# ---------------------------- OpenAI extractor -------------------------------

SYSTEM_PROMPT = """You extract procurement intents for CCTV products and related accessories.

Return a JSON object with:
- items[]: for each requested line item
  - quantity: integer >=1 (default 1 if not stated)
  - sku: exact string if provided (model/SKU/EAN/UPC), else null
  - family: free-form category (e.g., camera, nvr, server, switch, mount, storage, cable, monitor, other)
  - formFactor: free-form (e.g., dome, bullet, ptz, turret, mini-dome, box, any)
  - location: free-form (indoor, outdoor, any)
  - features[]: normalized tokens (poe, poe+, ir-30m, ir-60m, vandal, audio, h265, h264, 4k, 1080p, 720p, wifi, varifocal, fixed, night-vision)
  - brandPreference[]: lowercase strings mentioned as preferred brands
  - brandAvoid[]: lowercase strings to avoid (e.g., ptz, axis, hanwha)
  - budgetPerUnit: {amount:number, currency:string} if a per-unit cap is stated
- global: optional system requirements (nvrChannels, switchPorts, storageNeeds, avoidPtz, notes)

Rules:
- Prefer precision over guessing. If not stated, leave fields null/omitted.
- Copy exact SKUs/EANs/UPCs as given.
- Do not invent unavailable info.
"""

TOOLS = [{
    "type": "function",
    "function": {
        "name": "intent",
        "description": "Normalized purchase intent for CCTV queries (flexible, no enums).",
        "parameters": {
            "type": "object",
            "properties": {
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "quantity": {"type": "integer", "minimum": 1},
                            "sku": {"type": "string"},
                            "family": {"type": "string"},
                            "formFactor": {"type": "string"},
                            "location": {"type": "string"},
                            "features": {"type": "array", "items": {"type": "string"}},
                            "brandPreference": {"type": "array", "items": {"type": "string"}},
                            "brandAvoid": {"type": "array", "items": {"type": "string"}},
                            "budgetPerUnit": {
                                "type": "object",
                                "properties": {
                                    "amount": {"type": "number"},
                                    "currency": {"type": "string"}
                                }
                            }
                        },
                        "required": ["quantity"]
                    }
                },
                "global": {
                    "type": "object",
                    "properties": {
                        "nvrChannels": {"type": "integer"},
                        "switchPorts": {"type": "integer"},
                        "storageNeeds": {"type": "string"},
                        "avoidPtz": {"type": "boolean"},
                        "notes": {"type": "string"}
                    }
                }
            },
            "required": ["items"]
        }
    }
}]

_INTENT_CACHE: Dict[str, Dict[str, Any]] = {}

def _extract_with_openai(user_text: str) -> Dict[str, Any]:
    client = OpenAI(api_key=OPENAI_API_KEY)  # type: ignore
    resp = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[{"role":"system","content":SYSTEM_PROMPT},
                  {"role":"user","content":user_text}],
        tools=TOOLS,
        tool_choice={"type":"function","function":{"name":"intent"}},
        temperature=0.0,
        top_p=1.0,
        presence_penalty=0,
        frequency_penalty=0,
    )
    tool_calls = resp.choices[0].message.tool_calls or []
    raw = {}
    if tool_calls and tool_calls[0].function.name == "intent":
        raw = json.loads(tool_calls[0].function.arguments)

    items: List[Dict[str, Any]] = []
    for it in (raw.get("items") or [{"quantity":1}]):
        it = dict(it)
        try:
            it["quantity"] = max(1, int(it.get("quantity") or 1))
        except Exception:
            it["quantity"] = 1

        # Normalize lists
        it["features"] = normalize_features(it.get("features") or [])
        it["brandPreference"] = sorted({(v or "").strip().lower() for v in (it.get("brandPreference") or []) if v})
        it["brandAvoid"] = sorted({(v or "").strip().lower() for v in (it.get("brandAvoid") or []) if v})

        # prepared filters
        tokens: List[str] = []
        for k in ("formFactor","location"):
            v = (it.get(k) or "").strip().lower()
            if v and v != "any":
                tokens.append(v)
        tokens.extend(it.get("features") or [])
        it["prepared_filters"] = {
            "tokens": tokens,
            "expanded_tokens": expand_variants(tokens),
            "max_price": (it.get("budgetPerUnit") or {}).get("amount"),
            "brand_preference": it.get("brandPreference"),
            "brand_avoid": it.get("brandAvoid"),
        }
        it["vague"] = _is_vague_camera_request(user_text, it)
        items.append(it)

    g = raw.get("global") or {}
    if isinstance(g.get("avoidPtz"), str):
        g["avoidPtz"] = g["avoidPtz"].strip().lower() in {"true","1","yes","y"}

    return {"items": items, "global": g}

def extract_intent(user_text: str) -> Dict[str, Any]:
    key = user_text.strip().lower()
    if key in _INTENT_CACHE:
        return _INTENT_CACHE[key]

    if OPENAI_API_KEY and OpenAI:
        try:
            result = _extract_with_openai(user_text)
            _INTENT_CACHE[key] = result
            return result
        except Exception:
            pass

    result = heuristic_intent(user_text)
    _INTENT_CACHE[key] = result
    return result

if __name__ == "__main__":
    samples = [
        "Need 4 outdoor dome cameras with IR 30m and PoE. Add 1 NVR 16 channels and a 24-port PoE switch.",
        "give me a camera",
        "Prefer Axis, avoid PTZ. Budget $900 each. 5 outdoor cameras IR 60m.",
        "One server and 8 cameras, 16-channel recorder, and 24 ports PoE switch",
    ]
    for s in samples:
        print("\nTEXT:", s)
        print(json.dumps(extract_intent(s), indent=2))
