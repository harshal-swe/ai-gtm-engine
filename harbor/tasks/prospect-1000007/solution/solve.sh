#!/bin/bash
cat > /app/action.json <<'JSON'
{"icp_check": {"industry_match": true, "size_match": true, "region_match": true, "buyer_match": true, "red_flag": false}, "decision": "pursue", "tier": "A", "channel": "email", "subject": "Copper Cloud and PipeForge", "message": "Hi Raj, saw that copper Cloud announced expansion into LATAM (new). PipeForge helps teams like Copper Cloud replace stale lead lists with live buying signals, with a pipeline growth focus. Open to a quick chat next week?"}
JSON
