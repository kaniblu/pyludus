import os
import sys
import select
import logging
import subprocess
from itertools import chain
from dataclasses import dataclass
from typing import Sequence, Mapping, IO


class ProcessError(Exception):
    pass


@dataclass
class NonBlockingReadingIO:
    f: IO
    buffer_size: int = 512
    _poll: select.poll = None

    def __post_init__(self):
        self._poll = select.poll()
        self._poll.register(self.f, select.POLLIN)

    def read(self, n: int = None) -> bytes:
        ret = b''
        if n is None:
            while self._poll.poll(1):
                ret += os.read(self.f.fileno(), self.buffer_size)
        else:
            while self._poll.poll(1):
                r = os.read(self.f.fileno(), min(self.buffer_size, n))
                n -= len(r)
                ret += r
        return ret


@dataclass
class Process:
    args: Sequence[str]
    cwd: str = "/"
    inherit_env: bool = True
    aux_env: Mapping[str, str] = None
    aux_paths: Sequence[str] = None
    _process: subprocess.Popen = None
    _logger: logging.Logger = None
    _stderr: NonBlockingReadingIO = None

    def __post_init__(self):
        self._logger = logging.Logger(self.__class__.__name__)

    def create_env(self) -> Mapping[str, str]:
        env = dict()
        if self.inherit_env:
            env.update(os.environ.copy())
            env["PATH"] = ":".join((":".join(sys.path), env["PATH"]))
        if self.aux_env is not None:
            env.update(self.aux_env)
        if self.aux_paths is not None:
            env["PATH"] = ":".join(chain(self.aux_paths, [env["PATH"]]))
        return env

    def open(self):
        if self._process is not None:
            raise ProcessError(f"this object has already run once; create "
                               f"a new process object to run")
        self._process = subprocess.Popen(
            self.args,
            env=self.create_env(),
            cwd=self.cwd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        self._stderr = NonBlockingReadingIO(self._process.stderr)

    def run_sync(self):
        self.open()
        try:
            return self.wait()
        except ProcessError as e:
            return self._process.returncode

    def __enter__(self):
        self.open()
        return self

    def is_run(self):
        return self._process is not None

    def check_run(self):
        if not self.is_run():
            raise ProcessError(f"no process is running yet; call `self.open()`"
                               f"to spawn a new process")

    def is_alive(self):
        self.check_run()
        return self._process.poll() is None

    def check_alive(self):
        if not self.is_alive():
            raise ProcessError(f"process has terminated; create a new object "
                               f"and run again")

    def wait(self, timeout=None):
        self.check_run()
        self._process.wait(timeout)
        return self._process.returncode

    def close(self, kill=False):
        self.check_alive()
        if kill:
            return self._process.kill()
        else:
            return self._process.terminate()

    def write(self, data: bytes) -> int:
        self.check_alive()
        ret = self._process.stdin.write(data)
        self._process.stdin.flush()
        return ret

    def read(self, n: int = None) -> bytes:
        self.check_run()
        return self._process.stdout.read(n)

    def read_error(self, n: int = None) -> bytes:
        self.check_run()
        return self._stderr.read(n)

    def readline(self, limit: int = None) -> bytes:
        self.check_run()
        return self._process.stdout.readline(limit)

    def read_str(self, n: int = None, enc: str = "utf-8") -> str:
        return self.read(n).decode(enc)

    def readline_str(self, limit: int = None, enc: str = "utf-8") -> str:
        return self.readline(limit).decode(enc)

    def write_str(self, data: str, enc: str = "utf-8") -> int:
        return self.write(data.encode(enc))

    def __exit__(self, exc_type, exc_val, exc_tb):
        if not self.is_alive():
            return
        try:
            self.close()
        except ProcessError as e:
            self._logger.error(f"failed to gracefully close the process")
            self._logger.exception(e)

    def return_code(self) -> int:
        if not (self.is_run() and not self.is_alive()):
            raise ProcessError(f"process has yet to terminate")
        return self._process.poll()
