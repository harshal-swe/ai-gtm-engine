"""GRPO post-training of Qwen3-0.6B against the GTM simulator.

Policy + optimizer run locally (MPS/CUDA); every reward is computed by the
simulated buyer, inside a Tenki sandbox when TENKI_API_KEY is set.

    python train_grpo.py --steps 150
"""

import argparse
import json
import pathlib
import time

from datasets import Dataset
from peft import LoraConfig
from transformers import TrainerCallback
from trl import GRPOConfig, GRPOTrainer

from gtm_sim import env
from gtm_sim.evaluate import BASE_MODEL
from gtm_sim.remote import Scorer


class JsonlLogger(TrainerCallback):
    """Append each logged step to results/train_log.jsonl for the live dashboard."""

    def __init__(self, path="results/train_log.jsonl"):
        self.path = pathlib.Path(path)
        self.path.parent.mkdir(exist_ok=True)
        self.path.write_text("")

    def on_log(self, args, state, control, logs=None, **_):
        if logs and "reward" in logs:
            with self.path.open("a") as f:
                f.write(json.dumps({"step": state.global_step, "time": time.time(), **logs}) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--steps", type=int, default=50)
    ap.add_argument("--n-train", type=int, default=2000)
    ap.add_argument("--num-generations", type=int, default=8)
    ap.add_argument("--prompts-per-step", type=int, default=4)
    ap.add_argument("--lr", type=float, default=5e-5)
    ap.add_argument("--backend", default="auto", choices=["auto", "local", "tenki"])
    ap.add_argument("--out", default="runs/grpo")
    ap.add_argument("--init-adapter", default=None, help="continue training from a saved LoRA adapter")
    args = ap.parse_args()

    episodes = env.make_split(args.n_train, env.TRAIN_SEED)
    ds = Dataset.from_list([{"prompt": env.messages(ep), "seed": ep.seed} for ep in episodes])
    if args.init_adapter:  # don't replay the prompts the warm-start checkpoint already trained on
        ds = ds.shuffle(seed=1)

    scorer = Scorer(args.backend, n_sandboxes=1)

    def gtm_reward(completions, seed, **_):
        texts = [c[0]["content"] if isinstance(c, list) else c for c in completions]
        return [o["reward"] for o in scorer.score([{"seed": s, "completion": t} for s, t in zip(seed, texts)])]

    batch = args.num_generations * args.prompts_per_step
    cfg = GRPOConfig(
        output_dir=args.out,
        max_steps=args.steps,
        learning_rate=args.lr,
        lr_scheduler_type="constant_with_warmup",
        warmup_steps=5,
        per_device_train_batch_size=batch,
        gradient_accumulation_steps=1,
        num_generations=args.num_generations,
        max_completion_length=256,
        temperature=1.0,
        beta=0.0,
        chat_template_kwargs={"enable_thinking": False},
        bf16=True,
        logging_steps=1,
        save_steps=10,
        report_to="none",
        log_completions=False,
        seed=0,
    )
    lora = LoraConfig(r=16, lora_alpha=32, lora_dropout=0.0, task_type="CAUSAL_LM",
                      target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"])
    model, peft_config = BASE_MODEL, lora
    if args.init_adapter:
        import torch
        from peft import PeftModel
        from transformers import AutoModelForCausalLM
        base = AutoModelForCausalLM.from_pretrained(BASE_MODEL, dtype=torch.bfloat16)
        model, peft_config = PeftModel.from_pretrained(base, args.init_adapter, is_trainable=True), None
    trainer = GRPOTrainer(model=model, reward_funcs=gtm_reward, args=cfg, train_dataset=ds, peft_config=peft_config,
                          callbacks=[JsonlLogger()])
    try:
        trainer.train()
        trainer.save_model(f"{args.out}/final")
    finally:
        scorer.close()


if __name__ == "__main__":
    main()
