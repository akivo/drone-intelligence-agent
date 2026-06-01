from typing import TypedDict, Optional

from langgraph.graph import StateGraph, END
from langsmith import traceable


class AgentState(TypedDict):
    telemetry: dict
    anomaly_detected: bool
    anomaly_type: Optional[str]
    proposed_action: Optional[str]
    needs_approval: bool
    approved: Optional[bool]
    escalated: Optional[bool]
    log_message: str


# ── Thresholds ────────────────────────────────────────────────────────────────
BATTERY_CRITICAL = 20.0   # percent
ALTITUDE_MAX = 100.0      # metres
SPEED_MAX = 20.0          # m/s


@traceable(name="ingest_telemetry")
def ingest_node(state: AgentState) -> AgentState:
    t = state["telemetry"]
    print(
        f"[TELEMETRY] Alt: {t['altitude_m']:.1f}m | "
        f"Bat: {t['battery_pct']:.0f}% | "
        f"Speed: {t['speed_ms']:.1f}m/s | "
        f"GPS: ({t['lat']:.4f}, {t['lon']:.4f})"
    )
    return state


@traceable(name="detect_anomaly")
def detect_node(state: AgentState) -> AgentState:
    t = state["telemetry"]

    if t["battery_pct"] < BATTERY_CRITICAL:
        return {
            **state,
            "anomaly_detected": True,
            "anomaly_type": "LOW_BATTERY",
            "proposed_action": "RETURN_TO_HOME",
            "needs_approval": True,
        }

    if t["altitude_m"] > ALTITUDE_MAX:
        return {
            **state,
            "anomaly_detected": True,
            "anomaly_type": "ALTITUDE_BREACH",
            "proposed_action": "DESCEND_TO_SAFE_ALTITUDE",
            "needs_approval": True,
        }

    if t["speed_ms"] > SPEED_MAX:
        return {
            **state,
            "anomaly_detected": True,
            "anomaly_type": "OVERSPEED",
            "proposed_action": "REDUCE_SPEED",
            "needs_approval": True,
        }

    return {
        **state,
        "anomaly_detected": False,
        "anomaly_type": None,
        "proposed_action": None,
        "needs_approval": False,
    }


def route_after_detect(state: AgentState) -> str:
    return "hitl" if state["needs_approval"] else "log"


@traceable(name="log_normal")
def log_node(state: AgentState) -> AgentState:
    return {**state, "log_message": "All systems nominal"}


# ── Build graph ───────────────────────────────────────────────────────────────
_builder = StateGraph(AgentState)
_builder.add_node("ingest", ingest_node)
_builder.add_node("detect", detect_node)
_builder.add_node("log", log_node)

_builder.set_entry_point("ingest")
_builder.add_edge("ingest", "detect")
_builder.add_conditional_edges(
    "detect",
    route_after_detect,
    {"hitl": END, "log": "log"},
)
_builder.add_edge("log", END)

monitor_graph = _builder.compile()
