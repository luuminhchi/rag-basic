# app/main.py
from fastapi import FastAPI
from app.api.routers import chat

app = FastAPI(title="Traffic Law RAG API", version="1.0")

# Gắn cái router xử lý chat vào
app.include_router(chat.router, prefix="/api/v1")

@app.get("/health")
def health_check():
    return {"status": "ok", "message": "Hệ thống RAG đang chạy!"}