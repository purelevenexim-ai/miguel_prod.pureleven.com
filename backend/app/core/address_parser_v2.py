"""
Address Parser v2 — WhatsApp / freeform text → structured address fields.

Strategy:
- Apply regex patterns for phone, pincode, state, name
- Confidence levels: high / medium / low
- If confidence is low → do NOT retry, return raw text + flag for manual entry
- Optimized for Indian addresses pasted from WhatsApp chats

Trained on 30+ real orders from PureLeven Exim dataset covering patterns:
  - Multi-line WhatsApp pastes (name on line 1, address lines, pincode, phone)
  - "Pin - 682023", "PIN CODE: 682023", "PIN:682023"
  - "Mob: 9847836398", "Ph: 98...", "Mobile: 98..."
  - Names with dots/periods: "Moni T K.", "KUNHI MUHAMMAD . P", "Saira Banu.TP"
  - ALL-CAPS names, mixed-case, single-word names
  - Parenthetical POs: "Edavattom po", "(po)", "(P.O)"
  - Inline comma-separated: "House, Street, City, State PIN"
"""
from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import Optional


# ─────────────────────────────────────────────────────────────
# Indian States & Common District Lookups
# ─────────────────────────────────────────────────────────────

STATES = [
    "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh",
    "Goa", "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand", "Karnataka",
    "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya", "Mizoram",
    "Nagaland", "Odisha", "Punjab", "Rajasthan", "Sikkim", "Tamil Nadu",
    "Telangana", "Tripura", "Uttar Pradesh", "Uttarakhand", "West Bengal",
    # UTs
    "Delhi", "Jammu and Kashmir", "Ladakh", "Chandigarh", "Puducherry",
    "Dadra and Nagar Haveli", "Daman and Diu", "Andaman and Nicobar Islands",
    "Lakshadweep",
    # Abbreviations often seen in WhatsApp
    "AP", "MP", "UP", "WB", "TN", "HP", "J&K",
]

STATE_NORM = {
    "ap": "Andhra Pradesh", "mp": "Madhya Pradesh", "up": "Uttar Pradesh",
    "wb": "West Bengal", "tn": "Tamil Nadu", "hp": "Himachal Pradesh",
    "jk": "Jammu and Kashmir", "j&k": "Jammu and Kashmir",
    "uk": "Uttarakhand", "ka": "Karnataka", "mh": "Maharashtra",
    "gj": "Gujarat", "rj": "Rajasthan", "pb": "Punjab", "hr": "Haryana",
    "br": "Bihar", "jh": "Jharkhand", "or": "Odisha", "od": "Odisha",
    "cg": "Chhattisgarh", "as": "Assam", "kl": "Kerala", "ga": "Goa",
    "dl": "Delhi", "py": "Puducherry", "tg": "Telangana", "ts": "Telangana",
}

# Known Indian city / district names for extraction boost
KNOWN_CITIES = {
    "mumbai", "delhi", "bangalore", "bengaluru", "chennai", "kolkata",
    "hyderabad", "ahmedabad", "pune", "jaipur", "lucknow", "kanpur",
    "nagpur", "indore", "thane", "bhopal", "visakhapatnam", "vadodara",
    "surat", "ludhiana", "agra", "varanasi", "patna", "nashik", "meerut",
    "rajkot", "amritsar", "allahabad", "howrah", "coimbatore", "madurai",
    "gwalior", "vijayawada", "jodhpur", "raipur", "kota", "chandigarh",
    "guwahati", "thiruvananthapuram", "trivandrum", "kochi", "ernakulam",
    "kozhikode", "calicut", "thrissur", "trichur", "kollam", "palakkad",
    "palghad", "malappuram", "kannur", "cannanore", "kasaragod", "idukki",
    "wayanad", "alappuzha", "alleppey", "pathanamthitta", "kottayam",
    "noida", "gurgaon", "gurugram", "faridabad", "ghaziabad", "rohini",
    "dwarka", "andheri", "bandra", "dadar", "borivali", "powai",
    "navi mumbai", "kalyan", "dombivli",
    "mangalore", "mysore", "mysuru", "hubli", "dharwad", "belgaum", "belagavi",
    "salem", "tirunelveli", "tiruchirappalli", "trichy", "vellore",
    "aurangabad", "solapur", "kolhapur", "sangli", "satara",
    "bhilai", "ranchi", "dhanbad", "jamshedpur", "bokaro",
    "tirur", "perinthalmanna", "manjeri", "nilambur", "ponnani",
    "vadakara", "thalassery", "payyanur", "sultan bathery", "mananthavady",
    "chengannur", "thiruvalla", "adoor", "ranni", "konni",
    "angamaly", "aluva", "perumbavoor", "muvattupuzha", "thodupuzha",
    "bharuch", "vapi", "navsari", "anand", "nadiad", "dahod",
    "bhavnagar", "junagadh", "jamnagar", "gandhidham", "morbi",
}

