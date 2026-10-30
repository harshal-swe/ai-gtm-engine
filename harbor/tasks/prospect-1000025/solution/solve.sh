#!/bin/bash
cat > /app/action.json <<'JSON'
{"icp_check": {"industry_match": true, "size_match": true, "region_match": false, "buyer_match": true, "red_flag": false}, "decision": "pursue", "tier": "B", "channel": "linkedin", "subject": "Helix Commerce and PipeForge", "message": "Hi Kenji, saw that helix Commerce raised a $75M Series B (raised). PipeForge helps teams like Helix Commerce lower CAC by only working in-market accounts, with a pipeline growth focus. Open to a quick chat next week?"}
JSON
