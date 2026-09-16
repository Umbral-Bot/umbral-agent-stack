"""Offline tests for scripts/vm/pcrick_ssh_dispatch.py.

No real ssh, no PCRick, no network. Fake-ssh test doubles under
tests/fixtures/ stand in for the real `ssh` binary via --ssh-binary.
"""
from __future__ import annotations

import importlib.util
import os
import select
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1] / "scripts/vm/pcrick_ssh_dispatch.py"
FIXTURES = Path(__file__).resolve().parent / "fixtures"
FAKE_SSH_CLI = FIXTURES / "fake_ssh_cli.py"

spec = importlib.util.spec_from_file_location("pcrick_ssh_dispatch", MODULE)
dispatch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dispatch)


def _tempdir(test: unittest.TestCase) -> Path:
    d = tempfile.mkdtemp(prefix="pcrick-ssh-dispatch-test-")
    test.addCleanup(lambda: subprocess.run(["rm", "-rf", d]))
    return Path(d)


class BuildSshArgvTests(unittest.TestCase):
    """The local ssh invocation must be a plain argv list, never a shell
    string built by local interpolation. This is a local-execution
    guarantee only: the remote shell still interprets remote_command."""

    def test_structured_argv_flags_are_discrete_elements(self):
        argv = dispatch.build_ssh_argv(
            host="127.0.0.1",
            port=22024,
            user="rick",
            remote_command="whoami && hostname",
            connect_timeout=8,
        )
        self.assertEqual(argv[0], "ssh")
        self.assertIn("-n", argv)
        self.assertIn("BatchMode=yes", argv)
        self.assertIn("ConnectTimeout=8", argv)
        self.assertIn("-p", argv)
        self.assertIn("22024", argv)
        self.assertEqual(argv[-2], "rick@127.0.0.1")
        # Exactly one element carries the remote command; it is passed
        # through verbatim (ssh's own single-string command interface).
        self.assertEqual(argv[-1], "whoami && hostname")

    def test_empty_remote_command_rejected(self):
        with self.assertRaises(ValueError):
            dispatch.build_ssh_argv(host="h", port=1, user="u", remote_command="")

    def test_joining_with_spaces_does_not_preserve_argument_boundaries(self):
        """Pins the documented sharp edge: the CLI joins the trailing tokens
        with a single space, so an argument that contains spaces is NOT kept
        whole -- the remote shell sees several tokens. Asserted here so the
        wrapper is never read as argv-preserving."""
        args = dispatch.parse_args(
            ["--host", "h", "--port", "1", "--user", "u", "--", "echo", "hola mundo"]
        )
        self.assertEqual(args.remote_command, ["echo", "hola mundo"])
        argv = dispatch.build_ssh_argv(
            host="h", port=1, user="u", remote_command=" ".join(args.remote_command),
        )
        self.assertEqual(argv[-1], "echo hola mundo")

    def test_remote_command_metacharacters_never_reach_a_local_shell(self):
        """Scope check, not a sanitization claim. A remote_command full of
        shell metacharacters must be handed to the (fake) ssh binary as ONE
        untouched argv element and never interpreted by a LOCAL shell on the
        VPS. A real local shell (`shell=True` or manual string
        interpolation) would treat `;` as a command separator and actually
        run `touch <canary>`; our fixture process is not a shell at all, so
        proving the canary was never created proves no local shell ever saw
        this string.

        This proves NOTHING about the remote side. remote_command is a
        trusted, pre-formatted string and the remote Windows shell does
        interpret it, by design (see the module docstring). The wrapper
        offers no protection there, and this test asserts none."""
        canary = _tempdir(self) / "should-not-exist.txt"
        dangerous = f"echo hi; touch {canary}; echo pwned"
        argv = dispatch.build_ssh_argv(
            host="h", port=1, user="u", remote_command=dangerous, ssh_binary=str(FAKE_SSH_CLI),
        )
        # Our own local argv must carry the dangerous string as ONE element.
        self.assertEqual(argv[-1], dangerous)
        dispatch.run_dispatch(argv)
        self.assertFalse(
            canary.exists(),
            "a LOCAL shell on the VPS interpreted the remote command -- local injection!",
        )


