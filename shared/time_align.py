from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone


def now_utc() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def next_boundary_utc(interval_sec: int, skew_sec: int = 3) -> datetime:
    """
    Next UTC wall-clock boundary for the given interval.
    Example: 900 sec (15m) -> 00/15/30/45.
    skew_sec delays a few seconds after the boundary so feeds print.
    """
    t = now_utc()
    epoch = int(t.timestamp())
    next_epoch = ((epoch // interval_sec) + 1) * interval_sec + skew_sec
    return datetime.fromtimestamp(next_epoch, tz=timezone.utc)


def sleep_until(target_utc: datetime):
    while True:
        delta = (target_utc - now_utc()).total_seconds()
        if delta <= 0:
            break
        time.sleep(min(1.0, delta))


