# app/models.py
from sqlalchemy import Column, String, Text, ForeignKey, DateTime, LargeBinary
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base, relationship
import uuid
import datetime
import hashlib

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)

    def check_password(self, password: str) -> bool:
        stored = str(self.password_hash)  # Convert Column object to string value
        return stored == hashlib.sha256(password.encode()).hexdigest()


    @classmethod
    def create(cls, username, password):
        import hashlib, uuid
        user_id = f"user_{uuid.uuid4().hex[:8]}"
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        return cls(id=user_id, username=username, password_hash=password_hash)

class Session(Base):
    __tablename__ = "sessions"
    session_token = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"))

class UserFile(Base):
    __tablename__ = "user_files"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String, ForeignKey("users.id"))
    file_name = Column(String)
    file_type = Column(String)
    file_data = Column(LargeBinary)  # Use LargeBinary or BYTEA for binary data

class ChatHistory(Base):
    __tablename__ = "chat_history"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String, ForeignKey("users.id"))
    question = Column(Text)
    answer = Column(Text)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
