#!/bin/bash
cat > /app/action.json <<'JSON'
{"icp_check": {"industry_match": true, "size_match": true, "region_match": false, "buyer_match": true, "red_flag": false}, "decision": "pursue", "tier": "C", "channel": "email", "subject": "Atlas Systems and LedgerLoop", "message": "Hi Tom, saw that atlas Systems is growing. LedgerLoop helps teams like Atlas Systems eliminate spreadsheet reconciliation headcount, with a roi cost focus. Open to a quick chat next week?"}
JSON
