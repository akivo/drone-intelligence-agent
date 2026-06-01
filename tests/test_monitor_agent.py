import time
import pytest
from agents.monitor_agent import monitor_graph, BATTERY_CRITICAL, ALTITUDE_MAX


def _base_state(overrides: dict = {}) -> dict:
    base = {
        "telemetry": {
            "timestamp": time.time(),
            "drone_id": "Drone1",
            "battery_pct": 80.0,
            "altitude_m": 30.0,
            "lat": 37.77,
            "lon": -122.41,
            "speed_ms": 5.0,
            "is_flying": True,
        },
        "anomaly_detected": False,
        "anomaly_type": None,
        "proposed_action": None,
        "needs_approval": False,
        "approved": None,
        "escalated": None,
        "log_message": "",
    }
    base["telemetry"].update(overrides)
    return base


def test_nominal_flight_no_anomaly():
    result = monitor_graph.invoke(_base_state())
    assert result["anomaly_detected"] is False
    assert result["needs_approval"] is False
    assert result["log_message"] == "All systems nominal"


def test_low_battery_triggers_hitl():
    state = _base_state({"battery_pct": BATTERY_CRITICAL - 1})
    result = monitor_graph.invoke(state)
    assert result["anomaly_detected"] is True
    assert result["anomaly_type"] == "LOW_BATTERY"
    assert result["proposed_action"] == "RETURN_TO_HOME"
    assert result["needs_approval"] is True


def test_altitude_breach_triggers_hitl():
    state = _base_state({"altitude_m": ALTITUDE_MAX + 10})
    result = monitor_graph.invoke(state)
    assert result["anomaly_detected"] is True
    assert result["anomaly_type"] == "ALTITUDE_BREACH"
    assert result["needs_approval"] is True


def test_battery_exactly_at_threshold_is_safe():
    state = _base_state({"battery_pct": BATTERY_CRITICAL})
    result = monitor_graph.invoke(state)
    # boundary: NOT strictly less than, so == threshold is safe
    assert result["anomaly_detected"] is False


def test_altitude_exactly_at_max_is_safe():
    state = _base_state({"altitude_m": ALTITUDE_MAX})
    result = monitor_graph.invoke(state)
    assert result["anomaly_detected"] is False
