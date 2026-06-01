import asyncio
import time

from observability.langsmith_setup import configure_langsmith
from simulation.airsim_client import get_client
from agents.monitor_agent import monitor_graph
from agents.hitl_gate import hitl_gate
from agents.rag_query_agent import run_demo_queries
from tools.flight_logger import log_telemetry, log_anomaly_event

MONITOR_INTERVAL_S = 2      # seconds between telemetry reads
MONITOR_CYCLES = 30         # total cycles  (~60 seconds of flight)


async def monitoring_loop(client) -> None:
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

        await asyncio.sleep(MONITOR_INTERVAL_S)


async def main() -> None:
    print("=" * 62)
    print("  Drone Fleet Intelligence Agent  - Starting Up")
    print("=" * 62)

    # Configure LangSmith tracing
    configure_langsmith()

    # Connect to AirSim (or mock if unavailable)
    client = get_client("Drone1")

    # Run patrol and monitoring concurrently
    patrol_task = asyncio.create_task(client.takeoff_and_patrol())
    monitor_task = asyncio.create_task(monitoring_loop(client))

    await asyncio.gather(patrol_task, monitor_task)

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
    asyncio.run(main())
