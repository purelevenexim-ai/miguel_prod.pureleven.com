"""
Address Parser v3 — Production-grade WhatsApp / freeform text → structured address.

FLOW:
  INPUT TEXT → Normalize → Extract Phones → Extract Pincode → Detect Country
  → Fetch State/City/District from India Post API → Extract Name → Build Address Body
  → Validation Checks → Confidence Score → Return ParsedAddress

HANDLES:
  ✅ Indian WhatsApp addresses (multi-line, messy formatting)
  ✅ "Pin - 682023", "PIN CODE: 682023", "683 102"
  ✅ "Mob: 9847836398", "+91 98478 36398", "0091-9847836398"
  ✅ Names: "Moni T K.", "KUNHI MUHAMMAD . P", "Saira Banu.TP", "Mrs Falocy D'sa"
  ✅ Foreign phone numbers → auto-detect, flag for review
  ✅ Foreign addresses → country ≠ India, employee review required
  ✅ Pincode > 6 digits → flagged for employee review
  ✅ Phone < 10 digits → flagged for employee review
  ✅ India Post pincode API → auto-fill State, District, Region

Trained on 30+ real PureLeven Exim orders from Kerala, Gujarat, Goa, Delhi, etc.
"""
from __future__ import annotations

import re
import logging
from dataclasses import dataclass, field
from typing import Optional

try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────

INDIA_POST_API = "https://api.postalpincode.in/pincode/{pincode}"
PINCODE_CACHE: dict[str, dict | None] = {}   # in-memory cache per process

# Indian States
STATES = [
    "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh",
    "Goa", "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand", "Karnataka",
    "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya", "Mizoram",
    "Nagaland", "Odisha", "Punjab", "Rajasthan", "Sikkim", "Tamil Nadu",
    "Telangana", "Tripura", "Uttar Pradesh", "Uttarakhand", "West Bengal",
    "Delhi", "Jammu and Kashmir", "Ladakh", "Chandigarh", "Puducherry",
    "Dadra and Nagar Haveli", "Daman and Diu", "Andaman and Nicobar Islands",
    "Lakshadweep",
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
    "kerala": "Kerala", "karnataka": "Karnataka", "tamil nadu": "Tamil Nadu",
    "maharashtra": "Maharashtra", "gujarat": "Gujarat", "rajasthan": "Rajasthan",
    "goa": "Goa", "delhi": "Delhi", "punjab": "Punjab", "haryana": "Haryana",
    "bihar": "Bihar", "odisha": "Odisha", "assam": "Assam",
    "west bengal": "West Bengal", "telangana": "Telangana",
    "andhra pradesh": "Andhra Pradesh", "madhya pradesh": "Madhya Pradesh",
    "uttar pradesh": "Uttar Pradesh", "uttarakhand": "Uttarakhand",
    "himachal pradesh": "Himachal Pradesh", "jharkhand": "Jharkhand",
    "chhattisgarh": "Chhattisgarh", "chandigarh": "Chandigarh",
}

# Foreign country keywords
FOREIGN_COUNTRIES = {
    "usa", "united states", "america", "uk", "united kingdom", "england",
    "canada", "australia", "uae", "dubai", "abu dhabi", "sharjah",
    "qatar", "doha", "oman", "muscat", "bahrain", "kuwait", "saudi",
    "saudi arabia", "singapore", "malaysia", "germany", "france",
    "italy", "spain", "netherlands", "switzerland", "sweden", "norway",
    "japan", "south korea", "china", "hong kong", "new zealand",
    "ireland", "scotland", "sri lanka", "bangladesh", "nepal", "pakistan",
    "thailand", "indonesia", "philippines", "vietnam", "south africa",
    "kenya", "nigeria", "egypt", "brazil", "mexico", "argentina",
}

# International phone country codes (prefix → country)
COUNTRY_CODES = {
    "1": "USA/Canada", "44": "UK", "971": "UAE", "61": "Australia",
    "65": "Singapore", "60": "Malaysia", "49": "Germany", "33": "France",
    "39": "Italy", "34": "Spain", "81": "Japan", "82": "South Korea",
    "86": "China", "64": "New Zealand", "353": "Ireland",
    "94": "Sri Lanka", "880": "Bangladesh", "977": "Nepal",
    "92": "Pakistan", "966": "Saudi Arabia", "974": "Qatar",
    "968": "Oman", "973": "Bahrain", "965": "Kuwait",
    "66": "Thailand", "62": "Indonesia", "63": "Philippines",
    "27": "South Africa", "254": "Kenya", "234": "Nigeria",
    "55": "Brazil", "52": "Mexico",
}

