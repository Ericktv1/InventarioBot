import re, unicodedata

def strip_think(text: str) -> str:
    if not text: return ""
    cleaned = re.sub(r"<think>.*?</think>\s*", "", text, flags=re.DOTALL|re.IGNORECASE).strip()
    if cleaned: return cleaned
    m = re.search(r"</think>\s*(.*)$", text, flags=re.DOTALL|re.IGNORECASE)
    if m and m.group(1).strip(): return m.group(1).strip()
    return re.sub(r"</?think>", "", text, flags=re.IGNORECASE).strip()

def _norm(s: str) -> str:
    if not s: return ""
    s = unicodedata.normalize("NFD", s)
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    return " ".join(s.lower().strip().split())

_NUM_WORDS = {"uno":1, "una":1, "un":1, "dos":2, "tres":3, "cuatro":4, "cinco":5, "seis":6,
              "siete":7, "ocho":8, "nueve":9, "diez":10, "par":2, "par de":2}

def to_qty(token: str, default: int = 1) -> int:
    t = _norm(token)
    if t.startswith("x") and t[1:].isdigit(): return max(1, int(t[1:]))
    if t.endswith("x") and t[:-1].isdigit(): return max(1, int(t[:-1]))
    n = "".join(ch for ch in t if ch.isdigit())
    if n.isdigit(): return max(1, int(n))
    for k, v in _NUM_WORDS.items():
        if t.startswith(k): return v
    return default
