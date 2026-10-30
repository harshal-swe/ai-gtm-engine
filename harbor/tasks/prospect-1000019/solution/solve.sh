#!/bin/bash
cat > /app/action.json <<'JSON'
{"icp_check": {"industry_match": true, "size_match": true, "region_match": true, "buyer_match": true, "red_flag": false}, "decision": "pursue", "tier": "A", "channel": "email", "subject": "Ember AI and LedgerLoop", "message": "Hi Omar, saw that ember AI has 26 open finance roles posted (hiring). LedgerLoop helps teams like Ember AI audit-ready revenue numbers with zero manual tie-outs, with a roi cost focus. Open to a quick chat next week?"}
JSON
