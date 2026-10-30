"""Score our policies on GTM-Bench's ICP-definition step.

GTM-Bench (Blackpearl, https://github.com/pearlengine/GTM.Bench) gives real seller
prompts and an LLM-judge rubric for the ICP.md artifact. Its repo has no license,
so this script fetches the task set and judge prompt at run time and does not
store them in this repository. The judge runs through the local `claude` CLI.

    python -m gtm_sim.gtmbench_icp --name base
    python -m gtm_sim.gtmbench_icp --name grpo --adapter runs/grpo3/final
"""

import argparse
import json
import pathlib
import re
import subprocess
import urllib.request
from concurrent.futures import ThreadPoolExecutor

RAW = "https://raw.githubusercontent.com/pearlengine/GTM.Bench/HEAD/"
DIMS = ["icp_alignment", "buyer_account_specificity", "commercial_relevance", "gtm_actionability",
        "concision", "offer_separation"]


def fetch(path: str) -> str:
    with urllib.request.urlopen(RAW + path, timeout=30) as r:
        return r.read().decode()


def icp_prompt(task: str, schema: str) -> list[dict]:
    return [
        {"role": "system", "content": "You are a GTM strategist. Write the ideal customer profile as a Markdown "
                                      "document that follows the given template exactly. Be specific and concise."},
        {"role": "user", "content": f"TASK:\n{task}\n\nWrite ICP.md using this template:\n\n{schema}"},
    ]


def judge(judge_prompt: str, task: str, icp: str) -> dict | None:
    prompt = (f"{judge_prompt}\n\nDo not use any tools; judge from the inputs alone.\n\n"
              f"TASK:\n{task}\n\nOFFER.md:\n(Not produced in this run; infer the offer from the TASK.)\n\n"
              f"ICP.md:\n{icp}")
    r = subprocess.run(["claude", "-p", prompt], capture_output=True, text=True, timeout=300)
    m = re.search(r"\{.*\}", r.stdout, flags=re.S)
    try:
        d = json.loads(m.group(0)) if m else None
        return {k: int(d[k]["score"]) for k in DIMS} if d else None
    except (json.JSONDecodeError, KeyError, TypeError, ValueError):
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True)
    ap.add_argument("--adapter", default=None)
    ap.add_argument("--n", type=int, default=24)
    ap.add_argument("--judges", type=int, default=8)
    args = ap.parse_args()

    tasks = [json.loads(l) for l in fetch("tasks/question_set.jsonl").splitlines() if l.strip()]
    tasks = tasks[:: max(1, len(tasks) // args.n)][: args.n]  # spread across suites and verticals
    schema = fetch("prompts/gtm_bench/icp_schema.md")
    judge_prompt = fetch("prompts/judges/icp_judge.md")

    import torch
    from .evaluate import device, load_policy
    model, tok = load_policy(args.adapter)
    icps = []
    for i in range(0, len(tasks), 8):
        batch = tasks[i:i + 8]
        texts = [tok.apply_chat_template(icp_prompt(t["prompt"], schema), tokenize=False,
                                         add_generation_prompt=True, enable_thinking=False) for t in batch]
        enc = tok(texts, return_tensors="pt", padding=True).to(device())
        with torch.no_grad():
            gen = model.generate(**enc, max_new_tokens=600, do_sample=False, pad_token_id=tok.pad_token_id)
        icps += tok.batch_decode(gen[:, enc["input_ids"].shape[1]:], skip_special_tokens=True)
        print(f"  generated {len(icps)}/{len(tasks)}", flush=True)
    del model

    with ThreadPoolExecutor(args.judges) as ex:
        scores = list(ex.map(lambda p: judge(judge_prompt, p[0]["prompt"], p[1]), zip(tasks, icps)))

    ok = [s for s in scores if s]
    means = {k: sum(s[k] for s in ok) / len(ok) for k in DIMS} if ok else {}
    out = {"name": args.name, "adapter": args.adapter, "n_tasks": len(tasks), "n_judged": len(ok),
           "mean_overall": sum(means.values()) / len(DIMS) if ok else None, "means": means,
           "source": "GTM-Bench ICP judge rubric (pearlengine/GTM.Bench), tasks fetched at run time",
           "per_task": [{"task_id": t["task_id"], "vertical": t["metadata"].get("vertical"), "scores": s, "icp": icp}
                        for t, s, icp in zip(tasks, scores, icps)]}
    pathlib.Path("results").mkdir(exist_ok=True)
    pathlib.Path(f"results/gtmbench_icp_{args.name}.json").write_text(json.dumps(out, indent=2))
    print(json.dumps({k: v for k, v in out.items() if k != "per_task"}, indent=2))


if __name__ == "__main__":
    main()
