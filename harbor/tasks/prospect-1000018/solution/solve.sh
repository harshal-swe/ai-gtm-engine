#!/bin/bash
cat > /app/action.json <<'JSON'
{"icp_check": {"industry_match": true, "size_match": true, "region_match": true, "buyer_match": true, "red_flag": false}, "decision": "pursue", "tier": "B", "channel": "email", "subject": "Harbor AI and PipeForge", "message": "Hi Priya, saw that harbor AI is growing. PipeForge helps teams like Harbor AI replace stale lead lists with live buying signals, with a pipeline growth focus. Open to a quick chat next week?"}
JSON
