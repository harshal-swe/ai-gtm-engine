"""Build the GTM Gym dashboard's data files from results/.

    python -m gtm_sim.costs && python -m gtm_sim.dashboard_data   # writes results/dash/*.json
"""

import datetime as dt
import json
import pathlib

R = pathlib.Path("results")
OUT = R / "dash"
TOTAL_STEPS = 50

EVAL_FIELDS = [
    ("qualification_accuracy", "Qualification accuracy", "pct", "up"),
    ("wasted_sends_on_bad_fit", "Wasted sends to bad-fit leads", "int", "down"),
    ("expected_meetings", "Expected meetings booked", "num", "up"),
    ("reply_rate_on_good_fit", "Reply rate on good-fit leads", "pct", "up"),
]
FEATURE_FIELDS = [
    ("has_cta", "Messages with a call to action", "up"),
    ("unsupported_claim", "Messages with made-up figures", "down"),
]


def icp_accuracy(name):
    """Share of ICP-check fields (5 per prospect) the model got right, from saved eval samples."""
    p = R / f"{name}_samples.jsonl"
    if not p.exists():
        return None
    rows = [json.loads(l) for l in p.read_text().splitlines() if l.strip()]
    return sum(r["outcome"]["features"].get("icp_fields_correct", 0) for r in rows) / (5 * len(rows))


def load(name):
    p = R / f"{name}.json"
    return json.loads(p.read_text()) if p.exists() else None


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    base, grpo = load("baseline"), load("grpo")

    # One row per metric, baseline vs trained side by side.
    rows = []
    for key, label, fmt, better in EVAL_FIELDS:
        rows.append({"metric": label, "format": fmt, "better": better,
                     "baseline": base[key] if base else None, "trained": grpo[key] if grpo else None})
    rows.append({"metric": "ICP check accuracy", "format": "pct", "better": "up",
                 "baseline": icp_accuracy("baseline") if base else None,
                 "trained": icp_accuracy("grpo") if grpo else None})
    for key, label, better in FEATURE_FIELDS:
        rows.append({"metric": label, "format": "pct", "better": better,
                     "baseline": base["message_feature_rates"].get(key) if base else None,
                     "trained": grpo["message_feature_rates"].get(key) if grpo else None})
    (OUT / "eval.json").write_text(json.dumps(rows, indent=1))

    funnel = []
    for model, res in (("Base Qwen3-0.6B", base), ("GRPO-trained", grpo)):
        if res:
            for stage, n in res["sampled_funnel"].items():
                funnel.append({"model": model, "stage": stage, "count": n})
    (OUT / "funnel.json").write_text(json.dumps(funnel, indent=1))

    log = [json.loads(l) for l in (R / "train_log.jsonl").read_text().splitlines() if l.strip()] \
        if (R / "train_log.jsonl").exists() else []
    t0 = log[0]["time"] - float(log[0].get("step_time", 0)) if log else None
    train = [{"step": e["step"], "reward": float(e["reward"]), "reward_std": float(e["reward_std"]),
              "frac_reward_zero_std": float(e.get("frac_reward_zero_std", 0)),
              "completion_length": float(e.get("completions/mean_length", 0)),
              "minutes": round((e["time"] - t0) / 60, 2)} for e in log]
    (OUT / "training.json").write_text(json.dumps(train, indent=1))

    costs = json.loads((R / "costs.json").read_text())
    (OUT / "costs.json").write_text(json.dumps([
        {"sandbox": r["id"][-12:], "name": r["name"], "state": r["state"].lower(), "cpu": r["cpu"],
         "memory_gb": r["memory_mb"] / 1024, "seconds": r["seconds"], "cost_usd": r["cost_usd"],
         "started": r["start"]} for r in costs["rows"]], indent=1))

    step = train[-1]["step"] if train else 0
    pace = (train[-1]["minutes"] / step) if step else None
    phase = ("Done" if grpo else "Evaluating trained model" if step >= TOTAL_STEPS
             else "Training" if step else "Starting training")
    # Work items for the team; state follows the run's phase.
    trained, evaluated = (pathlib.Path("runs/grpo/final/adapter_config.json").exists(), grpo is not None)
    plan = [
        ("GTM buyer simulator (products, prospects, personas, reward)", "done"),
        ("Scoring runs in Tenki sandboxes", "done"),
        ("Baseline eval of Qwen3-0.6B", "done" if base else "in progress"),
        ("First GRPO run: messages improved, but it never disqualified a lead", "done"),
        ("Added an ICP check step so the agent learns to skip bad-fit leads", "done"),
        ("GRPO post-training on the Mac (50 steps, done by 2:30pm)", "done" if trained else "in progress"),
        ("Eval of the trained model", "done" if evaluated else "in progress" if trained else "next"),
        ("Export leads and drafts into RelayGTM's dashboard", "next"),
        ("Add a before/after slide to the RelayGTM deck", "next"),
    ]
    (OUT / "plan.json").write_text(json.dumps([{"item": i, "state": st} for i, st in plan], indent=1))

    status = [{
        "phase": phase, "step": step, "total_steps": TOTAL_STEPS,
        "eta_minutes": round(pace * (TOTAL_STEPS - step)) if pace and not grpo else 0,
        "tenki_usd": costs["total_usd"], "tenki_sandboxes": costs["sandboxes"],
        "tenki_sandbox_minutes": round(costs["sandbox_seconds"] / 60, 1),
        "local_gpu_usd": 0.0, "updated": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
    }]
    (OUT / "status.json").write_text(json.dumps(status, indent=1))
    print(json.dumps(status[0]))


if __name__ == "__main__":
    main()
