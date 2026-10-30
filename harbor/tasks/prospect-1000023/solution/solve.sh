#!/bin/bash
cat > /app/action.json <<'JSON'
{"icp_check": {"industry_match": true, "size_match": true, "region_match": true, "buyer_match": true, "red_flag": false}, "decision": "pursue", "tier": "B", "channel": "email", "subject": "Brightline Commerce and VaultEdge", "message": "Hi Victor, saw that brightline Commerce is growing. VaultEdge helps teams like Brightline Commerce pass SOC 2 and HIPAA audits in weeks, not quarters, with a api ci focus. Open to a quick chat next week?"}
JSON