# Known Indian city / district names
KNOWN_CITIES = {
    "mumbai", "delhi", "bangalore", "bengaluru", "chennai", "kolkata",
    "hyderabad", "ahmedabad", "pune", "jaipur", "lucknow", "kanpur",
    "nagpur", "indore", "thane", "bhopal", "visakhapatnam", "vadodara",
    "surat", "ludhiana", "agra", "varanasi", "patna", "nashik", "meerut",
    "rajkot", "amritsar", "allahabad", "howrah", "coimbatore", "madurai",
    "gwalior", "vijayawada", "jodhpur", "raipur", "kota", "chandigarh",
    "guwahati", "thiruvananthapuram", "trivandrum", "kochi", "ernakulam",
    "kozhikode", "calicut", "thrissur", "trichur", "kollam", "palakkad",
    "palghat", "malappuram", "kannur", "cannanore", "kasaragod", "idukki",
    "wayanad", "alappuzha", "alleppey", "pathanamthitta", "kottayam",
    "noida", "gurgaon", "gurugram", "faridabad", "ghaziabad",
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
    "margao", "panjim", "mapusa", "vasco",
    "kayamkulam", "karunagappally", "haripad", "mavelikara",
    "kazhakuttam", "attingal", "neyyattinkara", "nedumangad",
    # Common international cities (for informational context only)
    "london", "new york", "toronto", "sydney", "dubai", "singapore",
    "bangkok", "hong kong", "tokyo", "paris", "berlin", "amsterdam",
}


# ─────────────────────────────────────────────────────────────
# Result Dataclass
# ─────────────────────────────────────────────────────────────

@dataclass
class ParsedAddress:
    confidence: str = "low"          # "high" | "medium" | "low"
    needs_manual: bool = True

    # Core fields
    name: Optional[str] = None
    name2: Optional[str] = None      # company name or C/O
    phone: Optional[str] = None      # normalized: +919847836398
    phone_display: Optional[str] = None  # display: 98478 36398
    phone2: Optional[str] = None
    address_line: Optional[str] = None
    city: Optional[str] = None
    district: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    country: str = "India"

    # Flags
    is_international: bool = False
    phone_is_foreign: bool = False
    pincode_needs_review: bool = False
    phone_needs_review: bool = False

    raw: str = ""
    warnings: list[str] = field(default_factory=list)


# ─────────────────────────────────────────────────────────────
# Regexes
# ─────────────────────────────────────────────────────────────

# ── PHONE ─────────────────────────────────────────────────────
# Indian mobile: 10 digits starting 6-9, with optional +91/91/0/0091 prefix
# [^\S\n] = whitespace but NOT newline (prevents cross-line matching)
RE_INDIAN_PHONE = re.compile(
    r'(?:(?:mob(?:ile)?|ph(?:one)?|call|whatsapp|contact|cell|tel)[^\S\n]*[:\-]?[^\S\n]*)?'
    r'(?:(?:00)?(?:\+?91)[^\S\n\-]?|0)?'
    r'([6-9]\d[^\S\n\-]?\d{4}[^\S\n\-]?\d{4})',
    re.IGNORECASE
)

# Suspicious phone patterns: 11-15 digits (might be typo, extra digit, or misformatted)
RE_SUSPICIOUS_PHONE = re.compile(
    r'(?:(?:mob(?:ile)?|ph(?:one)?|call|whatsapp|contact|cell|tel)[^\S\n]*[:\-]?[^\S\n]*)?'
    r'(?:(?:00)?(?:\+?91)[^\S\n\-]?|0)?'
    r'([6-9]\d[\d\s\-]{9,15}\d)',  # 11-17 total digits: starts with 6-9, has 11+ digits total
    re.IGNORECASE
)

# International phone: starts with + followed by country code + number
# Prefer 1-3 digit country codes; disallow 4+ digits unless they're clearly NOT a phone
RE_INTL_PHONE = re.compile(
    r'(?:(?:mob(?:ile)?|ph(?:one)?|call|whatsapp|contact|cell|tel)[^\S\n]*[:\-]?[^\S\n]*)?'
    r'\+(\d{1,3})[^\S\n\-]?(\d[\d\s\-]{5,14}\d)',
    re.IGNORECASE
)

# Detects +<non-91 digits> pattern to identify international prefixes
RE_INTL_PREFIX = re.compile(r'\+(?!91[\s\-]?[6-9])\d{1,4}[\s\-]?\d')

