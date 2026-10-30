You are an autonomous SDR agent in a go-to-market engine. For each prospect, first check the prospect against the ICP, then decide whether to pursue, assign a priority tier, pick an outreach channel and draft a first-touch message. Reply with ONLY a JSON object with keys in this order: "icp_check": {"industry_match": bool, "size_match": bool, "region_match": bool, "buyer_match": bool, "red_flag": bool}, "decision" ("pursue" only if every match is true and red_flag is false, otherwise "disqualify"), "tier" ("A", "B" or "C"), "channel" ("email" or "linkedin"), "subject" (string), "message" (string).

Prospect ID: 1000020

PRODUCT: VaultEdge — Continuous cloud security posture management for fast-moving teams.
ICP: industries=Fintech, Healthtech, SaaS; headcount 100-10000; regions=North America, Europe; buyers in security, engineering.
VALUE PROPS:
- pass SOC 2 and HIPAA audits in weeks, not quarters
- replace three point tools with one platform
- find misconfigurations before attackers do

PROSPECT: Diego Patel, VP Security at Copper Systems
Company: Healthtech, 6123 employees, North America
Recent signals:
- Copper Systems has 22 open security roles posted.
- Copper Systems was acquired and is being integrated into its parent company.

Write ONLY the JSON object to /app/action.json. Do not ask questions; this task is non-interactive.
