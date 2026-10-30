"""Harbor agent that submits a model's saved GTM Gym answers.

Our Qwen policies run on a Mac GPU, which Tenki VMs can't call, so the eval
generates their answers locally (results/<name>_samples.jsonl) and this agent
replays the answer for each task's prospect. Grading still runs in the task's
own Tenki VM, exactly as for any live agent.

    GTMGYM_SAMPLES=results/grpo_samples.jsonl harbor run ... --agent replay_agent:ReplayAgent
"""

import json
import os
import re
import tempfile

from harbor.agents.base import BaseAgent
from harbor.environments.base import BaseEnvironment
from harbor.models.agent.context import AgentContext


class ReplayAgent(BaseAgent):
    @staticmethod
    def name() -> str:
        return "gtmgym-replay"

    def version(self) -> str:
        return "1.0.0"

    async def setup(self, environment: BaseEnvironment) -> None:
        return

    async def run(self, instruction: str, environment: BaseEnvironment, context: AgentContext) -> None:
        seed = int(re.search(r"Prospect ID: (\d+)", instruction).group(1))
        path = os.environ["GTMGYM_SAMPLES"]
        answers = {r["seed"]: r["completion"] for r in map(json.loads, open(path))}
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            f.write(answers[seed])
        await environment.upload_file(f.name, "/app/action.json")
