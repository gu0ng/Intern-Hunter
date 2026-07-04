from app.config import settings


class JobCacheTool:
    name = "job_cache_tool"
    description = "Optional Redis cache for jd_hash to job_id mapping. Falls back silently when Redis is unavailable."

    def __init__(self) -> None:
        self._client = None
        self._available = False
        if not settings.enable_redis_cache:
            return
        try:
            import redis

            self._client = redis.Redis.from_url(settings.redis_url, decode_responses=True, socket_connect_timeout=0.5, socket_timeout=0.5)
            self._client.ping()
            self._available = True
        except Exception:
            self._client = None
            self._available = False

    @property
    def available(self) -> bool:
        return self._available

    def get_job_id(self, jd_hash: str) -> int | None:
        if not self._available or self._client is None:
            return None
        try:
            value = self._client.get(self._key(jd_hash))
            return int(value) if value else None
        except Exception:
            return None

    def set_job_id(self, jd_hash: str, job_id: int) -> None:
        if not self._available or self._client is None:
            return
        try:
            self._client.setex(self._key(jd_hash), settings.job_cache_ttl_seconds, str(job_id))
        except Exception:
            return

    def _key(self, jd_hash: str) -> str:
        return f"intern-hunter:job-match:{jd_hash}"
