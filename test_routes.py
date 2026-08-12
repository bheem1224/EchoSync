import asyncio
from web.api_app import create_app
from fastapi.testclient import TestClient

app = create_app()

async def test():
    async with app.router.lifespan_context(app):
        # The lifespan will mount the plugins
        client = TestClient(app)
        response = client.get('/api/v1/plugins/2391116200/settings')
        print("Status code:", response.status_code)
        print("Response:", response.text)
        
        # Let's inspect the plugin_app
        for r in app.routes:
            if getattr(r, 'path', '') == '/api/v1/plugins/2391116200':
                plugin_app = r.app
                print("Plugin app routes:")
                for pr in plugin_app.routes:
                    print(getattr(pr, 'path', repr(pr)))

asyncio.run(test())
