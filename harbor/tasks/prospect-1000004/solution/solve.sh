#!/bin/bash
cat > /app/action.json <<'JSON'
{"icp_check": {"industry_match": true, "size_match": true, "region_match": true, "buyer_match": true, "red_flag": false}, "decision": "pursue", "tier": "A", "channel": "linkedin", "subject": "Ember Works and VaultEdge", "message": "Hi Felix, saw that ember Works is migrating from QuickBooks to HubSpot (migrat). VaultEdge helps teams like Ember Works find misconfigurations before attackers do, with a api ci focus. Open to a quick chat next week?"}
JSON
