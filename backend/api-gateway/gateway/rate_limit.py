import time
from collections import defaultdict, deque
from dataclasses import dataclass, field


@dataclass
class SlidingWindowRateLimiter:
    max_requests: int
    window_seconds: int
    _hits: dict[str, deque[float]] = field(default_factory=lambda: defaultdict(deque))

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        window_start = now - self.window_seconds
        hits = self._hits[key]
        while hits and hits[0] <= window_start:
            hits.popleft()
        if len(hits) >= self.max_requests:
            return False
        hits.append(now)
        return True