# Phone-only line (for stripping from address body)
RE_PHONE_LINE = re.compile(
    r'^\s*(?:mob(?:ile)?|ph(?:one)?|call|whatsapp|contact|cell|tel)\s*[:\-]?\s*'
    r'(?:00)?(?:\+?91)?[^\S\n\-]?[6-9]\d[^\S\n\-]?\d{4}[^\S\n\-]?\d{4}\s*$',
    re.IGNORECASE
)
RE_BARE_PHONE_LINE = re.compile(
    r'^\s*(?:00)?(?:\+?91)?[^\S\n\-]?[6-9]\d[^\S\n\-]?\d{4}[^\S\n\-]?\d{4}\s*$'
)

# ── PINCODE ───────────────────────────────────────────────────
# Labeled: "Pin - 682023", "PIN CODE: 682023", "Pincode 682023"
RE_PINCODE_LABELED = re.compile(
    r'(?:pin\s*(?:code)?\s*[:\-\u2013\u2014.\s]\s*)([1-9]\d{2}\s?\d{3})\b',
    re.IGNORECASE
)
# Bare 6-digit (with optional space: "683 102")
RE_PINCODE_BARE = re.compile(r'\b([1-9]\d{2}\s?\d{3})\b')

# Entire line is a pincode
RE_PINCODE_LINE = re.compile(
    r'^\s*(?:pin\s*(?:code)?\s*[:\-\u2013\u2014.\s]\s*)?([1-9]\d{2}\s?\d{3})\s*$',
    re.IGNORECASE
)

# ── NAME ──────────────────────────────────────────────────────
RE_NAME_LINE = re.compile(
    r'^(?:name|customer|to|recipient|attn|c/?o|care of)[:\s]*(.+)$',
    re.IGNORECASE | re.MULTILINE
)

# Address keywords → NOT a name
RE_ADDRESS_KEYWORDS = re.compile(
    r'(?:'
    r'\d{6}|\d{10}|@|http|www\.'
    r'|(?:^|\s)(?:house|ho|flat|floor|plot|apt|apartment|block|sector|lane|'
    r'road|rd|street|st|nagar|colony|layout|marg|cross|main|near|opp|opposite|'
    r'behind|beside|next\s*to|above|below|south|north|east|west|'
    r'ward|div|division|mandal|taluk|tehsil|tahsil|dist|dt|district|'
    r'post|po|p\.o|pin|pincode|mob|mobile|ph|phone|whatsapp|'
    r'order|address|email|state|city|village|rs\.|total|amount|rupee|\u20b9|'
    r'park|garden|gardens|arcade|junction|complex|tower|towers|avenue|'
    r'building|bldg|enclave|residency|society|flats|heights|'
    r'bus\s*stop|railway|station|temple|church|mosque|masjid|school|college|'
    r'hospital|market|bazaar|chowk|square|circle|gate|no\.'
    r')'
    r'(?:\s|$|[.,;:\-)])'
    r')',
    re.IGNORECASE
)


# ─────────────────────────────────────────────────────────────
# Phone Helpers
# ─────────────────────────────────────────────────────────────

def _normalize_indian_phone(raw: str) -> tuple[str | None, bool]:
    """
    Extract 10 digits from an Indian mobile number.
    Returns: (normalized_10_digits, needs_review)
    - needs_review=True if digits were truncated or number is malformed
    """
    digits = re.sub(r'\D', '', raw)
    
    # Exact 10-digit number
    if len(digits) == 10:
        return (digits, False)
    
    # +91 prefix (12 digits total)
    if len(digits) == 12 and digits.startswith('91'):
        return (digits[2:], False)
    
    # 0091 prefix (14 digits total)
    if len(digits) == 14 and digits.startswith('0091'):
        return (digits[4:], False)
    
    # 0 prefix (11 digits total, India standard)
    if len(digits) == 11 and digits.startswith('0'):
        return (digits[1:], False)
    
    # 11+ digit numbers: ambiguous, flag for review
    if len(digits) >= 11:
        # Return raw as-is with review flag
        return (digits, True)
    
    # Less than 10 digits: also flag for review
    if len(digits) > 0:
        return (digits, True)
    
    # No digits found
    return (None, False)


def _format_phone_display(ten_digits: str) -> str:
    """Format as: 98478 36398"""
    if len(ten_digits) == 10:
        return f"{ten_digits[:5]} {ten_digits[5:]}"
    return ten_digits


def _format_phone_stored(ten_digits: str) -> str:
    """Format as: +919847836398"""
    return f"+91{ten_digits}"


