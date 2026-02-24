from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import redis.asyncio as aioredis
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

class IdempotencyMiddleware(BaseHTTPMiddleware):
    """
    Middleware tracking X-Idempotency-Key against Redis to prevent execution storms.
    Implements a fast-failing throttle for duplicated in-flight requests.
    """
    def __init__(self, app, redis_client: aioredis.Redis, ttl: int = 300):
        super().__init__(app)
        self.redis = redis_client
        self.ttl = ttl

    async def dispatch(self, request: Request, call_next):
        # We only care about mutation / execution endpoints
        if request.url.path not in ["/v1/gates/deploy", "/health/run"] or request.method != "POST":
            return await call_next(request)
            
        idempotency_key = request.headers.get("X-Idempotency-Key")
        if not idempotency_key:
            # If no key, we let it pass, but in strict mode we could deny it.
            return await call_next(request)
            
        # Bind key uniqueness to the principal if available
        caller_identity = getattr(request.state, "caller_identity", "anonymous")
        redis_key = f"idem:{caller_identity}:{idempotency_key}"
        
        try:
            # Atomic setnx to acquire the lock
            is_new = await self.redis.set(redis_key, "IN_FLIGHT", ex=self.ttl, nx=True)
            if not is_new:
                status = await self.redis.get(redis_key)
                if status == "IN_FLIGHT":
                    logger.warning(f"Concurrent execution blocked for idempotency key: {idempotency_key}")
                    return JSONResponse(
                        status_code=409, 
                        content={"detail": "Request already in progress. Please wait."}
                    )
                else:
                    logger.info(f"Returning cached idempotent response for {idempotency_key}")
                    import json
                    return JSONResponse(status_code=200, content=json.loads(status))

            # Proceed with the actual request
            response = await call_next(request)
            
            # If it's a 200/503 (completed validations), cache the response payload
            if response.status_code in [200, 503]:
                # We need to extract the streaming response body
                body = [section async for section in response.body_iterator]
                response.body_iterator = _AsyncIteratorWrapper(body)
                
                payload = b"".join(body).decode()
                await self.redis.set(redis_key, payload, ex=self.ttl)
            else:
                # If it failed due to some other error, delete the lock so they can retry
                await self.redis.delete(redis_key)
                
            return response
            
        except Exception as e:
            # Fail-open
            logger.error(f"Idempotency Redis exception: {e}. Failing open.")
            return await call_next(request)

class _AsyncIteratorWrapper:
    """Wrapper to restream the body back to FastAPI after reading it for Redis."""
    def __init__(self, obj):
        self._it = iter(obj)
    def __aiter__(self):
        return self
    async def __anext__(self):
        try:
            return next(self._it)
        except StopIteration:
            raise StopAsyncIteration
