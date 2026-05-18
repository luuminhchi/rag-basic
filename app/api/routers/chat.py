# app/api/routers/chat.py
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services.search import perform_hybrid_search

router = APIRouter()

class ChatRequest(BaseModel):
    query: str
    vehicle_type: str = None

@router.post("/chat")
def chat_with_bot(request: ChatRequest, db: Session = Depends(get_db)):
    # 1. Gọi service search
    chunks = perform_hybrid_search(db, query=request.query, filter_vehicle=request.vehicle_type)
    
    # 2. Gọi LLM
    # answer = llm_service.generate_answer(request.query, chunks)
    
    return {"answer": "...", "sources": chunks}