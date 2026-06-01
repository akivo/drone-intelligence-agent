import os

from dotenv import load_dotenv
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_postgres import PGVector
from langchain_core.documents import Document

load_dotenv()

_embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")


def get_vectorstore(collection: str = "flight_logs") -> PGVector:
    conn_str = os.getenv("DATABASE_URL")
    if not conn_str:
        raise RuntimeError("DATABASE_URL not set in environment")
    return PGVector(
        _embeddings,
        collection_name=collection,
        connection=conn_str,
    )


def similarity_search(query: str, k: int = 5) -> list[Document]:
    vs = get_vectorstore()
    return vs.similarity_search(query, k=k)


def add_document(text: str, metadata: dict | None = None) -> None:
    vs = get_vectorstore()
    doc = Document(page_content=text, metadata=metadata or {})
    vs.add_documents([doc])
