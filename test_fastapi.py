from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

app = FastAPI()
router = APIRouter()


@router.get("/settings")
def settings():
    return {"hello": "world"}


plugin_app = FastAPI()
plugin_app.include_router(router)
plugin_app.include_router(router)

app.mount("/api/v1/plugins/123", plugin_app)

client = TestClient(app)
response = client.get("/api/v1/plugins/123/settings")
print("Status:", response.status_code)
print("Response:", response.text)
