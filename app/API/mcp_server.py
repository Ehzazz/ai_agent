# import sys
# import os
# import asyncio
# import logging
# from typing import Annotated
# from mcp.server import Server, NotificationOptions
# from mcp.server.models import InitializationOptions
# from mcp.types import (
#     Resource,
#     Tool,
#     TextContent,
#     ImageContent,
#     EmbeddedResource,
#     GetPromptResult,
#     Prompt,
#     PromptMessage,
#     PromptArgument
# )
# import mcp.server.stdio
# import auth
# from mcp.server.fastmcp import FastMCP


# # Add root to sys path
# sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# # RAG agent from main.py
# from main import rag_agent

# # ============================================================
# # Initialize MCP Server
# # ============================================================
# mcp = FastMCP("eqs_rag_server")

# # ============================================================
# # List tools
# # ============================================================
# @mcp.tool()
# async def register_user(username: str, password: str) -> str:
#     return await auth.create_user(username, password)

# @mcp.tool()
# async def login_user(username: str, password: str) -> str:
#     return await auth.login_user(username, password)

# @mcp.tool()
# def logout_user(session_token: str) -> str:
#     return auth.logout_user(session_token)

# @mcp.tool()
# async def rag_query(question: str) -> str:
#     if not auth.CURRENT_SESSION_USER_ID:
#         return "❌ No user is currently logged in. Please login first."
#     user_id = auth.CURRENT_SESSION_USER_ID
#     result = await asyncio.to_thread(
#         rag_agent.invoke,
#         {
#             "question": question,
#             "context_docs": [],
#             "answer": ""
#         }
#     )
#     return result["answer"]

# @mcp.tool()
# def view_history() -> list:
#     if not auth.CURRENT_SESSION_USER_ID:
#         return ["No user is currently logged in. Please login first."]
#     return auth.get_history_by_user_id(auth.CURRENT_SESSION_USER_ID)

# # ============================================================
# # Main function to run STDIO server
# # ============================================================
# if __name__ == "__main__":
#     mcp.run(transport="stdio")
