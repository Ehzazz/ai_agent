import os
from typing import TypedDict, List

from dotenv import load_dotenv
from langchain_core.output_parsers import StrOutputParser
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores.pgvector import PGVector as BasePGVector

class NoCreatePGVector(BasePGVector):
    def create_tables_if_not_exists(self):
        pass  # Do nothing
    def create_vector_extension(self):
        pass  # Do nothing

from langgraph.graph import StateGraph

from llm import GeminiLLM  # You must have a GeminiLLM class implemented

import tempfile
import io

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
vectorstore = NoCreatePGVector(
    collection_name="rag_embeddings",
    connection_string=PGVECTOR_CONNECTION_STRING,
    embedding_function=embedding_model,
)

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

# ----------------------------
# Node 1: Retrieve documents
# ----------------------------
def retrieve_docs(state: AgentState) -> AgentState:
    retriever = vectorstore.as_retriever(search_kwargs={"k": 5})
    docs = retriever.invoke(state["question"])
    state["context_docs"] = docs
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

# ----------------------------
# Utility: Embed PDF and save vectors
# ----------------------------
def embed_pdf(file_obj, metadata: dict = {}):
    """Loads and embeds a PDF file, storing its vectors in PostgreSQL via pgvector."""
    import tempfile
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    # Get the file name from metadata
    # collection_name = metadata.get("file_name", "default_collection") # This line is removed
    # Create a new vectorstore for this file/collection
    from langchain_community.vectorstores.pgvector import PGVector as BasePGVector
    class NoCreatePGVector(BasePGVector):
        def create_tables_if_not_exists(self):
            pass
        def create_vector_extension(self):
            pass
    from dotenv import load_dotenv
    import os
    load_dotenv()
    PGVECTOR_CONNECTION_STRING = os.getenv("VECTORSTORE_DATABASE_URL")
    if not PGVECTOR_CONNECTION_STRING:
        raise ValueError("VECTORSTORE_DATABASE_URL environment variable is not set")
    embedding_model = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    vectorstore = NoCreatePGVector(
        collection_name="rag_embeddings", # This line is changed to use the global vectorstore
        connection_string=PGVECTOR_CONNECTION_STRING,
        embedding_function=embedding_model,
    )
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    try:
        file_obj.seek(0)
        tmp.write(file_obj.read())
        tmp.flush()
        tmp.close()
        loader = PyPDFLoader(tmp.name)
        pages = loader.load()
    finally:
        os.unlink(tmp.name)
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    docs = text_splitter.split_documents(pages)
    for doc in docs:
        doc.metadata.update(metadata)
    # Try to add documents, create collection if not found
    try:
        vectorstore.add_documents(docs)
    except ValueError as e:
        if "Collection not found" in str(e):
            vectorstore.create_tables_if_not_exists()
            vectorstore.add_documents(docs)
        else:
            raise

def get_file_type(filename, content):
    ext = filename.lower().split('.')[-1]
    if ext == 'pdf':
        return 'pdf'
    elif ext == 'txt':
        return 'txt'
    elif ext == 'docx':
        return 'docx'
    elif ext == 'xlsx':
        return 'xlsx'
    else:
        return None

def process_file(filename, content):
    file_type = get_file_type(filename, content)
    if file_type == 'pdf':
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(content)
            tmp.flush()
            tmp_path = tmp.name
        try:
            loader = PyPDFLoader(tmp_path)
            pages = loader.load()
        finally:
            os.remove(tmp_path)
        return pages
    elif file_type == 'txt':
        # Decode and process as text
        text = content.decode('utf-8')
        ...
    elif file_type == 'docx':
        # Use python-docx or langchain docx loader
        ...
    elif file_type == 'xlsx':
        # Use openpyxl or pandas
        ...
    else:
        raise ValueError("Unsupported file type")
