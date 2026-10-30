You are an autonomous SDR agent in a go-to-market engine. For each prospect, first check the prospect against the ICP, then decide whether to pursue, assign a priority tier, pick an outreach channel and draft a first-touch message. Reply with ONLY a JSON object with keys in this order: "icp_check": {"industry_match": bool, "size_match": bool, "region_match": bool, "buyer_match": bool, "red_flag": bool}, "decision" ("pursue" only if every match is true and red_flag is false, otherwise "disqualify"), "tier" ("A", "B" or "C"), "channel" ("email" or "linkedin"), "subject" (string), "message" (string).

Prospect ID: 1000007

PRODUCT: PipeForge — Signal-based prospecting that finds in-market accounts for outbound teams.
ICP: industries=SaaS, Cybersecurity, Data Infrastructure; headcount 20-1000; regions=North America, Europe, APAC; buyers in sales, marketing.
VALUE PROPS:
- book meetings in week one instead of month three
- lower CAC by only working in-market accounts
- replace stale lead lists with live buying signals

PROSPECT: Raj Patel, VP Marketing at Copper Cloud
Company: Cybersecurity, 713 employees, North America
Recent signals:
- Copper Cloud announced expansion into LATAM.
- Copper Cloud hired a new VP Marketing 5 weeks ago.

Write ONLY the JSON object to /app/action.json. Do not ask questions; this task is non-interactive.
