import time
from collections import defaultdict
from typing import Dict, Tuple

class RateLimiter:
    def __init__(self, max_requests: int = 60, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window = window_seconds
        self._requests: Dict[str, list] = defaultdict(list)
    
    def is_allowed(self, client_id: str) -> Tuple[bool, int]:
        now = time.monotonic()
        reqs = self._requests[client_id]
        
        # Limpiar requests viejos
        reqs[:] = [t for t in reqs if now - t < self.window]
        
        if len(reqs) >= self.max_requests:
            return False, 0
            
        reqs.append(now)
        return True, max(self.max_requests - len(reqs), 0)

    def clear(self) -> None:
        self._requests.clear()
