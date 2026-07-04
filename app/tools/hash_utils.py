import hashlib
import re


def normalize_jd_text(jd_text: str) -> str:
    """Normalize JD text so identical content with small whitespace changes has one hash."""
    text = jd_text.strip().lower()
    text = re.sub(r"\s+", " ", text)
    return text


def compute_jd_hash(jd_text: str) -> str:
    return hashlib.sha256(normalize_jd_text(jd_text).encode("utf-8")).hexdigest()