# ─────────────────────────────────────────────────────────────
# Result Dataclass
# ─────────────────────────────────────────────────────────────

@dataclass
class ParsedAddress:
    confidence: str = "low"
    needs_manual: bool = True

    name: Optional[str] = None
    name2: Optional[str] = None
    phone: Optional[str] = None
    phone2: Optional[str] = None
    address_line: Optional[str] = None
    city: Optional[str] = None
    district: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    country: str = "India"

    raw: str = ""
    warnings: list[str] = field(default_factory=list)


# ─────────────────────────────────────────────────────────────
# Regexes
# ─────────────────────────────────────────────────────────────

# Phone: 10-digit Indian numbers with optional +91/91/0 prefix
# Also captures phones prefixed with "Mob:", "Ph:", "Mobile:", etc.
RE_PHONE = re.compile(
    r'(?:(?:mob(?:ile)?|ph(?:one)?|call|whatsapp|contact|cell|tel)\s*[:\-]?\s*)?'
    r'(?:(?:\+91|91|0)?[\s\-]?)?'
    r'([6-9]\d[\s\-]?\d{4}[\s\-]?\d{4})',
    re.IGNORECASE
)

# Pincode: 6-digit Indian PIN with optional prefix labels
RE_PINCODE_LABELED = re.compile(
    r'(?:pin\s*(?:code)?\s*[:\-\u2013\u2014.\s]\s*)([1-9]\d{5})\b',
    re.IGNORECASE
)
RE_PINCODE_BARE = re.compile(r'\b([1-9]\d{5})\b')

# Phone line — entire line is primarily a phone number
RE_PHONE_LINE = re.compile(
    r'^\s*(?:mob(?:ile)?|ph(?:one)?|call|whatsapp|contact|cell|tel)\s*[:\-]?\s*'
    r'(?:\+?91[\s\-]?)?[6-9]\d[\s\-]?\d{4}[\s\-]?\d{4}\s*$',
    re.IGNORECASE
)

# Bare phone-only line (just digits, maybe with prefix)
RE_BARE_PHONE_LINE = re.compile(
    r'^\s*(?:\+?91[\s\-]?)?[6-9]\d[\s\-]?\d{4}[\s\-]?\d{4}\s*$'
)

# Pincode line — entire line is primarily a pincode
RE_PINCODE_LINE = re.compile(
    r'^\s*(?:pin\s*(?:code)?\s*[:\-\u2013\u2014.\s]\s*)?([1-9]\d{5})\s*$',
    re.IGNORECASE
)

# Labeled name line
RE_NAME_LINE = re.compile(
    r'^(?:name|customer|to|recipient|attn|c/?o|care of)[:\s]*(.+)$',
    re.IGNORECASE | re.MULTILINE
)

# Address keywords that disqualify a line from being a name
RE_ADDRESS_KEYWORDS = re.compile(
    r'(?:'
    r'\d{6}|\d{10}|@|http|www\.'
    r'|(?:^|\s)(?:house|ho|flat|floor|plot|apt|apartment|block|sector|lane|'
    r'road|rd|street|st|nagar|colony|layout|marg|cross|main|near|opp|opposite|'
    r'behind|beside|next\s*to|above|below|front|back|south|north|east|west|'
    r'ward|div|division|mandal|taluk|tehsil|tahsil|dist|dt|district|'
    r'post|po|p\.o|pin|pincode|mob|mobile|ph|phone|whatsapp|'
    r'order|address|email|state|city|village|rs\.|total|amount|rupee|\u20b9|'
    r'park|garden|gardens|arcade|junction|complex|tower|towers|avenue|'
    r'building|bldg|enclave|residency|society|flats|heights|'
    r'bus\s*stop|railway|station|temple|church|mosque|masjid|school|college|'
    r'hospital|market|bazaar|chowk|square|circle|gate|no\.|'
    r'vattom|kadavu|paramb|kunnu|thodi|mukku|padi|para|'
    r'puram|abad|ganj|pur|wadi|wada|peth|palli|oor|ur|'
    r'pallam|kandath|veettil|peedik|mukk|paramba)'
    r'(?:\s|$|[.,;:\-)])'
    r')',
    re.IGNORECASE
)


