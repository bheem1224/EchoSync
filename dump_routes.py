from web.api_app import create_app
app = create_app()

def print_routes(app_or_router, prefix=""):
    for r in app_or_router.routes:
        if hasattr(r, 'path'):
            print(f"{prefix}{r.path} -> {type(r).__name__} (name: {getattr(r, 'name', 'None')})")
        elif hasattr(r, 'app'):  # Mount
            print(f"{prefix}{getattr(r, 'path', repr(r))} -> Mount")
            if hasattr(r.app, 'routes'):
                print_routes(r.app, prefix + "  ")

print_routes(app)
