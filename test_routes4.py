import asyncio
from web.api_app import create_app
from fastapi.testclient import TestClient
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

app = create_app()

class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        print("INSIDE PLUGIN APP:", request.scope['path'], request.scope.get('root_path'))
        try:
            response = await call_next(request)
            print("RESPONSE STATUS:", response.status_code)
            return response
        except Exception as e:
            print("EXCEPTION:", e)
            raise e

async def test():
    async with app.router.lifespan_context(app):
        for r in app.routes:
            if getattr(r, 'path', '') == '/api/v1/plugins/2391116200':
                plugin_app = r.app
                plugin_app.add_middleware(LoggingMiddleware)
                
        client = TestClient(app)
        print("GET ->", client.get('/api/v1/plugins/2391116200/settings').status_code)

if __name__ == "__main__":
    asyncio.run(test())
