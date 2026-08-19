import hashlib
import hmac
import time
from collections import defaultdict, deque
from threading import RLock


class IpHasher:
    def __init__(self, secret: str):
        self.secret = secret.encode("utf-8")

    def hash_ip(self, ip_address: str) -> str:
        return hmac.new(self.secret, ip_address.encode("utf-8"), hashlib.sha256).hexdigest()


class DuplicateJobLock:
    def __init__(self):
        self._jobs: dict[str, str] = {}
        self._lock = RLock()

    def acquire(self, owner_key: str, job_id: str) -> bool:
        with self._lock:
            if owner_key in self._jobs:
                return False
            self._jobs[owner_key] = job_id
            return True

    def is_locked(self, owner_key: str) -> bool:
        with self._lock:
            return owner_key in self._jobs

    def release(self, owner_key: str, job_id: str) -> bool:
        with self._lock:
            if self._jobs.get(owner_key) != job_id:
                return False
            del self._jobs[owner_key]
            return True


class RateLimiter:
    def __init__(self, max_requests: int, window_seconds: float):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: dict[str, deque[float]] = defaultdict(deque)
        self._lock = RLock()

    def allow(self, owner_key: str) -> bool:
        now = time.monotonic()
        with self._lock:
            timestamps = self._requests[owner_key]
            while timestamps and now - timestamps[0] >= self.window_seconds:
                timestamps.popleft()
            if len(timestamps) >= self.max_requests:
                return False
            timestamps.append(now)
            return True
