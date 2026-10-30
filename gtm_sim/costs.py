"""Estimate Tenki spend for this project from the workspace's sandbox list.

Rates are Tenki's published sandbox pricing. The SDK exposes no created/terminated
timestamps, so start = timeout_at - workspace max duration (2h cap) and end =
last_activity_at (or now, for live sandboxes). Disk is not billed per second
in the published rates and is left out.

    python -m gtm_sim.costs   # writes results/costs.json
"""

import datetime as dt
import json
import os
import pathlib

from . import remote  # noqa: F401 - loads TENKI_API_KEY from .env

VCPU_SECOND = 0.000014
GIB_SECOND = 0.0000045
MAX_DURATION = dt.timedelta(hours=2)  # workspace cap observed via MAX_DURATION_CAPPED


def main():
    from tenki_sandbox import client
    c = client.Client(api_key=os.environ["TENKI_API_KEY"])
    now = dt.datetime.now(dt.timezone.utc)
    rows = []
    for sb in c.list(include_terminated=True):
        i = sb.info
        start = i.timeout_at - MAX_DURATION
        live = i.state not in ("TERMINATED", "TERMINATING", "FAILED")
        end = now if live else max(i.last_activity_at, start)
        secs = max((end - start).total_seconds(), 0)
        cost = secs * (i.cpu_cores * VCPU_SECOND + i.memory_mb / 1024 * GIB_SECOND)
        rows.append({"id": i.id, "name": i.name, "state": i.state, "live": live, "cpu": i.cpu_cores,
                     "memory_mb": i.memory_mb, "start": start.isoformat(), "seconds": round(secs),
                     "cost_usd": round(cost, 5)})
    rows.sort(key=lambda r: r["start"])
    out = {
        "updated": now.isoformat(),
        "rates": {"vcpu_second": VCPU_SECOND, "gib_second": GIB_SECOND},
        "sandboxes": len(rows),
        "live": sum(r["live"] for r in rows),
        "sandbox_seconds": sum(r["seconds"] for r in rows),
        "total_usd": round(sum(r["cost_usd"] for r in rows), 4),
        "rows": rows,
    }
    pathlib.Path("results").mkdir(exist_ok=True)
    pathlib.Path("results/costs.json").write_text(json.dumps(out, indent=2))
    print(json.dumps({k: v for k, v in out.items() if k != "rows"}, indent=2))


if __name__ == "__main__":
    main()
