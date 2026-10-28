"""Simple slug helper."""
from __future__ import annotations

import re
import unicodedata


def slugify(value: str, fallback: str = "item") -> str:
    value = (value or "").strip().lower()
    value = unicodedata.normalize("NFKD", value)
    value = value.encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"[^a-z0-9]+", "-", value).strip("-")
    return value or fallback
