You are an autonomous SDR agent in a go-to-market engine. For each prospect, first check the prospect against the ICP, then decide whether to pursue, assign a priority tier, pick an outreach channel and draft a first-touch message. Reply with ONLY a JSON object with keys in this order: "icp_check": {"industry_match": bool, "size_match": bool, "region_match": bool, "buyer_match": bool, "red_flag": bool}, "decision" ("pursue" only if every match is true and red_flag is false, otherwise "disqualify"), "tier" ("A", "B" or "C"), "channel" ("email" or "linkedin"), "subject" (string), "message" (string).

Prospect ID: 1000022

PRODUCT: VaultEdge — Continuous cloud security posture management for fast-moving teams.
ICP: industries=Fintech, Healthtech, SaaS; headcount 100-10000; regions=North America, Europe; buyers in security, engineering.
VALUE PROPS:
- pass SOC 2 and HIPAA audits in weeks, not quarters
- replace three point tools with one platform
- find misconfigurations before attackers do

PROSPECT: Chloe Silva, VP Marketing at Lumen Data
Company: Logistics, 39 employees, LATAM
Recent signals:
- Lumen Data posted a public complaint about their current accounting vendor.
- Lumen Data announced expansion into APAC.

Write ONLY the JSON object to /app/action.json. Do not ask questions; this task is non-interactive.
