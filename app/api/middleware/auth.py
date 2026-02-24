import jwt
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from app.utils.logger import principal_id_ctx, setup_logger

logger = setup_logger(__name__)

class AuthMiddleware(BaseHTTPMiddleware):
    """
    Principal-tier Authentication Middleware.
    Validates JWT token, extracts Caller Identity, and injects it into contextvars
    for downstream non-repudiation logging and database auditing.
    """
    def __init__(self, app, secret_key: str = "super-secure-key", algorithms: list = ["HS256"]):
        super().__init__(app)
        self.secret_key = secret_key
        self.algorithms = algorithms

    async def dispatch(self, request: Request, call_next):
        # Allow probes to bypass auth
        if request.url.path in ["/health/live", "/health/ready", "/metrics"]:
            return await call_next(request)

        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            logger.warning("Rejecting unauthenticated request to strict endpoint.")
            return JSONResponse(
                status_code=401,
                content={"detail": "Missing or invalid Authorization header"}
            )

        token = auth_header.split(" ")[1]
        
        try:
            # Decode JWT
            payload = jwt.decode(token, self.secret_key, algorithms=self.algorithms)
            
            # Extract principal
            caller_identity = payload.get("sub", "unknown_caller")
            caller_role = payload.get("role", "guest")
            
            # Bind to request state for other middleware (e.g. Idempotency)
            request.state.caller_identity = caller_identity
            request.state.caller_role = caller_role
            
            # Bind to contextvar for isolated down-stream engine logging
            token_id = principal_id_ctx.set(caller_identity)
            
            response = await call_next(request)
            
            # Cleanup context
            principal_id_ctx.reset(token_id)
            return response
            
        except jwt.ExpiredSignatureError:
            return JSONResponse(status_code=401, content={"detail": "Token expired"})
        except jwt.PyJWTError as e:
            return JSONResponse(status_code=401, content={"detail": f"Invalid token: {str(e)}"})
