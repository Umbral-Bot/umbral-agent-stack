#!/usr/bin/env python3
"""Test double for `ssh`: prints the argv it actually received (so tests can
verify what the wrapper passed through) then exits with a fixed code.
argv: <exit_code> [remote command string...]
"""
import sys

code = int(sys.argv[1])
print("STDOUT:" + " ".join(sys.argv[2:]))
print("STDERR-MARKER", file=sys.stderr)
sys.exit(code)