def _clean_phone(raw: str) -> str:
    """Normalize to 10-digit Indian number."""
    digits = re.sub(r'\D', '', raw)
    if len(digits) == 12 and digits.startswith('91'):
        return digits[2:]
    if len(digits) == 11 and digits.startswith('0'):
        return digits[1:]
    return digits[-10:] if len(digits) >= 10 else digits


def _find_state(text: str) -> Optional[str]:
    text_lower = text.lower()
    # Try full state names first (longer = more reliable)
    for s in STATES:
        if len(s) > 3 and s.lower() in text_lower:
            return STATE_NORM.get(s.lower(), s)
    # Try abbreviations (word boundary)
    for abbr, full in STATE_NORM.items():
        if len(abbr) >= 2 and re.search(r'\b' + re.escape(abbr) + r'\b', text_lower):
            return full
    return None


def _find_pincode(text: str) -> Optional[str]:
    """
    Find 6-digit Indian PIN code.
    Priority: labeled ("Pin - 682023") > bare ("682023").
    Excludes 6-digit substrings that are part of a 10-digit phone.
    """
    m = RE_PINCODE_LABELED.search(text)
    if m:
        return m.group(1)

    matches = RE_PINCODE_BARE.findall(text)
    if not matches:
        return None

    # Collect phone digit strings to exclude overlaps
    phone_digits_set = set()
    for pm in RE_PHONE.finditer(text):
        phone_digits_set.add(re.sub(r'\D', '', pm.group(0)))

    for candidate in matches:
        is_phone_part = any(candidate in pd for pd in phone_digits_set)
        if not is_phone_part:
            return candidate

    return matches[0] if matches else None


def _find_phones(text: str) -> list[str]:
    phones = []
    seen = set()
    for m in RE_PHONE.finditer(text):
        cleaned = _clean_phone(m.group(1))
        if len(cleaned) == 10 and cleaned not in seen:
            seen.add(cleaned)
            phones.append(cleaned)
    return phones


def _is_name_line(line: str) -> bool:
    """
    Determine if a line looks like a person's name.
    Handles: "Moni T K.", "KUNHI MUHAMMAD . P", "Saira Banu.TP",
             "Mrs Falocy D'sa", "Salini Krishnakumar", "Raju.K.George"
    """
    stripped = line.strip()
    if not stripped or len(stripped) < 2:
        return False

    # Remove trailing dots/commas for analysis
    clean = re.sub(r'[\.\,]+$', '', stripped).strip()
    if not clean:
        return False

    # If it has address keywords, it's not a name
    if RE_ADDRESS_KEYWORDS.search(stripped):
        return False

    # Contains 3+ consecutive digits → not a name
    if re.search(r'\d{3}', clean):
        return False

    # "T/116" or "#204" patterns → not a name
    if re.search(r'[#/\\]', clean):
        return False

    # Split on whitespace + dots ("Raju.K.George" → "Raju K George")
    name_clean = re.sub(r'\.(?=[A-Za-z])', ' ', clean)   # "K.George" → "K George"
    name_clean = re.sub(r'\.', '', name_clean)             # trailing dots
    name_clean = re.sub(r'\s+', ' ', name_clean).strip()
    words = name_clean.split()

    if not (1 <= len(words) <= 6):
        return False

    # Each word should be primarily alphabetic (allow ', -)
    for w in words:
        alpha_stripped = re.sub(r"['\u2019\-]", '', w)
        if not alpha_stripped:
            continue
        if not alpha_stripped.isalpha():
            return False

    # First real word should start with uppercase or be all-caps
    first_word = words[0]
    first_alpha = re.sub(r"['\u2019\-]", '', first_word)
    if first_alpha and not (first_alpha[0].isupper() or first_alpha.isupper()):
        return False

    return True