def _find_indian_phones(text: str) -> tuple[list[str], list[tuple[str, str]]]:
    """
    Find all valid Indian mobile numbers + suspicious patterns.
    Returns: (valid_10digit_list, suspicious_list)
    
    suspicious_list = [(raw_number, reason), ...]
      - reason: "11 digits (ambiguous)", etc.
    """
    # First, find spans of international phone numbers to exclude
    intl_spans = []
    for m in RE_INTL_PHONE.finditer(text):
        cc = m.group(1)
        if cc != "91":  # non-Indian international
            intl_spans.append((m.start(), m.end()))

    valid_phones = []
    suspicious_phones = []
    seen_valid = set()
    seen_suspicious = set()
    
    # Look for all digit sequences that could be phones (6+ digits)
    # This will catch both valid 10-digit and suspicious 11+ digit patterns
    digit_pattern = re.compile(
        r'(?:(?:mob(?:ile)?|ph(?:one)?|call|whatsapp|contact|cell|tel)[^\S\n]*[:\-]?[^\S\n]*)?'
        r'(?:(?:00)?(?:\+?91)[^\S\n\-]?|0)?'
        r'([\d\s\-]{6,})',  # 6+ chars (digits, spaces, hyphens)
        re.IGNORECASE
    )
    
    for m in digit_pattern.finditer(text):
        # Skip if this match overlaps with an international phone
        overlaps = any(s <= m.start() < e or s < m.end() <= e for s, e in intl_spans)
        if overlaps:
            continue
        
        raw = m.group(1)
        digits_only = re.sub(r'\D', '', raw)
        
        # Skip pincodes (6 digits starting with 1-9)
        if len(digits_only) == 6 and digits_only[0] in '123456789':
            continue
        
        # Valid: exactly 10 digits starting with 6-9
        if len(digits_only) == 10 and digits_only[0] in '6789':
            if digits_only not in seen_valid:
                seen_valid.add(digits_only)
                valid_phones.append(digits_only)
        
        # Suspicious: 11-15 digits or other odd lengths
        elif 6 <= len(digits_only) <= 15 and digits_only[0] in '6789' and digits_only not in seen_valid:
            if digits_only not in seen_suspicious:
                seen_suspicious.add(digits_only)
                reason = f"{len(digits_only)} digits"
                if len(digits_only) < 10:
                    reason += " (too short)"
                elif len(digits_only) > 10:
                    reason += " (too long — unclear if phone, pincode, or typo)"
                suspicious_phones.append((digits_only, reason))
    
    return (valid_phones, suspicious_phones)


def _find_international_phone(text: str) -> Optional[tuple[str, str, str]]:
    """
    Find international (non-India) phone.
    Returns: (full_number, country_code, country_name) or None.
    Only returns if country code is recognized in COUNTRY_CODES.
    """
    for m in RE_INTL_PHONE.finditer(text):
        cc = m.group(1)
        number = re.sub(r'\D', '', m.group(2))
        if cc == "91":
            continue  # That's India, skip
        
        # Validate country code — must be in COUNTRY_CODES or a valid prefix
        country = COUNTRY_CODES.get(cc, None)
        if not country:
            # Try shorter prefixes
            for code_len in [2, 1]:
                sub = cc[:code_len]
                if sub in COUNTRY_CODES:
                    country = COUNTRY_CODES[sub]
                    cc = sub  # Use the validated shorter code
                    break
        
        # If we still don't have a valid country, skip this match
        if not country:
            continue
        
        full = f"+{cc}{number}"
        return (full, cc, country)
    
    return None


# ─────────────────────────────────────────────────────────────
# Pincode Helpers
# ─────────────────────────────────────────────────────────────

def _find_pincode(text: str, indian_phones: list[str]) -> tuple[Optional[str], bool]:
    """
    Find pincode. Returns (pincode, needs_review).
    - Exactly 6 digits → valid Indian pincode
    - >6 or <6 digits (found via label) → needs_review = True
    """
    # Try labeled first
    m = RE_PINCODE_LABELED.search(text)
    if m:
        pin = m.group(1).replace(' ', '')
        return (pin, len(pin) != 6)

    # Try bare 6-digit
    matches = RE_PINCODE_BARE.findall(text)
    if matches:
        phone_digits = set(indian_phones)
        for pm in RE_INDIAN_PHONE.finditer(text):
            phone_digits.add(re.sub(r'\D', '', pm.group(0)))

        for candidate in matches:
            norm = candidate.replace(' ', '')
            if len(norm) != 6:
                continue
            is_phone = any(norm in pd for pd in phone_digits)
            if not is_phone:
                return (norm, False)

    return (None, False)


