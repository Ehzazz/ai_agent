from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from .db import get_db
from .models import Session, ChatHistory
from pydantic import BaseModel
from main import rag_agent
import asyncio
from typing import Optional
import uuid

router = APIRouter()

class QuestionRequest(BaseModel):
    question: str
    session_token: str
    file_id: Optional[str] = None  # Use file_id for filtering
    # file_name: Optional[str] = None  # Remove or deprecate

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
    filter_metadata = {
        "user_id": {"$eq": session.user_id}
    }
    if data.file_id:
        filter_metadata["file_id"] = {"$eq": data.file_id}  # type: ignore
    # Remove file_name fallback, as it is not present in the model

    # Set first_question if not already set
    if session.first_question is None:
        setattr(session, "first_question", data.question)
        print("Set first_question:", session.first_question)

    # Build conversation context from previous Q&A in this session
    history_result = await db.execute(
        select(ChatHistory)
        .where(ChatHistory.session_token == session.session_token)
        .order_by(ChatHistory.created_at.asc())
    )
    history = history_result.scalars().all()
    conversation_context = ""
    for h in history:
        conversation_context += f"User: {h.question}\nAI: {h.answer}\n"
    # Add the new question
    conversation_context += f"User: {data.question}\nAI:"

    # Run the agent, passing in the accumulated context and filter
    result = await asyncio.to_thread(rag_agent.invoke, {
        "question": conversation_context,
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

    setattr(session, "context_docs", new_context_docs)  # type: ignore
    db.add(session)
    chat = ChatHistory(user_id=session.user_id, session_token=session.session_token, question=data.question, answer=answer)
    db.add(chat)
    await db.commit()
    return {"answer": answer}

@router.post("/new-session")
async def new_session(data: dict, db: AsyncSession = Depends(get_db)):
    # Get the current session
    old_token = data.get("session_token")
    result = await db.execute(select(Session).where(Session.session_token == old_token))
    old_session = result.scalar_one_or_none()
    if not old_session:
        raise HTTPException(status_code=401, detail="Invalid session token")
    # Create a new session for the same user
    new_token = uuid.uuid4().hex
    new_session = Session(session_token=new_token, user_id=old_session.user_id, context_docs=[])
    db.add(new_session)
    await db.commit()
    return {"session_token": new_token}

@router.get("/sessions")
async def list_sessions(session_token: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Session).where(Session.session_token == session_token))
    current_session = result.scalar_one_or_none()
    if not current_session:
        raise HTTPException(status_code=401, detail="Invalid session token")
    result = await db.execute(
        select(Session)
        .where(Session.user_id == current_session.user_id)
        .order_by(Session.first_question.isnot(None).desc(), Session.context_docs.isnot(None).desc())
    )
    sessions = result.scalars().all()
    return [{"session_token": s.session_token, "first_question": s.first_question} for s in sessions]

@router.get("/chat-history-by-session")
async def get_history_by_session(session_token: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ChatHistory)
        .where(ChatHistory.session_token == session_token)
        .order_by(ChatHistory.created_at.asc())
    )
    history = result.scalars().all()
    messages = []
    for h in history:
        messages.append({"id": str(h.id), "sender": "user", "message": h.question})
        messages.append({"id": str(h.id), "sender": "agent", "message": h.answer})
    return messages

@router.delete("/chat-history/{history_id}")
async def delete_chat_history(history_id: str, session_token: str, db: AsyncSession = Depends(get_db)):
    # Verify the user owns the session
    session_result = await db.execute(select(Session).where(Session.session_token == session_token))
    session = session_result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=401, detail="Invalid session token")

    # Find the chat history entry
    history_result = await db.execute(select(ChatHistory).where(ChatHistory.id == history_id, ChatHistory.user_id == session.user_id))
    history_entry = history_result.scalar_one_or_none()

    if not history_entry:
        raise HTTPException(status_code=404, detail="Chat history not found or access denied")

    await db.delete(history_entry)
    await db.commit()
    return {"message": "Chat history deleted successfully"} 