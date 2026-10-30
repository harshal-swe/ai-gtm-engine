"""Package held-out GTM Gym prospects as Harbor tasks.

Each task gives the agent one prospect dossier and asks for the JSON action in
/app/action.json; the verifier runs the simulated buyer (tests/env.py, hidden
from the agent) and writes the reward. solution/solve.sh is a rule-based oracle
built from the hidden ground truth, so `--agent oracle` shows the ceiling.

    python -m gtm_sim.harbor_tasks --n 30 --out harbor/tasks
"""

import argparse
import json
import pathlib
import shutil

from . import env

DOCKERFILE = "FROM public.ecr.aws/docker/library/python:3.12-slim\nWORKDIR /app\n"

TEST_SH = """#!/bin/bash
mkdir -p /logs/verifier
python3 /tests/grade.py
"""

GRADE_PY = """import json, pathlib, sys
sys.path.insert(0, "/tests")
import env
SEED = {seed}
ep = env.make_episode(SEED)
p = pathlib.Path("/app/action.json")
text = p.read_text() if p.exists() else ""
o = env.score(ep, text)
out = pathlib.Path("/logs/verifier")
out.mkdir(parents=True, exist_ok=True)
(out / "reward.txt").write_text(str(round(o.reward, 4)))
(out / "rewards.json").write_text(json.dumps({{
    "reward": round(o.reward, 4), "reply_prob": round(o.reply_prob, 4),
    "meeting_prob": round(o.meeting_prob, 4), "decision_correct": int(o.decision_correct),
    "valid": int(o.valid)}}))
print(json.dumps({{"reward": o.reward, "features": o.features}}))
"""

TASK_TOML = """schema_version = "1.4"
artifacts = []

[task]
name = "gtmgym/prospect-{seed}"
version = "1.0.0"
description = "GTM Gym: qualify one B2B prospect and draft a first-touch message"
authors = []
keywords = ["gtm", "sales", "simulation"]

[metadata]

[verifier]
timeout_sec = 120.0
collect = []

[verifier.env]

[agent]
timeout_sec = 300.0

[environment]
network_mode = "public"
build_timeout_sec = 300.0
os = "linux"
mcp_servers = []

[environment.env]

[solution.env]
"""


def instruction(ep: env.Episode) -> str:
    return (f"{env.SYSTEM_PROMPT}\n\nProspect ID: {ep.seed}\n\n{env.user_prompt(ep)}\n\n"
            "Write ONLY the JSON object to /app/action.json. Do not ask questions; this task is non-interactive.\n")


def oracle_action(ep: env.Episode) -> dict:
    """A rule-based ideal answer built from the hidden ground truth."""
    truth = env.icp_truth(ep)
    if not ep.should_pursue():
        return {"icp_check": truth, "decision": "disqualify", "tier": "C", "channel": "email",
                "subject": "", "message": ""}
    pr, persona = ep.prospect, ep.persona()
    first = pr.contact_name.split()[0]
    signal = pr.signals[0].rstrip(".") if pr.signals else f"{pr.company} is growing"
    keyword = env.POSITIVE_SIGNALS[pr.signal_keys[0]][1][0] if pr.signal_keys else ""
    tone = " ".join(env.TONE_WORDS[persona["tone"]][:2])
    vp = ep.product["value_props"][persona["pain"]]
    msg = (f"Hi {first}, saw that {signal[0].lower() + signal[1:]}{' (' + keyword + ')' if keyword else ''}. "
           f"{ep.product['name']} helps teams like {pr.company} {vp}, with a {tone} focus. "
           "Open to a quick chat next week?")
    return {"icp_check": truth, "decision": "pursue", "tier": ep.true_tier(), "channel": persona["channel"],
            "subject": f"{pr.company} and {ep.product['name']}", "message": msg}


def write_task(ep: env.Episode, root: pathlib.Path):
    d = root / f"prospect-{ep.seed}"
    if d.exists():
        shutil.rmtree(d)
    (d / "environment").mkdir(parents=True)
    (d / "tests").mkdir()
    (d / "solution").mkdir()
    (d / "task.toml").write_text(TASK_TOML.format(seed=ep.seed))
    (d / "instruction.md").write_text(instruction(ep))
    (d / "environment" / "Dockerfile").write_text(DOCKERFILE)
    (d / "tests" / "test.sh").write_text(TEST_SH)
    (d / "tests" / "grade.py").write_text(GRADE_PY.format(seed=ep.seed))
    shutil.copy(env.__file__, d / "tests" / "env.py")
    action = json.dumps(oracle_action(ep))
    (d / "solution" / "solve.sh").write_text(f"#!/bin/bash\ncat > /app/action.json <<'JSON'\n{action}\nJSON\n")
    for f in ("tests/test.sh", "solution/solve.sh"):
        (d / f).chmod(0o755)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=30)
    ap.add_argument("--out", default="harbor/tasks")
    args = ap.parse_args()
    root = pathlib.Path(args.out)
    root.mkdir(parents=True, exist_ok=True)
    eps = env.make_split(args.n, env.EVAL_SEED)  # the same held-out prospects as the main eval
    for ep in eps:
        write_task(ep, root)
    print(f"wrote {len(eps)} tasks to {root}")


if __name__ == "__main__":
    main()
