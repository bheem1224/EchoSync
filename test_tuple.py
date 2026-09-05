from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

app = FastAPI()


@app.get("/test")
def test():
    return JSONResponse({"hello": "world"}), 200


client = TestClient(app)
try:
    response = client.get("/test")
    print("Status:", response.status_code)
except Exception as e:
    print("Exception:", type(e), e)
