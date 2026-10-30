You are an autonomous SDR agent in a go-to-market engine. For each prospect, first check the prospect against the ICP, then decide whether to pursue, assign a priority tier, pick an outreach channel and draft a first-touch message. Reply with ONLY a JSON object with keys in this order: "icp_check": {"industry_match": bool, "size_match": bool, "region_match": bool, "buyer_match": bool, "red_flag": bool}, "decision" ("pursue" only if every match is true and red_flag is false, otherwise "disqualify"), "tier" ("A", "B" or "C"), "channel" ("email" or "linkedin"), "subject" (string), "message" (string).

Prospect ID: 1000019

PRODUCT: LedgerLoop — Automated revenue reconciliation and close for finance teams.
ICP: industries=SaaS, Marketplace, Fintech; headcount 100-5000; regions=North America; buyers in finance.
VALUE PROPS:
- close the books in 3 days instead of 10
- eliminate spreadsheet reconciliation headcount
- audit-ready revenue numbers with zero manual tie-outs

PROSPECT: Omar Ivanova, Head of Revenue Accounting at Ember AI
Company: SaaS, 4517 employees, North America
Recent signals:
- Ember AI has 26 open finance roles posted.

Write ONLY the JSON object to /app/action.json. Do not ask questions; this task is non-interactive.
