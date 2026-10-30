"""Run the simulated buyer inside Tenki sandboxes.

The model lives on the trainer (GPU/MPS); the environment lives in disposable
Tenki VMs. Each call ships the simulator source plus a batch of
(seed, completion) pairs over stdin and gets scored outcomes back as JSON, so
sandboxes need nothing beyond the stock python3 image.
"""

from __future__ import annotations

import json
import os
import pathlib
from concurrent.futures import ThreadPoolExecutor

from . import env

# Pick up TENKI_API_KEY from a gitignored .env at the repo root, if present.
_dotenv = pathlib.Path(__file__).resolve().parent.parent / ".env"
if _dotenv.exists():
    for _line in _dotenv.read_text().splitlines():
        if "=" in _line and not _line.lstrip().startswith("#"):
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip().strip("'\""))

ENV_SRC = pathlib.Path(env.__file__).read_text()

# Runs inside the sandbox: load the simulator module from stdin, score every item.
BOOTSTRAP = r"""
import json, sys, types, random
from dataclasses import asdict
req = json.load(sys.stdin)
m = types.ModuleType("gtm_env"); sys.modules["gtm_env"] = m
exec(compile(req["env_src"], "gtm_env.py", "exec"), m.__dict__)
out = []
for it in req["items"]:
    ep = m.make_episode(it["seed"])
    o = asdict(m.score(ep, it["completion"]))
    if req.get("rollout"):
        o["stage"] = m.rollout(ep, it["completion"], random.Random(it["seed"] * 7919 + it.get("k", 0)))
    out.append(o)
print(json.dumps(out))
"""


def _score_local(items: list[dict], rollout: bool) -> list[dict]:
    import random
    from dataclasses import asdict
    out = []
    for it in items:
        ep = env.make_episode(it["seed"])
        o = asdict(env.score(ep, it["completion"]))
        if rollout:
            o["stage"] = env.rollout(ep, it["completion"], random.Random(it["seed"] * 7919 + it.get("k", 0)))
        out.append(o)
    return out


class Scorer:
    """Scores completions locally or in a pool of Tenki sandboxes."""

    def __init__(self, backend: str = "auto", n_sandboxes: int = 1, cpu: int = 1, memory_mb: int = 1024):
        if backend == "auto":
            backend = "tenki" if os.environ.get("TENKI_API_KEY") else "local"
        self.backend = backend
        self.sandboxes = []
        if backend == "tenki":
            self._spec = {"cpu_cores": cpu, "memory_mb": memory_mb}
            with ThreadPoolExecutor(n_sandboxes) as ex:
                self.sandboxes = list(ex.map(self._new_sandbox, range(n_sandboxes)))
            print(f"[tenki] {len(self.sandboxes)} sandbox(es) up: {[s.id for s in self.sandboxes]}")

    def _new_sandbox(self, i: int):
        from tenki import Sandbox
        # Workspace plans cap max_duration; we ask high and replace sandboxes that expire mid-run.
        return Sandbox.create(api_key=os.environ["TENKI_API_KEY"], name=f"gtm-sim-{i}", max_duration=3 * 3600,
                              allow_outbound=False, tags=["gtm-sim"], **self._spec)

    def _exec(self, sb, req: str) -> list[dict]:
        r = sb.exec("python3", "-c", BOOTSTRAP, input=req, timeout=300)
        if r.exit_code != 0:
            raise RuntimeError(f"sandbox {sb.id} failed: {r.stderr_text[-2000:]}")
        return json.loads(r.stdout_text)

    def _score_remote(self, i: int, items: list[dict], rollout: bool) -> list[dict]:
        req = json.dumps({"env_src": ENV_SRC, "items": items, "rollout": rollout})
        try:
            return self._exec(self.sandboxes[i], req)
        except Exception as e:  # noqa: BLE001 - expired/lost sandbox: replace it once and retry
            print(f"[tenki] sandbox {self.sandboxes[i].id} failed ({type(e).__name__}); replacing", flush=True)
            try:
                self.sandboxes[i].terminate()
            except Exception:  # noqa: BLE001
                pass
            self.sandboxes[i] = self._new_sandbox(i)
            return self._exec(self.sandboxes[i], req)

    def score(self, items: list[dict], rollout: bool = False) -> list[dict]:
        if self.backend == "local" or not items:
            return _score_local(items, rollout)
        n = len(self.sandboxes)
        shards = [items[i::n] for i in range(n)]
        with ThreadPoolExecutor(n) as ex:
            results = list(ex.map(lambda i: self._score_remote(i, shards[i], rollout), range(n)))
        # Re-interleave shard results back into input order.
        out = [None] * len(items)
        for i, res in enumerate(results):
            for j, o in enumerate(res):
                out[i + j * n] = o
        return out

    def close(self):
        for sb in self.sandboxes:
            try:
                sb.terminate()
            except Exception as e:  # noqa: BLE001 - best-effort cleanup
                print(f"[tenki] terminate {sb.id} failed: {e}")
        self.sandboxes = []

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
