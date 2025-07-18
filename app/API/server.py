import os
import uuid
import asyncio
import io
import tempfile
import json

from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import JSON

from .db import get_db
from .models import User, Session, UserFile, ChatHistory
from main import rag_agent
from langchain_community.document_loaders import PyPDFLoader, TextLoader, UnstructuredWordDocumentLoader, UnstructuredExcelLoader, UnstructuredPowerPointLoader
from utils.embedding_utils import embed_pdf, embed_docx, embed_ppt
from utils.file_processing import get_file_type, process_file

app = FastAPI(title="EQS RAG Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------------------
# Request models
# ----------------------------
class UserRequest(BaseModel):
    username: str
    password: str

class QuestionRequest(BaseModel):
    question: str
    session_token: str

class SessionTokenRequest(BaseModel):
    session_token: str

# ----------------------------
# Auth & Session Endpoints
# ----------------------------
@app.post("/register")
async def register_user(data: UserRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.username == data.username))
    if result.scalar():
        raise HTTPException(status_code=400, detail="Username already exists.")

    new_user = User.create(data.username, data.password)
    db.add(new_user)
    await db.commit()
    return {"message": "✅ User registered successfully", "user_id": new_user.id}

@app.post("/login")
async def login_user(data: UserRequest, db: AsyncSession = Depends(get_db)):
    stmt = select(User).where(User.username == data.username)
    result = await db.execute(stmt)
    user = result.scalar()

    if user is None or not user.check_password(data.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = uuid.uuid4().hex
    session = Session(session_token=token, user_id=user.id)
    db.add(session)
    await db.commit()
    return {"message": "✅ Login successful", "session_token": token}


@app.post("/logout")
async def logout_user(data: SessionTokenRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Session).where(Session.session_token == data.session_token))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=400, detail="Invalid session token")
    await db.delete(session)
    await db.commit()
    return {"message": "✅ Logout successful"}

# ----------------------------
# Upload and Embed File
# ----------------------------
@app.post("/upload-and-embed")
async def upload_and_embed(session_token: str = Form(...), file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Session).where(Session.session_token == session_token))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=401, detail="Invalid session token")

    user_id = session.user_id
    filename = file.filename

    # Read file ONCE
    content = await file.read()

    file_type = get_file_type(filename, content)
    if file_type not in ['pdf', 'docx', 'ppt']:
        return JSONResponse({"message": "Only PDF, DOCX, and PPT/PPTX files are supported at this time."}, status_code=400)

    user_file = UserFile(
        user_id=user_id,
        file_name=filename,
        file_type=file.content_type,
        file_data=content
    )
    db.add(user_file)
    await db.commit()

    try:
        pages = process_file(filename, content)
        if file_type == 'pdf':
            embed_pdf(io.BytesIO(content), metadata={
                "user_id": user_id,
                "file_name": filename
            })
        elif file_type == 'docx':
            embed_docx(io.BytesIO(content), metadata={
                "user_id": user_id,
                "file_name": filename
            })
        elif file_type == 'ppt':
            embed_ppt(io.BytesIO(content), metadata={
                "user_id": user_id,
                "file_name": filename
            })
        return {"message": f"✅ File '{filename}' uploaded & embedded successfully."}
    except Exception as e:
        import traceback
        print("Exception during file processing:", e)
        traceback.print_exc()
        return JSONResponse({"message": f"File processing failed: {str(e)}"}, status_code=400)

# ----------------------------
# Query RAG Agent
# ----------------------------
@app.post("/query")
async def query_rag(data: QuestionRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Session).where(Session.session_token == data.session_token))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=401, detail="Invalid or expired session token")

    # Load context_docs from session (deserialize if needed)
    context_docs = session.context_docs or []

    # Run the agent, passing in the accumulated context
    result = await asyncio.to_thread(rag_agent.invoke, {
        "question": data.question,
        "context_docs": context_docs,
        "answer": "",
        "user_id": session.user_id
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

    # Update session context_docs
    session.context_docs = new_context_docs  # type: ignore
    db.add(session)
    chat = ChatHistory(user_id=session.user_id, question=data.question, answer=answer)
    db.add(chat)
    await db.commit()
    return {"answer": answer}

# ----------------------------
# View Chat History
# ----------------------------
@app.get("/chat-history")
async def get_history(session_token: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Session).where(Session.session_token == session_token))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=401, detail="Invalid session token")

    result = await db.execute(
        select(ChatHistory)
        .where(ChatHistory.user_id == session.user_id)
        .order_by(ChatHistory.created_at.asc())  # keep in order
        .limit(20)
    )
    history = result.scalars().all()

    result = []
    for h in history:
        result.append({"sender": "user", "message": h.question})
        result.append({"sender": "agent", "message": h.answer})
    return result

@app.get("/")
def root():
    return {"message": "API is running"}