# AI GTM Engine

Hackathon project: an autonomous, closed-loop go-to-market engine (ICP → discovery → knowledge graph → enrichment → HITL outreach → pipeline dashboard).

See [docs/hackathon-spec.md](docs/hackathon-spec.md) for the full brief.

## GTM Gym: training RelayGTM's outreach agent in simulation

`gtm_sim/` is a GTM environment where a policy model plays an SDR: for each (product, prospect) pair it
checks the ICP, decides pursue/disqualify, picks a tier and channel, and drafts a first-touch message.
Simulated buyers with hidden persona preferences score the draft as a reply/meeting probability, with
penalties for spam words and figures not found in the prospect dossier. We post-train Qwen3-0.6B
on it with GRPO (TRL + LoRA) and compare against the base model on held-out prospects.

The policy trains locally (Apple Silicon MPS or CUDA); every reward is scored by the simulator inside
[Tenki](https://tenki.cloud) sandboxes (`gtm_sim/remote.py`), falling back to local scoring with no key.

```bash
python3.13 -m venv .venv && .venv/bin/pip install -r requirements.txt
echo 'TENKI_API_KEY=tk_...' > .env            # optional; gitignored

.venv/bin/python -m gtm_sim.evaluate --name baseline              # base model, 200 held-out prospects
.venv/bin/python train_grpo.py --steps 50                         # GRPO; logs to results/train_log.jsonl
.venv/bin/python -m gtm_sim.evaluate --name grpo --adapter runs/grpo/final
.venv/bin/python -m gtm_sim.compare results/baseline.json results/grpo.json
.venv/bin/python -m gtm_sim.export_relaygtm results/grpo_samples.jsonl > relaygtm_leads.json
```

| File | Purpose |
|---|---|
| `gtm_sim/env.py` | Products, prospect generator, prompt, simulated buyer (`score`, `rollout`) |
| `gtm_sim/remote.py` | Scores completions in Tenki sandboxes (self-healing pool) |
| `gtm_sim/evaluate.py` | Held-out eval with funnel metrics |
| `train_grpo.py` | GRPO post-training of Qwen3-0.6B with LoRA |
| `gtm_sim/export_relaygtm.py` | Converts eval rollouts into RelayGTM dashboard leads (fictional data) |
| `gtm_sim/costs.py`, `gtm_sim/dashboard_data.py` | Tenki spend estimate and progress-dashboard data |

### Results (Oct 30, 2026)

Base Qwen3-0.6B vs the trained model on 200 held-out simulated prospects (`results/baseline.json`, `results/grpo.json`):

| Metric | Base | Trained |
|---|---|---|
| Expected meetings booked | 10.8 | 18.1 (+67%) |
| Qualification accuracy | 58.5% | 76.5% |
| Wasted sends to bad-fit leads | 41 | 46 |
| ICP-check field accuracy | 66% | 77% |

External checks: on the **Harbor benchmark** (30 held-out prospects as Harbor tasks, each graded in its own Tenki VM;
`harbor/run_bench.sh`), mean reward 0.59 → 1.55 against a rule-based oracle ceiling of 2.58, and qualification 50% → 80%.
On a 24-task slice of **GTM-Bench**'s ICP step ([pearlengine/GTM.Bench](https://github.com/pearlengine/GTM.Bench),
tasks fetched at run time, scored with its judge rubric), 1.53 → 1.57 out of 5: no regression on a task the model was
not trained for. Not a leaderboard entry.

How we got there: run 1 improved messages but never disqualified a lead; run 2 added the ICP check and swung between
pursuing everyone and disqualifying most leads (`results/val_ckpt*.json`), because skipping a good lead cost only −0.2.
Run 3 raised that penalty to −1.0 and continued from run 2's step-20 checkpoint for 25 steps. Total Tenki spend: about $0.35.

**Band integration:** `gtm_sim/band_agent.py` puts the trained policy in a [Band](https://www.band.ai/) room. Mention it
(`@gtm-gym prospect 1000004`), and it posts its decision, draft and the simulated buyer's verdict, then waits for a human
to reply `approve` or `reject`. Put the agent's `agent_id`/`api_key` from app.band.ai in a gitignored `agent_config.yaml`
under `gtm_gym:`, then run `.venv/bin/python -m gtm_sim.band_agent`.
No Band account yet? `.venv/bin/python -m gtm_sim.band_demo` runs the same agent in a local mock of a Band room.
