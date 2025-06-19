from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter
from starlette.middleware.base import BaseHTTPMiddleware

class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware para manejar el rate limiting en toda la aplicación.
    Excluye ciertos endpoints de las limitaciones de tasa.
    """
    
    async def dispatch(self, request: Request, call_next):
        # Excluir documentación y endpoints de salud de rate limiting
        if request.url.path in ["/docs", "/redoc", "/openapi.json", "/health"]:
            return await call_next(request)
            
        try:
            # Verificar límites de tasa
            identifier = request.client.host
            for _, route in request.app.routes:
                if route.matches(request.scope)[0]:
                    for dependency in route.dependencies:
                        if isinstance(dependency, RateLimiter):
                            await FastAPILimiter.check(identifier, dependency)
            return await call_next(request)
            
        except HTTPException as e:
            if e.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={"detail": "Demasiadas solicitudes. Por favor, inténtalo de nuevo más tarde."}
                )
            raise

def setup_rate_limiting(app):
    """
    Configura el middleware de rate limiting en la aplicación FastAPI.
    
    Args:
        app: Instancia de FastAPI
    """
    # Agregar el middleware de rate limiting
    app.add_middleware(RateLimitMiddleware)
    
    # Configurar límites globales
    app.state.limiter = FastAPILimiter(
        key_func=lambda: "global",
        default_limits=["1000 per day", "100 per hour"],
        headers_enabled=True
    )
    
    logger.info("Rate limiting configurado correctamente")
