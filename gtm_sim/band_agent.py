"""GTM Gym as a Band agent: the trained outreach policy in a shared Band room.

Mention it in a room, optionally with a prospect id from the held-out set:

    @gtm-gym prospect 1000004
    @gtm-gym next

It runs the trained Qwen3-0.6B adapter on that prospect, scores the draft with
the simulated buyer, posts decision + draft + verdict, and asks the person who
mentioned it to reply "approve" or "reject" (the human-in-the-loop gate; nothing
is ever sent to a real prospect). Approvals are logged to results/band_approvals.jsonl.

Setup: create an agent at app.band.ai, then put its credentials in a gitignored
agent_config.yaml at the repo root:

    gtm_gym:
      agent_id: "<id>"
      api_key: "<key>"

    .venv/bin/python -m gtm_sim.band_agent
"""

import json
import pathlib
import re
import time

from band import Agent
from band.core.simple_adapter import SimpleAdapter

from . import env
from .evaluate import generate, load_policy

ADAPTER = "runs/grpo3/final"
LOG = pathlib.Path("results/band_approvals.jsonl")


class GTMGymAdapter(SimpleAdapter):
    def __init__(self):
        super().__init__()
        self.model, self.tok = load_policy(ADAPTER)
        self.next_seed = env.EVAL_SEED
        self.pending: dict[str, dict] = {}  # room_id -> last draft awaiting a decision

    async def on_message(self, msg, tools, history, participants_msg, contacts_msg, *,
                         is_session_bootstrap, room_id):
        text = (msg.content or "").strip()
        reply_to = [msg.sender_name] if msg.sender_name else None

        decision = re.search(r"\b(approve|reject)\b", text, re.I)
        if decision and room_id in self.pending:
            item = self.pending.pop(room_id)
            LOG.parent.mkdir(exist_ok=True)
            with LOG.open("a") as f:
                f.write(json.dumps({**item, "human": msg.sender_name, "verdict": decision.group(1).lower(),
                                    "at": time.time()}) + "\n")
            await self._send(tools, f"Logged: {decision.group(1).lower()}d prospect {item['seed']}. "
                                    "Nothing was sent to a real person.", reply_to)
            return

        m = re.search(r"prospect\s+(\d+)", text, re.I)
        seed = int(m.group(1)) if m else self.next_seed
        self.next_seed = seed + 1
        ep = env.make_episode(seed)
        completion = generate(self.model, self.tok, [ep], batch_size=1)[0]
        action = env.parse_action(completion) or {}
        o = env.score(ep, completion)
        pr = ep.prospect

        lines = [f"**Prospect {seed}**: {pr.contact_name}, {pr.title} at {pr.company} "
                 f"({pr.industry}, {pr.headcount} employees, {pr.region}) · product: {ep.product['name']}"]
        if action.get("decision") == "disqualify":
            lines.append("**Decision:** disqualify")
        else:
            lines += [f"**Decision:** pursue · tier {action.get('tier')} · {action.get('channel')}",
                      f"**Subject:** {action.get('subject', '')}",
                      f"**Draft:** {action.get('message', '')}"]
        verdict = "correct" if o.decision_correct else "wrong"
        lines.append(f"**Simulated buyer:** decision {verdict} · reply {o.reply_prob:.0%} · "
                     f"meeting {o.meeting_prob:.0%} · reward {o.reward:.2f}")
        lines.append("Reply **approve** or **reject**. Fictional prospect; nothing is sent.")
        self.pending[room_id] = {"seed": seed, "action": action, "reward": o.reward}
        await self._send(tools, "\n".join(lines), reply_to)

    async def _send(self, tools, content, mentions):
        try:
            await tools.send_message(content, mentions=mentions)
        except Exception:  # noqa: BLE001 - a handle the platform can't resolve: reply without mentioning
            await tools.send_message(content)


def main():
    agent = Agent.from_config("gtm_gym", adapter=GTMGymAdapter(), config_path="agent_config.yaml")
    agent.run()


if __name__ == "__main__":
    main()
