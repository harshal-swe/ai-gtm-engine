#!/bin/bash
cat > /app/action.json <<'JSON'
{"icp_check": {"industry_match": true, "size_match": true, "region_match": true, "buyer_match": true, "red_flag": false}, "decision": "pursue", "tier": "B", "channel": "linkedin", "subject": "Helix Works and PipeForge", "message": "Hi Elena, saw that helix Works is growing. PipeForge helps teams like Helix Works book meetings in week one instead of month three, with a pipeline growth focus. Open to a quick chat next week?"}
JSON
