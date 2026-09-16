#!/usr/bin/env python3
"""Dispatch a single remote command to PCRick over the existing SSH transport
without tripping OpenClaw's service-child lineage-fd supervision.

Root cause (T2, 2026-09-16; see docs/pcrick-job-adapter.md and
docs/operations/tanda2-desktop-recepcion-2026-09-16.md): OpenClaw's
``service-child-group-anchor`` supervises the command it spawns by holding an
extra file descriptor ("lineage fd") open across the whole process tree. If
the spawned command execs directly into ``ssh``, OpenSSH closes that
descriptor as part of its own startup hardening -- a normal, harmless thing
for ssh to do on its own -- but the anchor cannot tell that apart from a
genuinely orphaned subprocess tree. After a short grace window
(``LINEAGE_EXIT_OBSERVATION_MS`` = 100ms) it decides the lineage was lost and
sends SIGTERM to the whole process group, killing the still-running ssh
session.

Fix: never exec() into ssh. ``subprocess.Popen`` below forks a real child
without replacing this script's own process image, so this process keeps
running -- and keeps its own copy of any inherited supervision descriptors
open -- for ssh's entire real lifetime. The anchor then correctly observes
the lineage fd closing only when this wrapper itself exits, at (or after)
the moment ssh's real exit is already known, which is the normal/expected
completion path rather than the "lost lineage" path.

This script intentionally does NOT create a new session or process group
(no ``setsid``, no ``start_new_session=True``): staying in the same group as
the supervisor is what lets a legitimate group-wide cleanup signal still
reach ssh directly if the caller is actually canceled or the parent is lost.
Detaching from supervision to dodge the bug was considered and rejected.

Usage:
    pcrick_ssh_dispatch.py --host 127.0.0.1 --port 22024 --user rick \\
        --connect-timeout 8 -- whoami "&&" hostname

remote_command contract -- read this before passing anything through it:

1. It is a TRUSTED, PRE-FORMATTED remote command, not untrusted input. ssh
   hands the string to the remote Windows shell on PCRick and that shell
   DOES interpret it (``&&``, ``;``, quoting, redirection, expansion). This
   script offers no protection whatsoever against that remote
   interpretation, and does not try to: this is ssh's own normal
   single-string command interface, exactly as when a person types
   ``ssh host "a && b"`` by hand. Never build this string out of untrusted
   data.

2. The one guarantee this script does make is narrower: no LOCAL shell is
   involved on the VPS. The local ssh invocation is always built as a plain
   argv list and run without a shell (no ``shell=True``, no local string
   interpolation anywhere in this script), so the remote command's content
   -- including shell metacharacters meant for the *remote* host -- cannot
   execute anything locally on the VPS. That is the whole of the
   protection; it does not extend to the remote side.

3. Argument boundaries are NOT preserved. The trailing arguments are joined
   with a plain space (``" ".join(...)``) into the single command string ssh
   accepts, so an argument that itself contains spaces is effectively split
   into several tokens by the time the remote shell sees it: passing
   ``-- echo "hola mundo"`` arrives remotely as ``echo hola mundo``. If the
   remote command needs an argument containing spaces, quote it explicitly
   for the REMOTE shell inside the token itself, e.g.
   ``-- echo '"hola mundo"'``. Do not rely on local argv splitting to carry
   that boundary across.
"""
from __future__ import annotations

import argparse
import signal
import subprocess
import sys
import threading
from typing import Optional, Sequence

DEFAULT_CONNECT_TIMEOUT_SECONDS = 8
SIGTERM_TO_SIGKILL_GRACE_SECONDS = 5.0


def build_ssh_argv(
    *,
    host: str,
    port: int,
    user: str,
    remote_command: str,
    connect_timeout: int = DEFAULT_CONNECT_TIMEOUT_SECONDS,
    ssh_binary: str = "ssh",
) -> list[str]:
    """Build the ssh argv as a plain list -- no local shell string is ever
    built or interpreted. ``remote_command`` is passed through verbatim as
    the single argv element ssh hands to the remote shell: this function
    does not quote, escape or re-split it, so the caller owns whatever
    quoting the REMOTE shell needs and must treat the string as trusted,
    pre-formatted remote input (see the module docstring). Not building a
    local shell string only rules out local execution on the VPS; it says
    nothing about how the remote shell will interpret the string."""
    if not remote_command:
        raise ValueError("remote_command must be a non-empty string")
    return [
        ssh_binary,
        "-n",
        "-o", "BatchMode=yes",
        "-o", f"ConnectTimeout={connect_timeout}",
        "-p", str(port),
        f"{user}@{host}",
        remote_command,
    ]


def run_dispatch(ssh_argv: Sequence[str]) -> int:
    """Run ssh as a real child (never exec-replacing this process) and
    return its real exit code, forwarding SIGTERM/SIGINT to it if this
    wrapper itself is signaled."""
    # stdin=DEVNULL: the remote command is expected to be non-interactive
    # (ssh -n also refuses to read stdin at the protocol level); stdout and
    # stderr are left as this process's own fds so ssh's real output streams
    # straight through instead of being buffered and replayed.
    proc = subprocess.Popen(list(ssh_argv), stdin=subprocess.DEVNULL)

    kill_timer: Optional[threading.Timer] = None

    def _escalate_to_sigkill() -> None:
        if proc.poll() is None:
            proc.kill()

    def _forward_signal(signum: int, _frame: object) -> None:
        nonlocal kill_timer
        if proc.poll() is not None:
            return
        try:
            proc.send_signal(signum)
        except ProcessLookupError:
            return
        if kill_timer is None:
            kill_timer = threading.Timer(SIGTERM_TO_SIGKILL_GRACE_SECONDS, _escalate_to_sigkill)
            kill_timer.daemon = True
            kill_timer.start()

    previous_sigterm = signal.signal(signal.SIGTERM, _forward_signal)
    previous_sigint = signal.signal(signal.SIGINT, _forward_signal)
    try:
        return proc.wait()
    finally:
        if kill_timer is not None:
            kill_timer.cancel()
        signal.signal(signal.SIGTERM, previous_sigterm)
        signal.signal(signal.SIGINT, previous_sigint)


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--host", required=True)
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--user", required=True)
    parser.add_argument("--connect-timeout", type=int, default=DEFAULT_CONNECT_TIMEOUT_SECONDS)
    parser.add_argument("--ssh-binary", default="ssh", help="Override for tests; defaults to the ssh on PATH.")
    parser.add_argument(
        "remote_command",
        nargs=argparse.REMAINDER,
        help=(
            "Trusted, pre-formatted remote command, e.g. -- whoami '&&' hostname. "
            "These tokens are joined with a single space into the one command string "
            "ssh sends, so argument boundaries are NOT preserved: an argument "
            "containing spaces is split into several tokens by the remote shell. "
            "Quote for the remote shell yourself (e.g. -- echo '\"hola mundo\"'). "
            "The remote Windows shell does interpret this string; the only thing "
            "this wrapper guarantees is that no LOCAL shell is used on the VPS."
        ),
    )
    args = parser.parse_args(argv)
    if args.remote_command[:1] == ["--"]:
        args.remote_command = args.remote_command[1:]
    if not args.remote_command:
        parser.error("remote_command is required (pass it after --)")
    return args


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    ssh_argv = build_ssh_argv(
        host=args.host,
        port=args.port,
        user=args.user,
        remote_command=" ".join(args.remote_command),
        connect_timeout=args.connect_timeout,
        ssh_binary=args.ssh_binary,
    )
    return run_dispatch(ssh_argv)


if __name__ == "__main__":
    sys.exit(main())
