#!/usr/bin/env python3
"""Quick test: generate dashboard payload without sending to Notion."""
import json
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.dashboard_report_vps import build_dashboard_payload

p = build_dashboard_payload()
print(json.dumps(p, indent=2, default=str))
