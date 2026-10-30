"""Evaluate a policy on held-out prospects and report GTM funnel metrics.

    python -m gtm_sim.evaluate --name baseline
    python -m gtm_sim.evaluate --name grpo --adapter runs/grpo/final
"""

from __future__ import annotations

import argparse
import json
import pathlib
import time
from collections import Counter

import torch

from . import env
from .remote import Scorer

BASE_MODEL = "Qwen/Qwen3-0.6B"


def device() -> str:
    return "cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu"


def load_policy(adapter: str | None):
    from transformers import AutoModelForCausalLM, AutoTokenizer
    tok = AutoTokenizer.from_pretrained(BASE_MODEL, padding_side="left")
    model = AutoModelForCausalLM.from_pretrained(BASE_MODEL, dtype=torch.bfloat16).to(device())
    if adapter:
        from peft import PeftModel
        model = PeftModel.from_pretrained(model, adapter).merge_and_unload()
    model.eval()
    return model, tok


@torch.no_grad()
def generate(model, tok, episodes, batch_size: int = 16, max_new_tokens: int = 320) -> list[str]:
    outs = []
    for i in range(0, len(episodes), batch_size):
        batch = episodes[i:i + batch_size]
        prompts = [tok.apply_chat_template(env.messages(ep), tokenize=False, add_generation_prompt=True,
                                           enable_thinking=False) for ep in batch]
        enc = tok(prompts, return_tensors="pt", padding=True).to(model.device)
        gen = model.generate(**enc, max_new_tokens=max_new_tokens, do_sample=False,
                             pad_token_id=tok.pad_token_id)
        outs += tok.batch_decode(gen[:, enc["input_ids"].shape[1]:], skip_special_tokens=True)
        print(f"  generated {min(i + batch_size, len(episodes))}/{len(episodes)}", flush=True)
    return outs


def summarize(episodes, completions, outcomes) -> dict:
    n = len(episodes)
    good = [ep.should_pursue() for ep in episodes]
    stages = Counter(o["stage"] for o in outcomes)
    pursued = [o for o, c in zip(outcomes, completions) if (env.parse_action(c) or {}).get("decision") == "pursue"]
    good_pursued = [o for o, g in zip(outcomes, good) if g and o["stage"] != "Disqualified"]
    feats = Counter()
    for o in good_pursued:
        feats.update({k: v for k, v in o["features"].items()})
    return {
        "n": n,
        "mean_reward": sum(o["reward"] for o in outcomes) / n,
        "valid_json_rate": sum(o["valid"] for o in outcomes) / n,
        "qualification_accuracy": sum(o["decision_correct"] for o in outcomes) / n,
        "contacted": len(pursued),
        "wasted_sends_on_bad_fit": sum(1 for o, g in zip(outcomes, good) if not g and o["stage"] != "Disqualified"),
        "expected_replies": sum(o["reply_prob"] for o in outcomes),
        "expected_meetings": sum(o["meeting_prob"] for o in outcomes),
        "sampled_funnel": {s: stages.get(s, 0) for s in ["Disqualified", "Contacted", "Replied", "Meeting Booked"]},
        "reply_rate_on_good_fit": (sum(o["reply_prob"] for o in good_pursued) / len(good_pursued)) if good_pursued else 0.0,
        "message_feature_rates": {k: v / max(len(good_pursued), 1) for k, v in sorted(feats.items())},
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True)
    ap.add_argument("--adapter", default=None)
    ap.add_argument("--n", type=int, default=200)
    ap.add_argument("--batch-size", type=int, default=16)
    ap.add_argument("--backend", default="auto", choices=["auto", "local", "tenki"])
    ap.add_argument("--sandboxes", type=int, default=4)
    ap.add_argument("--split", default="test", choices=["test", "val"],
                    help="val = separate prospects for checkpoint selection, so the test set stays untouched")
    args = ap.parse_args()

    episodes = env.make_split(args.n, env.EVAL_SEED if args.split == "test" else env.VAL_SEED)
    model, tok = load_policy(args.adapter)
    t0 = time.time()
    completions = generate(model, tok, episodes, args.batch_size)
    gen_s = time.time() - t0

    with Scorer(args.backend, n_sandboxes=args.sandboxes) as scorer:
        t0 = time.time()
        outcomes = scorer.score([{"seed": ep.seed, "completion": c} for ep, c in zip(episodes, completions)],
                                rollout=True)
        score_s = time.time() - t0
        backend = scorer.backend

    metrics = summarize(episodes, completions, outcomes)
    metrics.update({"name": args.name, "adapter": args.adapter, "scoring_backend": backend,
                    "generation_seconds": round(gen_s, 1), "scoring_seconds": round(score_s, 2)})
    out = pathlib.Path("results"); out.mkdir(exist_ok=True)
    (out / f"{args.name}.json").write_text(json.dumps(metrics, indent=2))
    with open(out / f"{args.name}_samples.jsonl", "w") as f:
        for ep, c, o in zip(episodes, completions, outcomes):
            f.write(json.dumps({**env.episode_dict(ep), "completion": c, "outcome": o}) + "\n")
    print(json.dumps({k: v for k, v in metrics.items() if k != "message_feature_rates"}, indent=2))


if __name__ == "__main__":
    main()
