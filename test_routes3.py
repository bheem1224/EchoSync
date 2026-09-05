import asyncio

from fastapi.testclient import TestClient

from web.api_app import create_app

app = create_app()


async def test():
    async with app.router.lifespan_context(app):
        for r in app.routes:
            if getattr(r, "path", "") == "/api/v1/plugins/2391116200":
                plugin_app = r.app
                print("Found plugin app mounted at", r.path)

        client = TestClient(app)
        # Try both with and without trailing slash, just in case
        print(
            "GET /api/v1/plugins/2391116200/settings ->",
            client.get("/api/v1/plugins/2391116200/settings").status_code,
        )
        print(
            "GET /api/v1/plugins/2391116200/settings/ ->",
            client.get("/api/v1/plugins/2391116200/settings/").status_code,
        )


if __name__ == "__main__":
    asyncio.run(test())
