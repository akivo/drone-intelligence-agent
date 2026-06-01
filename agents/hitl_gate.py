from langsmith import traceable


_VALID_RESPONSES = {"y", "n", "e"}

_ACTION_LABELS = {
    "RETURN_TO_HOME": "Return drone to home position",
    "DESCEND_TO_SAFE_ALTITUDE": "Descend to safe altitude (< 80m)",
    "REDUCE_SPEED": "Reduce speed to safe limit",
}


@traceable(name="hitl_approval_gate")
def hitl_gate(state: dict) -> dict:
    """
    Pauses the agent graph and waits for a human operator decision.
    Supports: approve (y), cancel (n), escalate (e).
    """
    action_label = _ACTION_LABELS.get(state["proposed_action"], state["proposed_action"])
    t = state["telemetry"]

    print("\n" + "=" * 62)
    print(f"  [!] ANOMALY DETECTED: {state['anomaly_type']}")
    print(f"  Proposed action  : {action_label}")
    print(f"  Drone            : {t['drone_id']}")
    print(f"  Altitude         : {t['altitude_m']:.1f} m")
    print(f"  Battery          : {t['battery_pct']:.0f} %")
    print(f"  Speed            : {t['speed_ms']:.1f} m/s")
    print(f"  GPS              : ({t['lat']:.4f}, {t['lon']:.4f})")
    print("=" * 62)

    while True:
        response = input(
            "  Decision [y = approve | n = cancel | e = escalate]: "
        ).strip().lower()
        if response in _VALID_RESPONSES:
            break
        print(f"  Invalid input '{response}'. Please enter y, n, or e.")

    if response == "y":
        print(f"  [APPROVED] {action_label}\n")
        return {**state, "approved": True, "escalated": False}

    if response == "e":
        print("  [ESCALATED] Sent to senior operator - awaiting override\n")
        return {**state, "approved": False, "escalated": True}

    print("  [CANCELLED] Action cancelled by operator\n")
    return {**state, "approved": False, "escalated": False}
