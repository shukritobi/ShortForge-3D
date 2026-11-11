"""OS-held GPU slot shared by Studio jobs across server restarts."""
import os
from contextlib import contextmanager


@contextmanager
def studio_job_slot():
    path = os.environ.get("SHORTFORGE_STUDIO_JOB_LOCK")
    if not path:
        yield
        return
    with open(path, "a+b") as lock:
        lock.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise RuntimeError("A Studio job from this or an earlier server is still running. Retry when it exits.") from exc
        yield
