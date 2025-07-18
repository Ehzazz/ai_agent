from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from .db import get_db
from .models import User, Session
from pydantic import BaseModel
import uuid

router = APIRouter()

class UserRequest(BaseModel):
    username: str
    password: str

class SessionTokenRequest(BaseModel):
    session_token: str

@router.post("/register")
async def register_user(data: UserRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.username == data.username))
    if result.scalar():
        raise HTTPException(status_code=400, detail="Username already exists.")

    new_user = User.create(data.username, data.password)
    db.add(new_user)
    await db.commit()
    return {"message": "✅ User registered successfully", "user_id": new_user.id}

@router.post("/login")
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

@router.post("/logout")
async def logout_user(data: SessionTokenRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Session).where(Session.session_token == data.session_token))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=400, detail="Invalid session token")
    await db.delete(session)
    await db.commit()
    return {"message": "✅ Logout successful"} 