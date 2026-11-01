"""Run a project command with a timeout and measurements.

The command runs in its own process group with stdin closed: if it waits for input it gets
EOF instead of hanging. A separate thread reads the output, and the timeout is measured on
the main process, so a background child that keeps the output open does not turn a normal
exit into a "hang". After exit or timeout the whole group is killed. The result is the
time, the exit code of the main process, the output size and its tail; output read before
the timeout is kept.
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import signal
import subprocess
import threading
import time
from typing import IO, Any

READ_GRACE_S = 1.5
CHUNK = 65536


def _count_lines(output: bytes) -> int:
    if not output:
        return 0
    return output.count(b"\n") + (0 if output.endswith(b"\n") else 1)


def _reader(stream: IO[bytes], chunks: list[bytes]) -> None:
    fd = stream.fileno()
    while True:
        try:
            data = os.read(fd, CHUNK)
        except OSError:
            return
        if not data:
            return
        chunks.append(data)


def _kill_group(pid: int) -> None:
    try:
        os.killpg(pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        pass


def run(command: str, cwd: str, timeout_s: float, tail_lines: int = 40) -> dict[str, Any]:
    started = time.monotonic()
    proc = subprocess.Popen(
        command,
        shell=True,
        cwd=cwd,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    assert proc.stdout is not None
    chunks: list[bytes] = []
    reader = threading.Thread(target=_reader, args=(proc.stdout, chunks), daemon=True)
    reader.start()

    timed_out = False
    try:
        proc.wait(timeout=timeout_s)
    except subprocess.TimeoutExpired:
        timed_out = True
    _kill_group(proc.pid)
    if timed_out:
        proc.wait()
    reader.join(READ_GRACE_S)
    duration = time.monotonic() - started

    output = b"".join(chunks)
    tail = output.decode("utf-8", errors="replace").splitlines()[-tail_lines:] if tail_lines > 0 else []
    return {
        "command": command,
        "exit_code": None if timed_out else proc.returncode,
        "timed_out": timed_out,
        "duration_s": round(duration, 2),
        "output_bytes": len(output),
        "output_lines": _count_lines(output),
        "tail": "\n".join(tail),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cwd", required=True)
    parser.add_argument("--timeout", type=float, required=True)
    parser.add_argument("--tail-lines", type=int, default=40)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    parts = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not parts:
        parser.error("command is required after --")
    command = parts[0] if len(parts) == 1 else shlex.join(parts)
    print(json.dumps(run(command, args.cwd, args.timeout, args.tail_lines), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