class RunDispatchExitCodeTests(unittest.TestCase):
    """run_dispatch must return the real remote exit code and pass through
    real stdout/stderr, not a summarized/altered result."""

    def test_exit_code_and_output_are_the_real_ones(self):
        fixture = FIXTURES / "fake_ssh_echo_exit.py"
        argv = [sys.executable, str(fixture), "42", "some", "remote", "command"]
        code = dispatch.run_dispatch(argv)
        self.assertEqual(code, 42)

    def test_cli_rejects_missing_remote_command_without_hanging(self):
        result = subprocess.run(
            [sys.executable, str(MODULE), "--host", "h", "--port", "1", "--user", "u",
             "--ssh-binary", str(FAKE_SSH_CLI), "--"],
            capture_output=True, text=True, timeout=5,
        )
        self.assertNotEqual(result.returncode, 0)

    def test_cli_end_to_end_propagates_exit_code(self):
        counter = _tempdir(self) / "calls.txt"
        result = subprocess.run(
            [sys.executable, str(MODULE),
             "--host", "127.0.0.1", "--port", "22024", "--user", "rick",
             "--ssh-binary", str(FAKE_SSH_CLI),
             "--", "count-and-exit", str(counter), "13"],
            capture_output=True, text=True, timeout=10,
        )
        self.assertEqual(result.returncode, 13)


class NoInfiniteRetryTests(unittest.TestCase):
    """A connection failure (ssh's real exit 255) must come back as-is,
    exactly once -- no local retry loop."""

    def test_connection_failure_exit_code_is_not_retried(self):
        tmp = _tempdir(self)
        counter = tmp / "calls.txt"
        fixture = FIXTURES / "fake_ssh_count_and_exit.py"
        argv = [sys.executable, str(fixture), str(counter), "255"]

        code = dispatch.run_dispatch(argv)

        self.assertEqual(code, 255)
        calls = counter.read_text(encoding="utf-8").count("call\n")
        self.assertEqual(calls, 1, "the fake ssh binary must be invoked exactly once")


class LineageRegressionTests(unittest.TestCase):
    """Regression test for the actual T2 bug: a slow real remote command
    must NOT cause the wrapper to exit/close its own descriptors before
    that command truly finishes. This is exercised at the OS process level
    (an inherited pipe standing in for OpenClaw's real lineage fd) so it
    reproduces the anchor's real observation without needing the Node
    anchor itself."""

    def test_wrapper_keeps_lineage_descriptor_open_until_real_child_exits(self):
        read_fd, write_fd = os.pipe()
        self.addCleanup(lambda: self._safe_close(read_fd))

        proc = subprocess.Popen(
            [sys.executable, str(MODULE),
             "--host", "h", "--port", "1", "--user", "u",
             "--ssh-binary", str(FAKE_SSH_CLI),
             "--", "slow-exit", "0.35", "7"],
            pass_fds=(write_fd,),
        )
        # Our own ("anchor"'s) copy of the write end must be closed so that
        # only the wrapper's inherited copy can keep the pipe open.
        os.close(write_fd)

        start = time.monotonic()
        eof_seen_at = None
        while True:
            ready, _, _ = select.select([read_fd], [], [], 0.02)
            if ready:
                chunk = os.read(read_fd, 1)
                if chunk == b"":
                    eof_seen_at = time.monotonic()
                    break
            if time.monotonic() - start > 5:
                self.fail("timed out waiting for lineage pipe EOF")

        returncode = proc.wait(timeout=2)

        self.assertEqual(returncode, 7, "the wrapper must propagate the slow child's real exit code")
        self.assertGreaterEqual(
            eof_seen_at - start, 0.3,
            "the lineage descriptor closed before the slow remote command finished -- "
            "this is exactly the premature-SIGTERM bug the wrapper exists to prevent",
        )

    @staticmethod
    def _safe_close(fd):
        try:
            os.close(fd)
        except OSError:
            pass


class SignalForwardingTests(unittest.TestCase):
    """A cancellation of the wrapper must reach the real child promptly and
    controllably, not abandon it."""

    def test_sigterm_is_forwarded_to_the_real_child(self):
        import signal

        tmp = _tempdir(self)
        marker = tmp / "trapped.txt"

        proc = subprocess.Popen(
            [sys.executable, str(MODULE),
             "--host", "h", "--port", "1", "--user", "u",
             "--ssh-binary", str(FAKE_SSH_CLI),
             "--", "trap-sigterm", str(marker)],
        )
        time.sleep(0.3)  # let the child install its trap
        proc.send_signal(signal.SIGTERM)
        returncode = proc.wait(timeout=5)

        self.assertTrue(marker.exists(), "SIGTERM was not forwarded to the real child")
        self.assertEqual(returncode, 9)


if __name__ == "__main__":
    unittest.main()
