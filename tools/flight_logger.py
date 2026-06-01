import os
from datetime import datetime

from dotenv import load_dotenv
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_postgres import PGVector
from langchain_core.documents import Document

load_dotenv()

# Runs locally — no API key needed
_embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
_COLLECTION = "flight_logs"

_vectorstore: PGVector | None = None


def _get_vectorstore() -> PGVector:
    global _vectorstore
    if _vectorstore is None:
        conn_str = os.getenv("DATABASE_URL")
        if not conn_str:
            raise RuntimeError("DATABASE_URL not set in environment")
        _vectorstore = PGVector(
            _embeddings,
            collection_name=_COLLECTION,
            connection=conn_str,
        )
    return _vectorstore


def _snapshot_to_text(snapshot: dict) -> str:
    ts = datetime.fromtimestamp(snapshot["timestamp"]).isoformat()
    return (
        f"Drone {snapshot['drone_id']} at {ts}: "
        f"altitude {snapshot['altitude_m']:.1f}m, "
        f"battery {snapshot['battery_pct']:.0f}%, "
        f"speed {snapshot['speed_ms']:.1f}m/s, "
        f"position ({snapshot['lat']:.4f}, {snapshot['lon']:.4f}), "
        f"flying={snapshot['is_flying']}"
    )


def log_telemetry(snapshot: dict) -> None:
    text = _snapshot_to_text(snapshot)
    doc = Document(page_content=text, metadata=snapshot)
    _get_vectorstore().add_documents([doc])
    print(f"[LOGGED] {text[:90]}...")


def log_anomaly_event(snapshot: dict, anomaly_type: str, action: str, approved: bool) -> None:
    ts = datetime.fromtimestamp(snapshot["timestamp"]).isoformat()
    text = (
        f"ANOMALY EVENT at {ts}: drone {snapshot['drone_id']}, "
        f"type={anomaly_type}, proposed_action={action}, "
        f"operator_approved={approved}, "
        f"battery={snapshot['battery_pct']:.0f}%, "
        f"altitude={snapshot['altitude_m']:.1f}m"
    )
    metadata = {**snapshot, "event_type": "anomaly", "anomaly_type": anomaly_type, "approved": approved}
    doc = Document(page_content=text, metadata=metadata)
    _get_vectorstore().add_documents([doc])
    print(f"[ANOMALY LOGGED] {text[:90]}...")
