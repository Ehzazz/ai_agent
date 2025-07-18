import os
import uuid
import asyncio
import io
import tempfile
import json

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .auth import router as auth_router
from .chat import router as chat_router
from .file import router as file_router

app = FastAPI(title="RAG Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(file_router)

@app.get("/")
def root():
    return {"message": "API is running"}