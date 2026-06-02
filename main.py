import asyncio
import sys
import time
import warnings

# ── Windows + Python 3.10+ / tornado 4.5.3 compatibility fix ─────────────────
# tornado 4.5.3 (required by msgpack-rpc-python / AirSim Python API) only
# works with SelectorEventLoop.  Python 3.10+ on Windows defaults to
# ProactorEventLoop, which causes AirSim's confirmConnection() to hang forever.
# Setting the policy here (before any other imports) ensures that both this
# process and any subprocesses we spawn use the compatible loop type.
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
# ─────────────────────────────────────────────────────────────────────────────

# --- CRITICAL BUG FIX FOR AIRSIM/TORNADO ON PYTHON 3.13 ---
# Tornado 6 frequently clears the thread-local asyncio event loop on background threads 
# after RPC calls finish. This global patch ensures that anytime Tornado asks for an 
# event loop, it will always get one instead of crashing with a RuntimeError.
_original_get_event_loop = asyncio.get_event_loop
def _safe_get_event_loop():
    try:
        return _original_get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop
asyncio.get_event_loop = _safe_get_event_loop
# -----------------------------------------------------------

warnings.filterwarnings("ignore", category=PendingDeprecationWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)

from observability.langsmith_setup import configure_langsmith
from simulation.airsim_client import get_client
from agents.monitor_agent import monitor_graph
from agents.hitl_gate import hitl_gate
from agents.rag_query_agent import run_demo_queries
from tools.flight_logger import log_telemetry, log_anomaly_event

MONITOR_INTERVAL_S = 2      # seconds between telemetry reads
MONITOR_CYCLES = 30         # total cycles  (~60 seconds of flight)


def monitoring_loop(client) -> None:
    print(f"\n[MONITOR] Starting {MONITOR_CYCLES}-cycle telemetry loop ({MONITOR_INTERVAL_S}s interval)")

    for cycle in range(1, MONITOR_CYCLES + 1):
        print(f"\n--- Cycle {cycle}/{MONITOR_CYCLES} ----------------------------")

        telemetry = client.get_telemetry()
        snapshot = telemetry.to_dict()

        # Run through the LangGraph monitor agent
        result = monitor_graph.invoke(
            {
                "telemetry": snapshot,
                "anomaly_detected": False,
                "anomaly_type": None,
                "proposed_action": None,
                "needs_approval": False,
                "approved": None,
                "escalated": None,
                "log_message": "",
            }
        )

        # If HITL gate needed, pause and collect operator decision
        if result.get("needs_approval"):
            result = hitl_gate(result)
            log_anomaly_event(
                snapshot,
                anomaly_type=result.get("anomaly_type", "UNKNOWN"),
                action=result.get("proposed_action", "NONE"),
                approved=result.get("approved", False),
            )
        else:
            print(f"[STATUS] {result.get('log_message', 'OK')}")

        # Persist every snapshot to pgvector for RAG
        try:
            log_telemetry(snapshot)
        except Exception as e:
            print(f"[WARN] Could not log to pgvector: {e}")

        time.sleep(MONITOR_INTERVAL_S)


def main() -> None:
    print("=" * 62)
    print("  Drone Fleet Intelligence Agent  - Starting Up")
    print("=" * 62)

    # Configure LangSmith tracing
    configure_langsmith()

    # Run patrol in a background thread.
    # We must use a dedicated AirSim client for the background thread because 
    # msgpackrpc sockets are not thread-safe and tie themselves to the thread's event loop.
    import threading
    
    def patrol_thread():
        print("[LIVE] Connecting patrol thread to AirSim...")
        # The patrol thread MUST have API control to fly the drone
        patrol_client = get_client("Drone1", control=True)
        patrol_client.takeoff_and_patrol()

    t = threading.Thread(target=patrol_thread, daemon=True)
    t.start()

    # Delay slightly so patrol connects first and logs clearly
    time.sleep(1)

    # Connect monitoring client on the main thread
    print("[LIVE] Connecting monitoring thread to AirSim...")
    # The monitoring thread MUST NOT have API control, otherwise it will steal 
    # control from the patrol thread and force the drone into hover mode!
    monitor_client = get_client("Drone1", control=False)

    # Run monitoring
    monitoring_loop(monitor_client)
    
    # Wait for patrol to finish
    t.join()

    # Post-flight RAG demo
    print("\n" + "=" * 62)
    print("  Flight complete. Running RAG query demo...")
    print("=" * 62)

    try:
        run_demo_queries()
    except Exception as e:
        print(f"[WARN] RAG queries skipped - pgvector may not be reachable: {e}")

    print("\n[DONE] Session ended.")


if __name__ == "__main__":
    main()
