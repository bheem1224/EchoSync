import asyncio

from web.api_app import create_app

app = create_app()


async def test():
    async with app.router.lifespan_context(app):
        for r in app.routes:
            if getattr(r, "path", "") == "/api/v1/plugins/2391116200":
                plugin_app = r.app
                print("Plugin app routes:")
                for pr in plugin_app.routes:
                    if type(pr).__name__ == "_IncludedRouter":
                        for rr in pr.original_router.routes:
                            print(getattr(rr, "path", rr.name))


if __name__ == "__main__":
    asyncio.run(test())
