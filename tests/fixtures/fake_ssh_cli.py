#!/usr/bin/env python3
"""Fake `ssh` CLI: tolerates real ssh-style flags (-n, -o VALUE, -p VALUE,
user@host) like a stub would, then treats its last positional argument as
the remote command line -- exactly like real ssh -- and interprets it as a
tiny "<mode> <args...>" protocol so tests can script different remote
behaviors while still exercising the wrapper's real ssh_binary substitution
end to end (flags included)."""
import shlex
import signal
import sys
import time

argv = sys.argv[1:]
i = 0
positional = []
while i < len(argv):
    a = argv[i]
    if a == "-n":
        i += 1
    elif a in ("-o", "-p"):
        i += 2
    elif a.startswith("-"):
        i += 1
    else:
        positional.append(a)
        i += 1

remote_command = positional[-1]
mode, *rest = shlex.split(remote_command)

if mode == "echo-exit":
    code = int(rest[0])
    print("STDOUT:" + " ".join(rest[1:]))
    print("STDERR-MARKER", file=sys.stderr)
    sys.exit(code)
elif mode == "slow-exit":
    delay, code = float(rest[0]), int(rest[1])
    time.sleep(delay)
    sys.exit(code)
elif mode == "count-and-exit":
    counter_file, code = rest[0], int(rest[1])
    with open(counter_file, "a", encoding="utf-8") as fh:
        fh.write("call\n")
    sys.exit(code)
elif mode == "trap-sigterm":
    marker = rest[0]

    def _handler(signum, frame):
        with open(marker, "w", encoding="utf-8") as fh:
            fh.write("trapped")
        sys.exit(9)

    signal.signal(signal.SIGTERM, _handler)
    time.sleep(10)
elif mode == "record-argv":
    dest = rest[0]
    with open(dest, "w", encoding="utf-8") as fh:
        fh.write(remote_command)
    sys.exit(0)
else:
    print(f"unknown mode: {mode}", file=sys.stderr)
    sys.exit(64)
