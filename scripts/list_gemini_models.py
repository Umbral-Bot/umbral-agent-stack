#!/usr/bin/env python3
"""List available Gemini models that support generateContent."""
import json
import os
import urllib.request

key = os.environ.get("GOOGLE_API_KEY", "")
url = f"https://generativelanguage.googleapis.com/v1beta/models?key={key}"
try:
    r = urllib.request.urlopen(url, timeout=15)
    d = json.loads(r.read())
    for m in d.get("models", []):
        name = m.get("name", "")
        display = m.get("displayName", "")
        methods = m.get("supportedGenerationMethods", [])
        if "generateContent" in methods:
            print(f"{name}  ({display})")
except Exception as e:
    print(f"ERROR: {e}")
