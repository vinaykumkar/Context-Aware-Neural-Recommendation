"""Cache layer: Redis when available, in-memory fallback otherwise.

The app must keep working when the Redis server is not installed/running,
so every failure degrades gracefully to a small Python dict cache with TTL.
Status is exposed for the demo UI:
    Redis: Connected
    Redis: Offline - using in-memory fallback
"""

import json
import time

from src import config

try:
    import redis as redis_lib

    REDIS_LIB_AVAILABLE = True
except ImportError:  # pragma: no cover
    REDIS_LIB_AVAILABLE = False


class CacheClient:
    def __init__(self, host: str = config.REDIS_HOST, port: int = config.REDIS_PORT):
        self._redis = None
        self._memory = {}  # key -> (expiry_ts, value)
        self.status = "Offline - using in-memory fallback"
        if REDIS_LIB_AVAILABLE:
            try:
                client = redis_lib.Redis(
                    host=host, port=port, socket_connect_timeout=1,
                    socket_timeout=1, decode_responses=True,
                )
                client.ping()
                self._redis = client
                self.status = "Connected"
            except Exception:
                self._redis = None

    @property
    def backend(self) -> str:
        return "Redis" if self._redis is not None else "Memory"

    # ------------------------------------------------------------ ops
    def get(self, key: str):
        if self._redis is not None:
            raw = self._redis.get(key)
            return json.loads(raw) if raw is not None else None
        item = self._memory.get(key)
        if item is None:
            return None
        expiry, value = item
        if expiry is not None and time.time() > expiry:
            self._memory.pop(key, None)
            return None
        return value

    def set(self, key: str, value, ttl: int = config.REDIS_TTL_SECONDS) -> None:
        payload = json.dumps(value)
        if self._redis is not None:
            self._redis.set(key, payload, ex=ttl)
        else:
            expiry = time.time() + ttl if ttl else None
            self._memory[key] = (expiry, value)

    def clear_local(self) -> None:
        """Clears only the in-memory fallback cache (used by the demo)."""
        self._memory.clear()

    # ------------------------------------------------------------ keys
    @staticmethod
    def user_features_key(customer_id: str) -> str:
        return f"user_features:{customer_id}"

    @staticmethod
    def recommendations_key(customer_id: str, k: int) -> str:
        return f"recommendations:{customer_id}:k{k}"
