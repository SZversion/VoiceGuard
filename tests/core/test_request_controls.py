from app.core.request_controls import DuplicateJobLock, IpHasher, RateLimiter


def test_ip_hasher_returns_stable_non_raw_key():
    hasher = IpHasher("test-secret")

    first = hasher.hash_ip("127.0.0.1")
    second = hasher.hash_ip("127.0.0.1")

    assert first == second
    assert first != "127.0.0.1"


def test_duplicate_job_lock_allows_one_active_job_per_owner():
    lock = DuplicateJobLock()

    assert lock.acquire("owner-1", "job-1") is True
    assert lock.acquire("owner-1", "job-2") is False
    assert lock.release("owner-1", "job-1") is True
    assert lock.acquire("owner-1", "job-2") is True


def test_rate_limiter_rejects_requests_over_limit():
    limiter = RateLimiter(max_requests=2, window_seconds=60)

    assert limiter.allow("owner-1") is True
    assert limiter.allow("owner-1") is True
    assert limiter.allow("owner-1") is False
    assert limiter.allow("owner-2") is True
