#!/bin/bash
cat > /app/action.json <<'JSON'
{"icp_check": {"industry_match": true, "size_match": true, "region_match": true, "buyer_match": true, "red_flag": false}, "decision": "pursue", "tier": "A", "channel": "linkedin", "subject": "Nimbus Labs and PipeForge", "message": "Hi Tom, saw that nimbus Labs is migrating from Jenkins to HubSpot (expan). PipeForge helps teams like Nimbus Labs book meetings in week one instead of month three, with a pipeline growth focus. Open to a quick chat next week?"}
JSON
