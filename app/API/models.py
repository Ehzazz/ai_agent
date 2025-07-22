# app/models.py
from sqlalchemy import Column, String, Text, ForeignKey, DateTime, LargeBinary, JSON
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import declarative_base, relationship
import uuid
import datetime
import hashlib
from pgvector.sqlalchemy import Vector

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
    context_docs = Column(JSON, default=list)
    first_question = Column(Text, nullable=True)

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
    session_token = Column(String, nullable=True)  # Not a foreign key, for flexibility
    question = Column(Text)
    answer = Column(Text)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class LangchainPGCollection(Base):
    __tablename__ = "langchain_pg_collection"
    uuid = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, unique=True, nullable=False)
    cmetadata = Column(JSON)

class LangchainPGEmbedding(Base):
    __tablename__ = "langchain_pg_embedding"
    uuid = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    collection_id = Column(UUID(as_uuid=True), ForeignKey("langchain_pg_collection.uuid"))
    embedding = Column(Vector(384))  # Change 1536 to your embedding dimension if different
    document = Column(Text)
    cmetadata = Column(JSONB)
    custom_id = Column(String, nullable=True)  # <-- Add this line
