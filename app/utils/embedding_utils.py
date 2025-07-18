import tempfile
import os
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores.pgvector import PGVector as BasePGVector
from langchain_community.document_loaders import PyPDFLoader, UnstructuredWordDocumentLoader, UnstructuredPowerPointLoader
from dotenv import load_dotenv

class NoCreatePGVector(BasePGVector):
    def create_tables_if_not_exists(self):
        pass
    def create_vector_extension(self):
        pass

def embed_pdf(file_obj, metadata: dict = {}):
    load_dotenv()
    PGVECTOR_CONNECTION_STRING = os.getenv("VECTORSTORE_DATABASE_URL")
    if not PGVECTOR_CONNECTION_STRING:
        raise ValueError("VECTORSTORE_DATABASE_URL environment variable is not set")
    embedding_model = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    vectorstore = NoCreatePGVector(
        collection_name="rag_embeddings",
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
    try:
        vectorstore.add_documents(docs)
    except ValueError as e:
        if "Collection not found" in str(e):
            vectorstore.create_tables_if_not_exists()
            vectorstore.add_documents(docs)
        else:
            raise

def embed_docx(file_obj, metadata: dict = {}):
    load_dotenv()
    PGVECTOR_CONNECTION_STRING = os.getenv("VECTORSTORE_DATABASE_URL")
    if not PGVECTOR_CONNECTION_STRING:
        raise ValueError("VECTORSTORE_DATABASE_URL environment variable is not set")
    embedding_model = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    vectorstore = NoCreatePGVector(
        collection_name="rag_embeddings",
        connection_string=PGVECTOR_CONNECTION_STRING,
        embedding_function=embedding_model,
    )
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".docx")
    try:
        file_obj.seek(0)
        tmp.write(file_obj.read())
        tmp.flush()
        tmp.close()
        loader = UnstructuredWordDocumentLoader(tmp.name)
        pages = loader.load()
    finally:
        os.unlink(tmp.name)
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    docs = text_splitter.split_documents(pages)
    for doc in docs:
        doc.metadata.update(metadata)
    try:
        vectorstore.add_documents(docs)
    except ValueError as e:
        if "Collection not found" in str(e):
            vectorstore.create_tables_if_not_exists()
            vectorstore.add_documents(docs)
        else:
            raise

def embed_ppt(file_obj, metadata: dict = {}):
    load_dotenv()
    PGVECTOR_CONNECTION_STRING = os.getenv("VECTORSTORE_DATABASE_URL")
    if not PGVECTOR_CONNECTION_STRING:
        raise ValueError("VECTORSTORE_DATABASE_URL environment variable is not set")
    embedding_model = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    vectorstore = NoCreatePGVector(
        collection_name="rag_embeddings",
        connection_string=PGVECTOR_CONNECTION_STRING,
        embedding_function=embedding_model,
    )
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pptx")
    try:
        file_obj.seek(0)
        tmp.write(file_obj.read())
        tmp.flush()
        tmp.close()
        loader = UnstructuredPowerPointLoader(tmp.name)
        pages = loader.load()
    finally:
        os.unlink(tmp.name)
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    docs = text_splitter.split_documents(pages)
    for doc in docs:
        doc.metadata.update(metadata)
    try:
        vectorstore.add_documents(docs)
    except ValueError as e:
        if "Collection not found" in str(e):
            vectorstore.create_tables_if_not_exists()
            vectorstore.add_documents(docs)
        else:
            raise 