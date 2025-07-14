from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from mcp.client.stdio import stdio_client
from mcp import ClientSession, StdioServerParameters
import asyncio
from typing import Optional
from contextlib import asynccontextmanager

# ----------------------------
# Request Models
# ----------------------------

class RegisterRequest(BaseModel):
    username: str
    password: str

class LoginRequest(BaseModel):
    username: str
    password: str

class QueryRequest(BaseModel):
    question: str

# ----------------------------
# FastAPI App
# ----------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    global mcp_session
    import os
    server_params = StdioServerParameters(
      command="python",
      args=[os.path.abspath("API/server.py")],
  )
    stdio_transport = await stdio_client(server_params).__aenter__()
    read, write = stdio_transport
    mcp_session = await ClientSession(read, write).__aenter__()
    await mcp_session.initialize()
    yield
    if mcp_session:
        await mcp_session.__aexit__(None, None, None)

app = FastAPI(lifespan=lifespan)

# ----------------------------
# MCP Session Global
# ----------------------------

mcp_session: Optional[ClientSession] = None
session_lock = asyncio.Lock()

# ----------------------------
# Utility function
# ----------------------------

def get_content_text(content_item):
    if hasattr(content_item, "text"):
        return content_item.text
    elif hasattr(content_item, "url"):
        return f"[Media content URL: {content_item.url}]"
    else:
        return str(content_item)

# ----------------------------
# Endpoints
# ----------------------------

@app.post("/register")
async def register(req: RegisterRequest):
    async with session_lock:
        assert mcp_session is not None, "MCP session not initialized"
        result = await mcp_session.call_tool("register_user", req.dict())
    return {
        "result": get_content_text(result.content[0])
    }

@app.post("/login")
async def login(req: LoginRequest):
    assert mcp_session is not None, "MCP session not initialized"
    async with session_lock:
        result = await mcp_session.call_tool("login", req.dict())
    return {
        "result": get_content_text(result.content[0])
    }

@app.post("/query")
async def query(req: QueryRequest):
    assert mcp_session is not None, "MCP session not initialized"
    async with session_lock:
        result = await mcp_session.call_tool("rag_query", req.dict())
    return {
        "result": get_content_text(result.content[0])
    }

@app.get("/history")
async def history():
    async with session_lock:
        assert mcp_session is not None, "MCP session not initialized"
        result = await mcp_session.call_tool("view_history", {})
    # History may return a list of strings
    return {
        "result": [str(r) for r in result.content]
    }
