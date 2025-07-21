from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from .db import get_db
from .models import Session, ChatHistory
from pydantic import BaseModel
from main import rag_agent
import asyncio
from typing import Optional

router = APIRouter()

class QuestionRequest(BaseModel):
    question: str
    session_token: str
    file_name: Optional[str] = None

@router.post("/query")
async def query_rag(data: QuestionRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Session).where(Session.session_token == data.session_token))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=401, detail="Invalid or expired session token")

    context_docs = session.context_docs or []

    # Convert dicts back to Document objects if needed
    from langchain_core.documents import Document
    def dict_to_doc(d):
        return Document(page_content=d.get("page_content", ""), metadata=d.get("metadata", {}))
    context_docs = [dict_to_doc(doc) if isinstance(doc, dict) else doc for doc in context_docs]

    # Prepare filter for vectorstore retrieval
    filter_metadata = {"user_id": session.user_id}
    if data.file_name:
        filter_metadata["file_name"] = data.file_name  # type: ignore

    # Run the agent, passing in the accumulated context and filter
    result = await asyncio.to_thread(rag_agent.invoke, {
        "question": data.question,
        "context_docs": context_docs,
        "answer": "",
        "user_id": session.user_id,
        "filter_metadata": filter_metadata
    })
    answer = result["answer"]
    new_context_docs = result["context_docs"]

    # Convert Document objects to dicts before saving
    def doc_to_dict(doc):
        return {
            "page_content": getattr(doc, "page_content", None),
            "metadata": getattr(doc, "metadata", None)
        }
    new_context_docs = [doc_to_dict(doc) for doc in new_context_docs]

    session.context_docs = new_context_docs  # type: ignore
    db.add(session)
    chat = ChatHistory(user_id=session.user_id, question=data.question, answer=answer)
    db.add(chat)
    await db.commit()
    return {"answer": answer}

@router.get("/chat-history")
async def get_history(session_token: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Session).where(Session.session_token == session_token))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=401, detail="Invalid session token")

    result = await db.execute(
        select(ChatHistory)
        .where(ChatHistory.user_id == session.user_id)
        .order_by(ChatHistory.created_at.asc())
        .limit(20)
    )
    history = result.scalars().all()
    response = []
    for h in history:
        response.append({"sender": "user", "message": h.question})
        response.append({"sender": "agent", "message": h.answer})
    return response 