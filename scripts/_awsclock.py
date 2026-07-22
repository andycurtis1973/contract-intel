"""Clock-skew correction for live AWS calls (shared by the live scripts).

The sandbox clock drifts (runs slow), enough to blow past AWS's SigV4 signature
window — and it keeps drifting *during* a run, so a fixed offset captured once
goes stale. Fix: anchor to AWS's server time once (from a probe's Date header, or
the skew error), then advance with a MONOTONIC counter (time.perf_counter tracks
real elapsed time regardless of wall-clock drift). botocore 1.4x signs via
get_current_datetime(); we replace it process-wide. A near-no-op in a real
deployment (NTP-correct clock); not used inside Lambda.
"""

from __future__ import annotations

import datetime as _dt
import re
import time as _time
from email.utils import parsedate_to_datetime


def _patch(server_now: _dt.datetime) -> None:
    import botocore.auth
    import botocore.utils

    anchor_perf = _time.perf_counter()

    def _now():
        # server_now + real-elapsed-since-anchor (monotonic, drift-proof).
        return server_now + _dt.timedelta(seconds=_time.perf_counter() - anchor_perf)

    botocore.utils.get_current_datetime = _now
    botocore.auth.get_current_datetime = _now


def ensure_clock_synced(region: str = "us-east-1") -> _dt.timedelta:
    """Anchor botocore's signing clock to AWS server time. Returns the offset
    (server - local) for reporting; ~0 when the clock is already correct."""
    import boto3
    from botocore.config import Config
    from botocore.exceptions import ClientError

    sts = boto3.client(
        "sts", region_name=region,
        config=Config(retries={"mode": "standard", "total_max_attempts": 5}),
    )
    try:
        resp = sts.get_caller_identity()
        server_now = parsedate_to_datetime(resp["ResponseMetadata"]["HTTPHeaders"]["date"])
    except ClientError as e:
        times = re.findall(r"\d{8}T\d{6}Z", str(e))
        if "ignature" not in str(e) or not times:
            raise
        server_now = max(_dt.datetime.strptime(t, "%Y%m%dT%H%M%SZ") for t in times)
        server_now = server_now.replace(tzinfo=_dt.timezone.utc)

    if server_now.tzinfo is None:
        server_now = server_now.replace(tzinfo=_dt.timezone.utc)
    offset = server_now - _dt.datetime.now(_dt.timezone.utc)
    _patch(server_now)
    return offset
