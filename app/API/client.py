from mcp.client.stdio import stdio_client
from mcp import ClientSession, StdioServerParameters
import asyncio

async def main():
    server_params = StdioServerParameters(
        command="python",
        args=["API/server.py"],  # Make sure this path is correct
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # List tools
            tools = await session.list_tools()
            print("\n✅ Available Tools:")
            for tool in tools.tools:
                print(f"- {tool.name}: {tool.description}")

            # Register the user 'azaz' with password '1234'
            register_result = await session.call_tool("register_user", {
                "username": "az21",
                "password": "1234"
            })
            print("\n✅ Register Result:")
            text = getattr(register_result.content[0], "text", None)
            if text is not None:
                print("-", text)
            else:
                print("-", register_result.content[0])

            # Login with the same credentials
            login_result = await session.call_tool("login", {
                "username": "az21",
                "password": "1234"
            })
            print("\n✅ Login Result:")
            text = getattr(login_result.content[0], "text", None)
            if text is not None:
                print("-", text)
            else:
                print("-", login_result.content[0])

            # Run a RAG query
            rag_result = await session.call_tool("rag_query", {
                "question": "What can you tell me about LangChain?"
            })
            print("\n✅ RAG Query Result:")
            text = getattr(rag_result.content[0], "text", None)
            if text is not None:
                print("-", text)
            else:
                print("-", rag_result.content[0])

            # View user history
            history_result = await session.call_tool("view_history", {})
            print("\n✅ View History Result:")
            for entry in history_result.content:
                text = getattr(entry, "text", None)
                if text is not None:
                    print("-", text)
                else:
                    print("-", entry)

if __name__ == "__main__":
    asyncio.run(main())
