#!/usr/bin/env python3
"""Test double for `ssh`: appends one line to a counter file each time it
runs, then exits with a fixed code. Used to prove a connection-failure exit
is returned as-is with no local retry loop (the counter must stay at 1).
argv: <counter_file> <exit_code>
"""
import sys

counter_file, code = sys.argv[1], int(sys.argv[2])
with open(counter_file, "a", encoding="utf-8") as fh:
    fh.write("call\n")
sys.exit(code)
