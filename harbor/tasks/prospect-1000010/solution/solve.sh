#!/bin/bash
cat > /app/action.json <<'JSON'
{"icp_check": {"industry_match": true, "size_match": true, "region_match": true, "buyer_match": true, "red_flag": false}, "decision": "pursue", "tier": "A", "channel": "email", "subject": "Juniper Systems and LedgerLoop", "message": "Hi Chloe, saw that juniper Systems raised a $40M Series C (raised). LedgerLoop helps teams like Juniper Systems eliminate spreadsheet reconciliation headcount, with a roi cost focus. Open to a quick chat next week?"}
JSON
