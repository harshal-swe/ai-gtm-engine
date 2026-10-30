"""Export simulator rollouts as RelayGTM dashboard leads (fictional demo data).

Maps onto the RelayGTM dashboard columns: Lead, Company & role, Stage, Fit score,
Attribution, Enrichment, Graph, Source, Approval — plus the drafted outreach for
the Agent Workspace approval queue.

    python -m gtm_sim.export_relaygtm results/grpo_samples.jsonl > results/relaygtm_leads.json
"""

import json
import sys

from . import env

STAGES = ["Matched", "Contacted", "Replied", "Meeting Booked", "Closed/Lost"]


def to_lead(row: dict) -> dict:
    p = row["prospect"]
    action = env.parse_action(row["completion"]) or {}
    stage = row["outcome"]["stage"]
    ep = env.make_episode(row["seed"])
    return {
        "id": f"sim-{row['seed']}",
        "lead": p["contact_name"],
        "company": p["company"],
        "role": p["title"],
        "product": row["product"],
        # Disqualified prospects are closed out by the agent; everything else keeps its sampled stage.
        "stage": "Closed/Lost" if stage == "Disqualified" else stage,
        "fitScore": round(100 * ep.fit_score()),
        "tier": action.get("tier"),
        "attribution": "agent",
        "agentDecision": action.get("decision"),
        "enrichment": "simulated",
        "graph": {"industry": p["industry"], "headcount": p["headcount"], "region": p["region"]},
        "signals": p["signals"],
        "source": "gtm-simulator (fictional)",
        "approval": "pending" if action.get("decision") == "pursue" else "n/a",
        "draft": {k: action.get(k) for k in ("channel", "subject", "message")},
        "simulated": {"replyProb": round(row["outcome"]["reply_prob"], 3),
                      "meetingProb": round(row["outcome"]["meeting_prob"], 3)},
    }


def main():
    rows = [json.loads(line) for line in open(sys.argv[1])]
    leads = [to_lead(r) for r in rows]
    json.dump({"mode": "demo", "stages": STAGES, "leads": leads}, sys.stdout, indent=2)


if __name__ == "__main__":
    main()