def _is_pincode_line(line: str, pincode: Optional[str] = None) -> bool:
    """Check if a line is just a pincode."""
    if RE_PINCODE_LINE.match(line):
        return True
    if pincode and pincode in line.replace(' ', ''):
        cleaned = RE_PINCODE_LABELED.sub('', line).strip()
        cleaned = RE_PINCODE_BARE.sub('', cleaned).strip()
        cleaned = re.sub(r'(?:pin\s*(?:code)?\s*[:\-\u2013\u2014.\s]*)', '', cleaned, flags=re.IGNORECASE).strip()
        cleaned = cleaned.strip(',.:;\u2013\u2014- ')
        if len(cleaned) < 3:
            return True
    return False


def _is_phone_line(line: str) -> bool:
    """Check if a line is just a phone number."""
    return bool(RE_PHONE_LINE.match(line)) or bool(RE_BARE_PHONE_LINE.match(line.strip()))


# ─────────────────────────────────────────────────────────────
# India Post Pincode API Lookup
# ─────────────────────────────────────────────────────────────

def _lookup_pincode(pincode: str) -> Optional[dict]:
    """
    Query India Post API for state, district, region from pincode.
    Returns dict with state/district/region/post_office/country or None.
    Uses in-memory cache.
    """
    if not pincode or len(pincode) != 6:
        return None

    if pincode in PINCODE_CACHE:
        return PINCODE_CACHE[pincode]

    if not HAS_HTTPX:
        logger.warning("httpx not installed — skipping pincode API lookup")
        return None

    try:
        url = INDIA_POST_API.format(pincode=pincode)
        resp = httpx.get(url, timeout=5.0)
        data = resp.json()

        if data and isinstance(data, list) and data[0].get("Status") == "Success":
            offices = data[0].get("PostOffice", [])
            if offices:
                first = offices[0]
                result = {
                    "state": first.get("State"),
                    "district": first.get("District"),
                    "region": first.get("Region"),
                    "post_office": first.get("Name"),
                    "country": first.get("Country", "India"),
                }
                PINCODE_CACHE[pincode] = result
                return result

        PINCODE_CACHE[pincode] = None
        return None

    except Exception as e:
        logger.warning(f"Pincode API error for {pincode}: {e}")
        return None


# ─────────────────────────────────────────────────────────────
# State Detection (fallback when API unavailable)
# ─────────────────────────────────────────────────────────────

def _find_state_from_text(text: str) -> Optional[str]:
    text_lower = text.lower()
    for s in STATES:
        if len(s) > 3 and s.lower() in text_lower:
            return STATE_NORM.get(s.lower(), s)
    for abbr, full in STATE_NORM.items():
        if len(abbr) == 2 and re.search(r'\b' + re.escape(abbr) + r'\b', text_lower):
            return full
    return None


# ─────────────────────────────────────────────────────────────
# Country Detection
# ─────────────────────────────────────────────────────────────

def _detect_country(text: str) -> Optional[str]:
    """Detect foreign country keywords in text."""
    text_lower = text.lower()
    for country in FOREIGN_COUNTRIES:
        if re.search(r'\b' + re.escape(country) + r'\b', text_lower):
            return country.title()
    return None


# ─────────────────────────────────────────────────────────────
# Name Detection
# ─────────────────────────────────────────────────────────────

def _is_name_line(line: str) -> bool:
    """
    Does this line look like a person's name?
    Handles: "Moni T K.", "KUNHI MUHAMMAD . P", "Saira Banu.TP",
             "Mrs Falocy D'sa", "Salini Krishnakumar"
    """
    stripped = line.strip()
    if not stripped or len(stripped) < 2:
        return False

    clean = re.sub(r'[\.\,]+$', '', stripped).strip()
    if not clean:
        return False

    if RE_ADDRESS_KEYWORDS.search(stripped):
        return False

    if re.search(r'\d{3}', clean):
        return False

    if re.search(r'[#/\\]', clean):
        return False

    # Normalize dots: "K.George" → "K George"
    name_clean = re.sub(r'\.(?=[A-Za-z])', ' ', clean)
    name_clean = re.sub(r'\.', '', name_clean)
    name_clean = re.sub(r'\s+', ' ', name_clean).strip()
    words = name_clean.split()

    if not (1 <= len(words) <= 6):
        return False

    for w in words:
        alpha = re.sub(r"['\u2019\-]", '', w)
        if not alpha:
            continue
        if not alpha.isalpha():
            return False

    first = re.sub(r"['\u2019\-]", '', words[0])
    if first and not (first[0].isupper() or first.isupper()):
        return False

    return True


# ─────────────────────────────────────────────────────────────
# Address Body Builder
# ─────────────────────────────────────────────────────────────