def _is_phone_line(line: str) -> bool:
    """Check if an entire line is primarily a phone number."""
    return bool(RE_PHONE_LINE.match(line)) or bool(RE_BARE_PHONE_LINE.match(line.strip()))


def _is_pincode_line(line: str, pincode: Optional[str] = None) -> bool:
    """Check if an entire line is primarily a pincode."""
    if RE_PINCODE_LINE.match(line):
        return True
    if pincode and pincode in line:
        cleaned = RE_PINCODE_LABELED.sub('', line).strip()
        cleaned = RE_PINCODE_BARE.sub('', cleaned).strip()
        cleaned = re.sub(r'(?:pin\s*(?:code)?\s*[:\-\u2013\u2014.\s]*)', '', cleaned, flags=re.IGNORECASE).strip()
        cleaned = cleaned.strip(',.:;\u2013\u2014- ')
        if len(cleaned) < 3:
            return True
    return False


def _strip_phone_from_line(line: str) -> str:
    """Remove phone numbers and their labels from a line."""
    cleaned = re.sub(
        r'(?:[\-\u2013\u2014]+\s*)?(?:mob(?:ile)?|ph(?:one)?|call|whatsapp|contact|cell|tel)\s*[:\-]?\s*'
        r'(?:\+?91[\s\-]?)?[6-9]\d[\s\-]?\d{4}[\s\-]?\d{4}',
        '', line, flags=re.IGNORECASE
    ).strip()
    # Trailing bare phone with separator
    cleaned = re.sub(
        r'[\-\u2013\u2014]+\s*(?:\+?91[\s\-]?)?[6-9]\d{9}\s*$',
        '', cleaned
    ).strip()
    cleaned = re.sub(r'\s+(?:\+?91[\s\-]?)?[6-9]\d{9}\s*$', '', cleaned).strip()
    return cleaned


def _build_address_line(
    lines: list[str],
    skip_indices: set[int],
    pincode: Optional[str] = None,
    state: Optional[str] = None,
    phones: list[str] = None,
) -> Optional[str]:
    """Build address body from lines not already used."""
    addr_parts = []
    state_lower = state.lower() if state else None
    phone_set = set(phones or [])

    for i, raw_line in enumerate(lines):
        line = raw_line.strip()
        if not line or i in skip_indices:
            continue
        if _is_pincode_line(line, pincode):
            continue
        if _is_phone_line(line):
            continue
        if state_lower and line.lower().strip().rstrip('.') == state_lower:
            continue

        cleaned = _strip_phone_from_line(line)

        # Strip inline pincode
        if pincode and pincode in cleaned:
            cleaned = cleaned.replace(pincode, '').strip()
            cleaned = re.sub(r'(?:pin\s*(?:code)?\s*[:\-\u2013\u2014.\s]*)', '', cleaned, flags=re.IGNORECASE).strip()
            cleaned = cleaned.strip(',.:;\u2013\u2014- ')

        # Remove bare phone numbers
        for ph in phone_set:
            cleaned = cleaned.replace(ph, '').strip()

        cleaned = cleaned.strip(',.:;\u2013\u2014- "\'')

        if cleaned and len(cleaned) >= 2:
            addr_parts.append(cleaned)

    return ", ".join(addr_parts) if addr_parts else None


# ─────────────────────────────────────────────────────────────
# Main Parse Function
# ─────────────────────────────────────────────────────────────

