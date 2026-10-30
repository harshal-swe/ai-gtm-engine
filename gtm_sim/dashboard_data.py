"""Build the GTM Gym dashboard's data files from results/.

    python -m gtm_sim.costs && python -m gtm_sim.dashboard_data   # writes results/dash/*.json
"""

import datetime as dt
import json
import pathlib

R = pathlib.Path("results")
OUT = R / "dash"
TOTAL_STEPS = 25

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


TRAINED = "grpo-run3"  # Harbor job / GTM-Bench result name of the model we present as "trained"


def harbor_stats(job):
    """Mean reward, qualification accuracy and expected meetings over a Harbor job's graded trials."""
    res = pathlib.Path(f"harbor/jobs/{job}/result.json")
    if not res.exists() or not json.loads(res.read_text()).get("finished_at"):
        return None  # only report finished jobs
    rows = [json.loads(p.read_text()) for p in pathlib.Path(f"harbor/jobs/{job}").glob("*/verifier/rewards.json")]
    if not rows:
        return None
    n = len(rows)
    return {"n": n, "reward": sum(r["reward"] for r in rows) / n,
            "qual": sum(r["decision_correct"] for r in rows) / n,
            "meetings": sum(r["meeting_prob"] for r in rows)}


def gtmbench(name):
    p = R / f"gtmbench_icp_{name}.json"
    return json.loads(p.read_text())["mean_overall"] if p.exists() else None


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

    hb = {k: harbor_stats(k) for k in ("base", TRAINED, "oracle")}
    pick = lambda k, f: hb[k][f] if hb[k] else None
    bench = [
        {"benchmark": "Harbor on Tenki (30 prospects)", "metric": "Mean simulator reward", "format": "num",
         "base": pick("base", "reward"), "trained": pick(TRAINED, "reward"), "ceiling": pick("oracle", "reward")},
        {"benchmark": "Harbor on Tenki (30 prospects)", "metric": "Qualification accuracy", "format": "pct",
         "base": pick("base", "qual"), "trained": pick(TRAINED, "qual"), "ceiling": pick("oracle", "qual")},
        {"benchmark": "Harbor on Tenki (30 prospects)", "metric": "Expected meetings booked", "format": "num",
         "base": pick("base", "meetings"), "trained": pick(TRAINED, "meetings"), "ceiling": pick("oracle", "meetings")},
        {"benchmark": "GTM-Bench ICP step (24 tasks)", "metric": "Judge score, 1 to 5", "format": "num",
         "base": gtmbench("base"), "trained": gtmbench(TRAINED), "ceiling": 5.0},
    ]
    for b in bench:
        b["id"] = b["benchmark"].split(" (")[0] + " / " + b["metric"]
    (OUT / "bench.json").write_text(json.dumps(bench, indent=1))

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
    run3 = pathlib.Path("runs/grpo3/final/adapter_config.json").exists()
    bench = pathlib.Path("logs/harbor_bench.out")
    bench_done = bench.exists() and "BENCH_DONE" in bench.read_text()
    plan = [
        ("GTM buyer simulator, scored in Tenki sandboxes", "done"),
        ("Run 1: messages improved, but the agent never disqualified a lead", "done"),
        ("Run 2 (ICP check added): fewer wasted sends, but too cautious, fewer meetings", "done"),
        ("Run 3: reward fix so skipping a good lead costs as much as the lost deal", "done" if run3 else "in progress"),
        ("Eval of run 3 on the held-out prospects", "done" if evaluated and run3 else "in progress" if run3 else "next"),
        ("Harbor benchmark on Tenki: oracle vs base vs trained, one VM per prospect",
         "done" if harbor_stats(TRAINED) else "in progress"),
        ("GTM-Bench ICP step: transfer check on real seller prompts", "done" if gtmbench(TRAINED) else "in progress"),
        ("Results slide for the RelayGTM deck", "done"),
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
