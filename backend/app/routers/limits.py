"""
Prop AI - shared rate-limit helpers for routers (chat and booking).

Each limited endpoint has two limits: per visitor (IP), which stops one
person flooding, and per site, which caps the damage from many IPs.
"""

from dataclasses import dataclass
from math import ceil

from fastapi import HTTPException, Request

from app.services.rate_limit import SlidingWindowLimiter


@dataclass(frozen=True)
class RateLimits:
    per_visitor: SlidingWindowLimiter  # keyed by IP
    per_site: SlidingWindowLimiter  # one key for everyone


def wait_text(seconds: int) -> str:
    """'40 seconds', '37 minutes', '3 hours': rounded up, so waiting that long always works."""
    if seconds < 60:
        amount, unit = seconds, "second"
    elif seconds <= 60 * 60:
        amount, unit = ceil(seconds / 60), "minute"
    else:
        amount, unit = ceil(seconds / 3600), "hour"
    return f"{amount} {unit}{'' if amount == 1 else 's'}"


def enforce(limits: RateLimits, request: Request, too_fast: str, site_full: str) -> None:
    """Raise 429 if either limit is used up. `too_fast` may contain {wait}.

    Per-visitor first: a flooder's blocked requests then never count toward
    the site's cap, so one person can't use it up for everyone.
    Behind a hosting proxy, request.client is the proxy unless uvicorn runs
    with --proxy-headers (set at deploy time).
    """
    visitor = request.client.host if request.client else "unknown"
    wait = limits.per_visitor.hit(visitor)
    if wait is not None:
        raise _too_many(too_fast, wait)
    wait = limits.per_site.hit("site")
    if wait is not None:
        raise _too_many(site_full, wait)


def _too_many(detail: str, wait: float) -> HTTPException:
    seconds = max(1, ceil(wait))
    return HTTPException(status_code=429, detail=detail.format(wait=wait_text(seconds)),
                         headers={"Retry-After": str(seconds)})