def _strip_phone_from_line(line: str) -> str:
    """Remove phone numbers and labels from a line."""
    cleaned = re.sub(
        r'(?:[\-\u2013\u2014]+\s*)?(?:mob(?:ile)?|ph(?:one)?|call|whatsapp|contact|cell|tel)\s*[:\-]?\s*'
        r'(?:00)?(?:\+?91)?[\s\-]?[6-9]\d[\s\-]?\d{4}[\s\-]?\d{4}',
        '', line, flags=re.IGNORECASE
    ).strip()
    cleaned = re.sub(
        r'[\-\u2013\u2014]+\s*(?:00)?(?:\+?91)?[\s\-]?[6-9]\d{9}\s*$',
        '', cleaned
    ).strip()
    cleaned = re.sub(r'\s+(?:00)?(?:\+?91)?[\s\-]?[6-9]\d{9}\s*$', '', cleaned).strip()
    return cleaned


def _build_address_line(
    lines: list[str],
    skip_indices: set[int],
    pincode: Optional[str] = None,
    state: Optional[str] = None,
    phones: list[str] = None,
) -> Optional[str]:
    """Build address body from lines not already consumed."""
    parts = []
    state_lower = state.lower() if state else None
    phone_set = set(phones or [])

    for i, raw in enumerate(lines):
        line = raw.strip()
        if not line or i in skip_indices:
            continue
        if _is_pincode_line(line, pincode):
            continue
        if _is_phone_line(line):
            continue
        if state_lower and line.lower().strip().rstrip('.') == state_lower:
            continue

        cleaned = _strip_phone_from_line(line)

        if pincode and pincode in cleaned:
            cleaned = cleaned.replace(pincode, '').strip()
            cleaned = re.sub(r'pin\s*(?:code)?\s*[:\-\u2013\u2014.\s]*', '', cleaned, flags=re.IGNORECASE).strip()
            cleaned = cleaned.strip(',.:;\u2013\u2014- ')

        for ph in phone_set:
            cleaned = cleaned.replace(ph, '').strip()

        cleaned = cleaned.strip(',.:;\u2013\u2014- "\'')

        if cleaned and len(cleaned) >= 2:
            parts.append(cleaned)

    return ", ".join(parts) if parts else None


# ─────────────────────────────────────────────────────────────
# City Extraction
# ─────────────────────────────────────────────────────────────

def _find_city(
    lines: list[str],
    used_indices: set[int],
    pincode: Optional[str],
    name: Optional[str],
    api_data: Optional[dict],
) -> Optional[str]:
    """
    Multi-strategy city detection:
      1. India Post API region/district
      2. Known cities in text
      3. Line before pincode
      4. Inline "Mumbai 400053"
    """
    # 1. From API
    if api_data:
        region = api_data.get("region")
        district = api_data.get("district")
        if region and region.lower() in KNOWN_CITIES:
            return region
        if district:
            return district

    # 2. Known city in lines
    for i, line in enumerate(lines):
        if i in used_indices:
            continue
        line_lower = line.lower().strip().rstrip(',.')
        if line_lower in KNOWN_CITIES:
            return line.strip().rstrip(',.')
        for city in KNOWN_CITIES:
            if city in line_lower:
                idx = line_lower.find(city)
                return line[idx:idx + len(city)].strip()

    # 3. Line before pincode
    if pincode:
        for i, line in enumerate(lines):
            if _is_pincode_line(line, pincode) and i > 0:
                prev = lines[i - 1].strip()
                if prev and i - 1 not in used_indices and prev != name:
                    words = prev.split()
                    if 1 <= len(words) <= 4 and not any(c.isdigit() for c in prev):
                        return prev.rstrip(',.')
                break

    # 4. Inline on pincode line
    if pincode:
        for line in lines:
            if pincode in line.replace(' ', ''):
                city_part = line.replace(pincode, '').strip()
                city_part = re.sub(r'pin\s*(?:code)?\s*[:\-\u2013\u2014.\s]*', '', city_part, flags=re.IGNORECASE).strip()
                city_part = city_part.strip(',.:;\u2013\u2014- ')
                if city_part and len(city_part) >= 3 and not re.search(r'\d', city_part):
                    if city_part != name and city_part.lower() not in ['pin', 'pincode', 'code']:
                        return city_part
                break

    return None


# ═════════════════════════════════════════════════════════════
# MAIN PARSE FUNCTION
# ═════════════════════════════════════════════════════════════

