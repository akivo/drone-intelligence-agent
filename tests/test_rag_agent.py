import time
from unittest.mock import MagicMock, patch
import pytest


def _make_snapshot(battery: float = 80.0, altitude: float = 30.0) -> dict:
    return {
        "timestamp": time.time(),
        "drone_id": "Drone1",
        "battery_pct": battery,
        "altitude_m": altitude,
        "lat": 37.77,
        "lon": -122.41,
        "speed_ms": 5.0,
        "is_flying": True,
    }


@patch("tools.flight_logger._get_vectorstore")
def test_log_telemetry_adds_document(mock_vs_factory):
    from tools.flight_logger import log_telemetry

    mock_vs = MagicMock()
    mock_vs_factory.return_value = mock_vs

    snapshot = _make_snapshot()
    log_telemetry(snapshot)

    mock_vs.add_documents.assert_called_once()
    doc = mock_vs.add_documents.call_args[0][0][0]
    assert "Drone1" in doc.page_content
    assert "altitude" in doc.page_content


@patch("tools.flight_logger._get_vectorstore")
def test_log_anomaly_event(mock_vs_factory):
    from tools.flight_logger import log_anomaly_event

    mock_vs = MagicMock()
    mock_vs_factory.return_value = mock_vs

    snapshot = _make_snapshot(battery=10.0)
    log_anomaly_event(snapshot, "LOW_BATTERY", "RETURN_TO_HOME", approved=True)

    mock_vs.add_documents.assert_called_once()
    doc = mock_vs.add_documents.call_args[0][0][0]
    assert "ANOMALY" in doc.page_content
    assert "LOW_BATTERY" in doc.page_content
    assert doc.metadata["approved"] is True


@patch("agents.rag_query_agent._get_chain")
def test_query_flights_returns_string(mock_chain_factory):
    from agents.rag_query_agent import query_flights

    mock_chain = MagicMock()
    mock_chain.invoke.return_value = {
        "result": "The maximum altitude was 35m.",
        "source_documents": [],
    }
    mock_chain_factory.return_value = mock_chain

    answer = query_flights("What was the max altitude?")
    assert isinstance(answer, str)
    assert "35m" in answer
