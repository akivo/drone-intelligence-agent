import os

from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_postgres import PGVector
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langsmith import traceable

load_dotenv()

# HuggingFace embeddings run locally - no API key, no cost (384-dim)
_embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
_llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)

_vectorstore: PGVector | None = None
_rag_chain = None

_PROMPT = ChatPromptTemplate.from_template(
    "You are a drone fleet analyst. Answer the question using only the flight log context below.\n\n"
    "Context:\n{context}\n\n"
    "Question: {question}\n\n"
    "Answer concisely and factually:"
)


def _format_docs(docs) -> str:
    return "\n\n".join(d.page_content for d in docs)


def _get_chain():
    global _vectorstore, _rag_chain
    if _rag_chain is None:
        conn_str = os.getenv("DATABASE_URL")
        if not conn_str:
            raise RuntimeError("DATABASE_URL not set in environment")
        _vectorstore = PGVector(
            _embeddings,
            collection_name="flight_logs",
            connection=conn_str,
        )
        retriever = _vectorstore.as_retriever(search_kwargs={"k": 10})
        _rag_chain = (
            {"context": retriever | _format_docs, "question": RunnablePassthrough()}
            | _PROMPT
            | _llm
            | StrOutputParser()
        )
    return _rag_chain


@traceable(name="rag_query")
def query_flights(question: str) -> str:
    """Answer a natural language question over stored flight logs."""
    print(f"\n[RAG] Q: {question}")
    answer = _get_chain().invoke(question)
    print(f"[RAG] A: {answer}")
    return answer


DEMO_QUERIES = [
    "What was the maximum altitude reached during the flight?",
    "Were there any battery warnings during the patrol?",
    "Summarize the patrol route telemetry.",
    "How many anomalies were detected and what types were they?",
    "What was the average speed throughout the flight?",
]


def run_demo_queries() -> None:
    for q in DEMO_QUERIES:
        query_flights(q)
        print()
