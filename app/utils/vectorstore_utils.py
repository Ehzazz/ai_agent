import os
from dotenv import load_dotenv
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores.pgvector import PGVector as BasePGVector

class NoCreatePGVector(BasePGVector):
    def create_tables_if_not_exists(self):
        pass
    def create_vector_extension(self):
        pass

def get_vectorstore():
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
    return vectorstore

# Delete all vectors for a given user_id and file_name
def delete_vectors_for_file(user_id, file_name):
    vectorstore = get_vectorstore()
    # The filter must match how you store metadata during embedding
    vectorstore.delete(
        filter={"user_id": user_id, "file_name": file_name}
    ) 