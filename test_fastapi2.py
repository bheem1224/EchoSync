import asyncio
from fastapi import FastAPI, APIRouter, Depends, Request
from fastapi.testclient import TestClient

async def enforce_plugin_passport(request: Request):
    pass

app = FastAPI()
router = APIRouter()

@router.get('/settings')
def settings():
    return {"hello": "world"}

plugin_app = FastAPI(dependencies=[Depends(enforce_plugin_passport)])
plugin_app.include_router(router)

app.mount('/api/v1/plugins/123', plugin_app)

client = TestClient(app)
response = client.get('/api/v1/plugins/123/settings')
print("Status:", response.status_code)
print("Response:", response.text)
