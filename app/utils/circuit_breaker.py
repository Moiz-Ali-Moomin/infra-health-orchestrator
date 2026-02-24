import time
from enum import Enum
from abc import ABC, abstractmethod
import redis.asyncio as aioredis
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

class CBState(Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"

class CircuitBreaker(ABC):
    @abstractmethod
    async def record_failure(self): pass
    @abstractmethod
    async def record_success(self): pass
    @abstractmethod
    async def can_execute(self) -> bool: pass

class RedisCircuitBreaker(CircuitBreaker):
    """Distributed state-machine for protecting downstream dependencies."""
    
    # Lua script to atomically increment failure and open circuit if threshold breached
    _LUA_RECORD_FAILURE = """
    local key_count = KEYS[1]
    local key_state = KEYS[2]
    local key_time = KEYS[3]
    local threshold = tonumber(ARGV[1])
    local now = tonumber(ARGV[2])

    local count = redis.call('INCR', key_count)
    redis.call('SET', key_time, now)

    if count >= threshold then
        redis.call('SET', key_state, 'OPEN')
    end
    return count
    """
    
    def __init__(self, redis_client: aioredis.Redis, domain: str, failure_threshold: int = 3, recovery_timeout_sec: int = 30):
        self.redis = redis_client
        self.domain = domain
        self.failure_threshold = failure_threshold
        self.recovery_timeout_sec = recovery_timeout_sec
        
        self.k_count = f"cb:{domain}:fail_count"
        self.k_state = f"cb:{domain}:state"
        self.k_time = f"cb:{domain}:last_fail_time"
        
        # Pre-load Lua Script
        self.script_failure = self.redis.register_script(self._LUA_RECORD_FAILURE)

    async def record_failure(self):
        try:
            now = int(time.time())
            await self.script_failure(
                keys=[self.k_count, self.k_state, self.k_time],
                args=[self.failure_threshold, now]
            )
        except Exception as e:
            logger.error(f"Redis CB Error ({self.domain}): {e}")

    async def record_success(self):
        try:
            await self.redis.mset({
                self.k_count: 0,
                self.k_state: CBState.CLOSED.value
            })
        except Exception:
            pass # Fail open

    async def can_execute(self) -> bool:
        try:
            state, last_time = await self.redis.mget(self.k_state, self.k_time)
            if not state or state == CBState.CLOSED.value:
                return True
                
            if state == CBState.OPEN.value:
                now = int(time.time())
                last_time = int(last_time) if last_time else 0
                if now - last_time > self.recovery_timeout_sec:
                    await self.redis.set(self.k_state, CBState.HALF_OPEN.value)
                    return True
                return False
                
            return True # HALF_OPEN
        except Exception as e:
            logger.warning(f"Redis CB fail-open fallback active for {self.domain}: {e}")
            return True # Degraded state, fail-open to allow traffic

class CircuitBreakerFactory:
    def __init__(self, redis_client: aioredis.Redis):
        self.redis = redis_client
        
    def get_breaker(self, domain: str) -> CircuitBreaker:
        return RedisCircuitBreaker(self.redis, domain)