def parse_address(raw_text: str) -> ParsedAddress:
    result = ParsedAddress(raw=raw_text)

    if not raw_text or not raw_text.strip():
        result.warnings.append("Empty input")
        return result

    # Normalize
    text = raw_text.strip()
    text = re.sub(r'\r\n|\r', '\n', text)
    text = re.sub(r'[,;|/]{2,}', '\n', text)
    text = re.sub(r'\t+', '\n', text)
    lines = [l.strip() for l in text.split('\n') if l.strip()]

    used_indices: set[int] = set()
    score = 0

    # ── 1. Phone numbers ──────────────────────────────────────
    phones = _find_phones(text)
    if phones:
        result.phone = phones[0]
        score += 2
        if len(phones) >= 2:
            result.phone2 = phones[1]
        for i, line in enumerate(lines):
            if _is_phone_line(line):
                used_indices.add(i)
    else:
        result.warnings.append("No phone number found")

    # ── 2. Pincode ────────────────────────────────────────────
    pincode = _find_pincode(text)
    if pincode:
        result.pincode = pincode
        score += 2
        for i, line in enumerate(lines):
            if _is_pincode_line(line, pincode):
                used_indices.add(i)
    else:
        result.warnings.append("No pincode found")

    # ── 3. State ──────────────────────────────────────────────
    state = _find_state(text)
    if state:
        result.state = state
        score += 1

    # ── 4. Name extraction ────────────────────────────────────
    named_match = RE_NAME_LINE.search(text)
    if named_match:
        result.name = named_match.group(1).strip()
        match_line = named_match.group(0).strip()
        for i, line in enumerate(lines):
            if line.strip() == match_line:
                used_indices.add(i)
                break
        score += 2
    else:
        # Heuristic: first line that looks like a name
        # In WhatsApp pastes, name is almost always line 1
        for i, line in enumerate(lines):
            if i in used_indices:
                continue
            if _is_name_line(line):
                result.name = line.strip()
                used_indices.add(i)
                score += 2
                break

        if not result.name:
            # Fallback: first non-empty line if short and not address-like
            if lines and not RE_ADDRESS_KEYWORDS.search(lines[0]) and len(lines[0].split()) <= 5:
                first_clean = re.sub(r'[\.\,]+$', '', lines[0]).strip()
                if first_clean and not re.search(r'\d{3}', first_clean):
                    result.name = lines[0].strip()
                    used_indices.add(0)
                    score += 1
                    result.warnings.append("Name detection uncertain")
                else:
                    result.warnings.append("Could not detect customer name")
            else:
                result.warnings.append("Could not detect customer name")

    # ── 5. City / District extraction ─────────────────────────
    # a) Known city scan
    for i, line in enumerate(lines):
        if i in used_indices:
            continue
        line_lower = line.lower().strip().rstrip(',.')
        if line_lower in KNOWN_CITIES:
            result.city = line.strip().rstrip(',.')
            break
        for city in KNOWN_CITIES:
            if city in line_lower:
                idx = line_lower.find(city)
                result.city = line[idx:idx + len(city)].strip()
                break
        if result.city:
            break

    # b) Line before pincode
    if not result.city and pincode:
        for i, line in enumerate(lines):
            if _is_pincode_line(line, pincode) and i > 0:
                prev = lines[i - 1].strip()
                if prev and i - 1 not in used_indices and prev != result.name:
                    words = prev.split()
                    if 1 <= len(words) <= 4 and not any(c.isdigit() for c in prev):
                        result.city = prev.rstrip(',.')
                break

    # c) Inline pincode line for city: "Mumbai 400053"
    if not result.city and pincode:
        for line in lines:
            if pincode in line:
                city_part = line.replace(pincode, '').strip()
                city_part = re.sub(r'(?:pin\s*(?:code)?\s*[:\-\u2013\u2014.\s]*)', '', city_part, flags=re.IGNORECASE).strip()
                city_part = city_part.strip(',.:;\u2013\u2014- ')
                if city_part and len(city_part) >= 3 and not re.search(r'\d', city_part):
                    if city_part != result.name and city_part.lower() not in ['pin', 'pincode', 'code']:
                        result.city = city_part
                break

    if result.city:
        score += 1

    # ── 6. Build address body ────────────────────────────────
    addr = _build_address_line(lines, used_indices, pincode=pincode, state=state, phones=phones)
    if addr:
        result.address_line = addr
        score += 1

    # ── 7. Confidence ────────────────────────────────────────
    if score >= 6:
        result.confidence = "high"
        result.needs_manual = False
    elif score >= 4:
        result.confidence = "medium"
        result.needs_manual = True
    else:
        result.confidence = "low"
        result.needs_manual = True
        result.warnings.append("Low confidence \u2014 please verify all fields manually")

    return result


def parse_address_dict(raw_text: str) -> dict:
    """Return as plain dict for API response."""
    p = parse_address(raw_text)
    return {
        "confidence": p.confidence,
        "needs_manual": p.needs_manual,
        "name": p.name,
        "name2": p.name2,
        "phone": p.phone,
        "phone2": p.phone2,
        "address_line": p.address_line,
        "city": p.city,
        "district": p.district,
        "state": p.state,
        "pincode": p.pincode,
        "country": p.country,
        "warnings": p.warnings,
    }
