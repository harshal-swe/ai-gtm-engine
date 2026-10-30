"""Print a before/after markdown table from two eval result files.

    python -m gtm_sim.compare results/baseline.json results/grpo.json
"""

import json
import sys

ROWS = [
    ("Mean simulator reward", "mean_reward", "{:.2f}"),
    ("Qualification accuracy", "qualification_accuracy", "{:.1%}"),
    ("Wasted sends on bad-fit leads", "wasted_sends_on_bad_fit", "{:d}"),
    ("Expected replies", "expected_replies", "{:.1f}"),
    ("Expected meetings booked", "expected_meetings", "{:.1f}"),
    ("Reply rate on good-fit leads", "reply_rate_on_good_fit", "{:.1%}"),
]
FEATURES = [
    ("Uses the buying signal", "uses_signal"),
    ("Persona-preferred channel", "right_channel"),
    ("Persona tone match", "tone_match"),
    ("Clear call to action", "has_cta"),
    ("Correct priority tier", "tier_correct"),
    ("Unsupported claims (lower is better)", "unsupported_claim"),
]


def main():
    a, b = (json.load(open(p)) for p in sys.argv[1:3])
    print(f"| Metric | {a['name']} | {b['name']} |\n|---|---|---|")
    for label, key, fmt in ROWS:
        print(f"| {label} | {fmt.format(a[key])} | {fmt.format(b[key])} |")
    for label, key in FEATURES:
        fa, fb = a["message_feature_rates"].get(key, 0), b["message_feature_rates"].get(key, 0)
        print(f"| {label} | {fa:.0%} | {fb:.0%} |")
    fa, fb = a["sampled_funnel"], b["sampled_funnel"]
    print(f"| Sampled funnel (DQ / Contacted / Replied / Meeting) | "
          f"{' / '.join(str(v) for v in fa.values())} | {' / '.join(str(v) for v in fb.values())} |")


if __name__ == "__main__":
    main()
