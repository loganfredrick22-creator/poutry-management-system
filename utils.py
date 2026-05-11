from __future__ import annotations

from datetime import date, datetime
from typing import Any, Optional


def today() -> date:
    return date.today()


def parse_date(s: str) -> Optional[date]:
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        return None


def fmt_date(d: Optional[date]) -> str:
    return d.strftime("%Y-%m-%d") if d else ""


def safe_float(x: Any, default: Optional[float] = 0.0) -> Optional[float]:
    try:
        if x is None or x == "":
            return default
        return float(x)
    except Exception:
        return default


def clamp_int(x: float, lo: int, hi: int) -> int:
    return int(max(lo, min(hi, round(float(x)))))


def age_days(hatch_date: Optional[date]) -> Optional[int]:
    if not hatch_date:
        return None
    return max(0, (today() - hatch_date).days)


def age_group(days: Optional[int]) -> str:
    if days is None:
        return "Unknown"
    if days < 30:
        return "Chick (0-29d)"
    if days < 90:
        return "Grower (30-89d)"
    if days < 180:
        return "Juvenile (90-179d)"
    return "Adult (180d+)"

