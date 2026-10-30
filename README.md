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
