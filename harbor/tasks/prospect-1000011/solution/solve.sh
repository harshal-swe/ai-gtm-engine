#!/bin/bash
cat > /app/action.json <<'JSON'
{"icp_check": {"industry_match": false, "size_match": false, "region_match": false, "buyer_match": false, "red_flag": true}, "decision": "disqualify", "tier": "C", "channel": "email", "subject": "", "message": ""}
JSON
