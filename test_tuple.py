import asyncio
from fastapi import FastAPI, APIRouter
from fastapi.testclient import TestClient
from fastapi.responses import JSONResponse

app = FastAPI()

@app.get('/test')
def test():
    return JSONResponse({"hello": "world"}), 200

client = TestClient(app)
try:
    response = client.get('/test')
    print("Status:", response.status_code)
except Exception as e:
    print("Exception:", type(e), e)
