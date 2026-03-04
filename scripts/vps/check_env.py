#!/usr/bin/env python3
import os
wt = os.environ.get("WORKER_TOKEN", "")
print(f"WORKER_TOKEN len={len(wt)} set={'yes' if wt else 'NO'}")
print(f"GOOGLE_API_KEY set={'yes' if os.environ.get('GOOGLE_API_KEY') else 'NO'}")
print(f"GITHUB_TOKEN set={'yes' if os.environ.get('GITHUB_TOKEN') else 'NO'}")
print(f"ANTHROPIC_API_KEY set={'yes' if os.environ.get('ANTHROPIC_API_KEY') else 'NO'}")
print(f"LANGFUSE_PUBLIC_KEY set={'yes' if os.environ.get('LANGFUSE_PUBLIC_KEY') else 'NO'}")
