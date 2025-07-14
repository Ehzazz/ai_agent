# test_auth.py
import asyncio
from auth import create_user, login_user

async def run():
    # Create user
    result = await create_user("testuser2", "pass123")
    print(result)

    # Try login
    result = await login_user("testuser2", "pass123")
    print(result)

# Run the test
asyncio.run(run())
