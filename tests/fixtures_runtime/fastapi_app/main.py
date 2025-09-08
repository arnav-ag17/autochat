"""
Simple FastAPI application for testing.
"""

from fastapi import FastAPI

app = FastAPI(title="Test FastAPI App")

@app.get("/")
def read_root():
    return {"message": "Hello from FastAPI!", "status": "ok"}

@app.get("/health")
def health_check():
    return {"status": "ok", "health": "healthy"}

@app.get("/api/message")
def api_message():
    return {"message": "Hello from FastAPI API!", "data": "test"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
