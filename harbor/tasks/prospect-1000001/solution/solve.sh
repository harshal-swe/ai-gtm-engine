#!/bin/bash
cat > /app/action.json <<'JSON'
{"icp_check": {"industry_match": true, "size_match": true, "region_match": true, "buyer_match": true, "red_flag": false}, "decision": "pursue", "tier": "A", "channel": "email", "subject": "Quanta Systems and LedgerLoop", "message": "Hi Sam, saw that quanta Systems announced expansion into North America (expan). LedgerLoop helps teams like Quanta Systems audit-ready revenue numbers with zero manual tie-outs, with a roi cost focus. Open to a quick chat next week?"}
JSON
