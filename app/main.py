import os
from typing import TypedDict, List

from dotenv import load_dotenv
from langchain_core.output_parsers import StrOutputParser
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores.pgvector import PGVector as BasePGVector
from langchain_community.document_loaders import UnstructuredWordDocumentLoader
from langchain_community.document_loaders import UnstructuredPowerPointLoader
from langgraph.graph import StateGraph

from llm import GeminiLLM  # You must have a GeminiLLM class implemented

import tempfile
import io

from langchain_core.documents import Document


from utils.vectorstore_utils import get_vectorstore

# ----------------------------
# Load environment and models
# ----------------------------
load_dotenv()

# Embedding model
embedding_model = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

# PostgreSQL pgvector connection
PGVECTOR_CONNECTION_STRING = os.getenv("VECTORSTORE_DATABASE_URL")
if not PGVECTOR_CONNECTION_STRING:
    raise ValueError("VECTORSTORE_DATABASE_URL environment variable is not set")

# Vector store setup (collection is shared, metadata is filtered per user/file)

# Language model
llm = GeminiLLM()
parser = StrOutputParser()

# ----------------------------
# LangGraph State Definition
# ----------------------------
class AgentState(TypedDict):
    question: str
    context_docs: List
    answer: str
    user_id: str  # Add this line

# ----------------------------
# Node 1: Retrieve documents
# ----------------------------
def retrieve_docs(state: AgentState) -> AgentState:
    from utils.vectorstore_utils import get_vectorstore
    user_id = state.get("user_id")
    filter_metadata = state.get("filter_metadata")
    if not filter_metadata:
        filter_metadata = {"user_id": user_id}
    vectorstore = get_vectorstore()
    retriever = vectorstore.as_retriever(
        search_kwargs={
            "k": 5,
            "filter": filter_metadata
        }
    )
    new_docs = retriever.invoke(state["question"])
    file_id = filter_metadata.get("file_id")
    if file_id:
        # Strictly filter all docs by file_id, including accumulated docs
        filtered_docs = [doc for doc in new_docs if doc.metadata.get("file_id") == file_id]
        state["context_docs"] = filtered_docs
    else:
        # Default: accumulate all docs
        accumulated_docs = state.get("context_docs", [])
        all_docs = accumulated_docs + [doc for doc in new_docs if doc not in accumulated_docs]
        state["context_docs"] = all_docs
    print("Context docs:", [doc.metadata for doc in state["context_docs"]])
    return state

# ----------------------------
# Node 2: Generate answer
# ----------------------------
def answer_question(state: AgentState) -> AgentState:
    if not state["context_docs"]:
        state["answer"] = "❌ No relevant information found in the documents."
        return state

    # Build context
    context = "\n\n".join([
        f"(Page {doc.metadata.get('page', 'N/A')}) {doc.page_content}"
        for doc in state["context_docs"]
    ])

    prompt = (
        "You are a professional assistant. Answer the user's question clearly using only the provided document.\n"
        "Cite the page number when relevant. If the answer is not present, say so clearly.\n\n"
        f"Context:\n{context}\n\nQuestion: {state['question']}"
    )

    # Generate response
    response = llm._call(prompt)
    state["answer"] = response
    return state

# ----------------------------
# LangGraph: Build DAG
# ----------------------------
graph = StateGraph(AgentState)
graph.add_node("retrieve", retrieve_docs)
graph.add_node("generate", answer_question)
graph.set_entry_point("retrieve")
graph.add_edge("retrieve", "generate")
graph.set_finish_point("generate")

rag_agent = graph.compile()