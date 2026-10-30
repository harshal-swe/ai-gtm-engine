#!/bin/bash
cat > /app/action.json <<'JSON'
{"icp_check": {"industry_match": true, "size_match": false, "region_match": true, "buyer_match": true, "red_flag": false}, "decision": "pursue", "tier": "C", "channel": "linkedin", "subject": "Tidal Pay and PipeForge", "message": "Hi Kenji, saw that tidal Pay is growing. PipeForge helps teams like Tidal Pay book meetings in week one instead of month three, with a pipeline growth focus. Open to a quick chat next week?"}
JSON
