#!/bin/bash
cat > /app/action.json <<'JSON'
{"icp_check": {"industry_match": true, "size_match": true, "region_match": true, "buyer_match": true, "red_flag": false}, "decision": "pursue", "tier": "A", "channel": "linkedin", "subject": "Nimbus Pay and PipeForge", "message": "Hi Chloe, saw that nimbus Pay has 26 open sales roles posted (hiring). PipeForge helps teams like Nimbus Pay lower CAC by only working in-market accounts, with a pipeline growth focus. Open to a quick chat next week?"}
JSON
