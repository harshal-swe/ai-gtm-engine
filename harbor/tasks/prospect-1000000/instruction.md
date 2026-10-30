You are an autonomous SDR agent in a go-to-market engine. For each prospect, first check the prospect against the ICP, then decide whether to pursue, assign a priority tier, pick an outreach channel and draft a first-touch message. Reply with ONLY a JSON object with keys in this order: "icp_check": {"industry_match": bool, "size_match": bool, "region_match": bool, "buyer_match": bool, "red_flag": bool}, "decision" ("pursue" only if every match is true and red_flag is false, otherwise "disqualify"), "tier" ("A", "B" or "C"), "channel" ("email" or "linkedin"), "subject" (string), "message" (string).

Prospect ID: 1000000

PRODUCT: ShipLens — AI test automation that writes and maintains end-to-end tests for web apps.
ICP: industries=SaaS, Fintech, E-commerce; headcount 50-2000; regions=North America, Europe; buyers in engineering, product.
VALUE PROPS:
- ship releases 2x faster without flaky tests
- cut QA spend by replacing manual regression cycles
- catch regressions before customers do

PROSPECT: Lena Cohen, CISO at Northwind Health
Company: SaaS, 11 employees, APAC
Recent signals:
- Northwind Health announced expansion into North America.
- Northwind Health has 17 open security roles posted.

Write ONLY the JSON object to /app/action.json. Do not ask questions; this task is non-interactive.
