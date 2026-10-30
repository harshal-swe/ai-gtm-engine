#!/bin/bash
cat > /app/action.json <<'JSON'
{"icp_check": {"industry_match": true, "size_match": true, "region_match": true, "buyer_match": true, "red_flag": false}, "decision": "pursue", "tier": "B", "channel": "email", "subject": "Mosaic Health and PipeForge", "message": "Hi Ines, saw that mosaic Health is growing. PipeForge helps teams like Mosaic Health replace stale lead lists with live buying signals, with a pipeline growth focus. Open to a quick chat next week?"}
JSON