def parse_address(raw_text: str) -> ParsedAddress:
    result = ParsedAddress(raw=raw_text)

    if not raw_text or not raw_text.strip():
        result.warnings.append("Empty input")
        return result

    # ── Normalize ─────────────────────────────────────────────
    text = raw_text.strip()
    text = re.sub(r'\r\n|\r', '\n', text)
    text = re.sub(r'[,;|/]{2,}', '\n', text)
    text = re.sub(r'\t+', '\n', text)
    lines = [l.strip() for l in text.split('\n') if l.strip()]

    used_indices: set[int] = set()
    score = 0

    # ═════════════════════════════════════════════════════════
    # STEP 1 — PHONE EXTRACTION
    # ═════════════════════════════════════════════════════════
    indian_phones, suspicious_phones = _find_indian_phones(text)
    intl_phone = _find_international_phone(text)

    if indian_phones:
        ten = indian_phones[0]
        result.phone = _format_phone_stored(ten)           # +919847836398
        result.phone_display = _format_phone_display(ten)  # 98478 36398
        score += 2

        if len(indian_phones) >= 2:
            result.phone2 = _format_phone_stored(indian_phones[1])

        for i, line in enumerate(lines):
            if _is_phone_line(line):
                used_indices.add(i)
        
        # If we also found suspicious phones, add warning
        if suspicious_phones:
            reason_list = [f"{num} ({reason})" for num, reason in suspicious_phones]
            result.warnings.append(
                f"Found suspicious phone numbers (not used): {', '.join(reason_list[:2])} "
                f"— verify if these are phones or other data"
            )

    elif suspicious_phones:
        # No valid phones found, but found suspicious ones
        # Flag for employee review
        first_phone, reason = suspicious_phones[0]
        result.phone = first_phone
        result.phone_needs_review = True
        result.needs_manual = True
        score += 1
        result.warnings.append(
            f"Phone number {first_phone} has {reason} — unclear if phone, pincode, or other data. "
            f"Please verify manually."
        )
        
        for i, line in enumerate(lines):
            if _is_phone_line(line):
                used_indices.add(i)

    elif intl_phone:
        full, cc, country_name = intl_phone
        result.phone = full
        result.phone_display = full
        result.phone_is_foreign = True
        result.is_international = True
        result.country = country_name
        result.needs_manual = True
        result.warnings.append(f"Foreign phone detected ({country_name}) — employee review required")
        score += 1

        for i, line in enumerate(lines):
            if _is_phone_line(line):
                used_indices.add(i)
    else:
        # Check for short/malformed numbers (phone-like digit sequences)
        # Exclude pincode (6 digits, starts with 1-9) and known phone numbers
        digit_lines = []
        existing_phones = set(indian_phones) if indian_phones else set()
        
        for line in lines:
            if re.match(r'^\s*\+?\d[\d\s\-]{3,}\d\s*$', line):
                raw_digits = re.sub(r'\D', '', line)
                # Skip if it's a pincode (6 digits 1-9xxx)
                if len(raw_digits) == 6 and raw_digits[0] in '123456789':
                    continue
                # Skip if it's a known phone we already extracted
                if raw_digits in existing_phones:
                    continue
                digit_lines.append((line, raw_digits))
        
        if digit_lines:
            line, raw_digits = digit_lines[0]
            if len(raw_digits) < 10:

                result.phone = line.strip()
                result.phone_needs_review = True
                result.needs_manual = True
                result.warnings.append(f"Phone has {len(raw_digits)} digits (less than 10) — needs review")
            elif len(raw_digits) > 13:
                result.phone = line.strip()
                result.phone_needs_review = True
                result.needs_manual = True
                result.warnings.append(f"Phone has {len(raw_digits)} digits (unusually long) — needs review")
        else:
            result.warnings.append("No phone number found")

    # ═════════════════════════════════════════════════════════
    # STEP 2 — PINCODE EXTRACTION
    # ═════════════════════════════════════════════════════════
    pincode, pin_needs_review = _find_pincode(text, indian_phones)
    if pincode:
        result.pincode = pincode
        if pin_needs_review:
            result.pincode_needs_review = True
            result.needs_manual = True
            result.warnings.append(
                f"Pincode '{pincode}' has {len(pincode)} digits "
                f"(expected 6 for India) — employee review required"
            )
            score += 1
        else:
            score += 2

        for i, line in enumerate(lines):
            if _is_pincode_line(line, pincode):
                used_indices.add(i)
    else:
        result.warnings.append("No pincode found")

    # ═════════════════════════════════════════════════════════
    # STEP 3 — COUNTRY DETECTION
    # ═════════════════════════════════════════════════════════
    foreign_country = _detect_country(text)
    if foreign_country:
        result.country = foreign_country
        result.is_international = True
        result.needs_manual = True
        result.warnings.append(f"International address detected ({foreign_country}) — employee review required")
        score += 1

    # ═════════════════════════════════════════════════════════
    # STEP 4 — STATE & DISTRICT FROM PINCODE (India Post API)
    # ═════════════════════════════════════════════════════════
    api_data = None
    if pincode and len(pincode) == 6 and not result.is_international:
        api_data = _lookup_pincode(pincode)
        if api_data:
            result.state = api_data.get("state")
            result.district = api_data.get("district")
            result.country = api_data.get("country", "India")
            score += 2  # API confirmed = high trust
        else:
            # API failed or invalid pin — fall back to text
            result.state = _find_state_from_text(text)
            if result.state:
                score += 1
            result.warnings.append("Pincode not found in India Post database — may be invalid")
            result.pincode_needs_review = True
            result.needs_manual = True
    elif not result.is_international:
        # Only do text-based state detection for India addresses
        state = _find_state_from_text(text)
        if state:
            result.state = state
            score += 1

    # ═════════════════════════════════════════════════════════
    # STEP 5 — NAME EXTRACTION
    # ═════════════════════════════════════════════════════════
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
        # First line that looks like a name (WhatsApp = name on line 1)
        for i, line in enumerate(lines):
            if i in used_indices:
                continue
            if _is_name_line(line):
                result.name = line.strip()
                used_indices.add(i)
                score += 2

                # Check next line for C/O or company
                if i + 1 < len(lines) and i + 1 not in used_indices:
                    next_line = lines[i + 1].strip()
                    if re.match(r'^(?:c/?o|care\s*of)[:\s]', next_line, re.IGNORECASE):
                        result.name2 = next_line
                        used_indices.add(i + 1)
                break

        if not result.name:
            if lines and not RE_ADDRESS_KEYWORDS.search(lines[0]) and len(lines[0].split()) <= 5:
                first = re.sub(r'[\.\,]+$', '', lines[0]).strip()
                if first and not re.search(r'\d{3}', first):
                    result.name = lines[0].strip()
                    used_indices.add(0)
                    score += 1
                    result.warnings.append("Name detection uncertain — employee should verify")
                else:
                    result.warnings.append("Could not detect customer name")
            else:
                result.warnings.append("Could not detect customer name")

    # ═════════════════════════════════════════════════════════
    # STEP 6 — CITY EXTRACTION
    # ═════════════════════════════════════════════════════════
    city = _find_city(lines, used_indices, pincode, result.name, api_data)
    if city:
        result.city = city
        score += 1

    # ═════════════════════════════════════════════════════════
    # STEP 7 — BUILD ADDRESS BODY
    # ═════════════════════════════════════════════════════════
    addr = _build_address_line(
        lines, used_indices,
        pincode=pincode, state=result.state, phones=indian_phones,
    )
    if addr:
        result.address_line = addr
        score += 1
    else:
        result.warnings.append("Could not extract address lines")

    # ═════════════════════════════════════════════════════════
    # STEP 8 — VALIDATION & CONFIDENCE
    # ═════════════════════════════════════════════════════════

    # Cross-checks
    if result.phone_is_foreign and result.pincode and len(result.pincode) == 6 and not result.is_international:
        result.warnings.append("Foreign phone with Indian pincode — please verify country")

    if result.address_line and len(result.address_line) < 15:
        result.warnings.append("Address is very short — may be incomplete")

    # Confidence scoring
    if result.is_international:
        result.confidence = "medium" if score >= 4 else "low"
        result.needs_manual = True
    elif score >= 5:
        result.confidence = "high"
        result.needs_manual = False
    elif score >= 3:
        result.confidence = "medium"
        result.needs_manual = True
    else:
        result.confidence = "low"
        result.needs_manual = True
        result.warnings.append("Low confidence — please verify all fields manually")

    # Override: any review flag forces manual
    if result.pincode_needs_review or result.phone_needs_review:
        result.needs_manual = True

    return result


# ─────────────────────────────────────────────────────────────
# API-facing dict wrapper
# ─────────────────────────────────────────────────────────────

def parse_address_dict(raw_text: str) -> dict:
    """Return parsed address as plain dict for the REST API."""
    p = parse_address(raw_text)
    return {
        "confidence": p.confidence,
        "needs_manual": p.needs_manual,

        "name": p.name,
        "name2": p.name2,
        "phone": p.phone,
        "phone_display": p.phone_display,
        "phone2": p.phone2,
        "address_line": p.address_line,
        "city": p.city,
        "district": p.district,
        "state": p.state,
        "pincode": p.pincode,
        "country": p.country,

        "is_international": p.is_international,
        "phone_is_foreign": p.phone_is_foreign,
        "pincode_needs_review": p.pincode_needs_review,
        "phone_needs_review": p.phone_needs_review,

        "warnings": p.warnings,
    }
