import json, pathlib, sys
sys.path.insert(0, "/tests")
import env
SEED = 1000005
ep = env.make_episode(SEED)
p = pathlib.Path("/app/action.json")
text = p.read_text() if p.exists() else ""
o = env.score(ep, text)
out = pathlib.Path("/logs/verifier")
out.mkdir(parents=True, exist_ok=True)
(out / "reward.txt").write_text(str(round(o.reward, 4)))
(out / "rewards.json").write_text(json.dumps({
    "reward": round(o.reward, 4), "reply_prob": round(o.reply_prob, 4),
    "meeting_prob": round(o.meeting_prob, 4), "decision_correct": int(o.decision_correct),
    "valid": int(o.valid)}))
print(json.dumps({"reward": o.reward, "features": o.features}))
