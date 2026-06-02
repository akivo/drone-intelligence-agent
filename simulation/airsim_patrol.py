"""
simulation/airsim_patrol.py — Standalone patrol demo script.

This script can be used to test AirSim connectivity independently
or as a quick demo without running the full main.py agent stack.

Run while AirSim (Blocks.exe) is open:
    python simulation/airsim_patrol.py
"""
import sys
import os
import time
import warnings

warnings.filterwarnings("ignore")

# ── CRITICAL: must be FIRST before any other imports ─────────────────────────
import asyncio
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
asyncio.set_event_loop(asyncio.new_event_loop())
# ─────────────────────────────────────────────────────────────────────────────

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import airsim

WAYPOINTS = [(20, 0, -15), (20, 20, -15), (0, 20, -15), (0, 0, -15)]
SPEED = 5  # m/s


def main():
    drone_id = sys.argv[1] if len(sys.argv) > 1 else "Drone1"

    print("=" * 50)
    print(f"  AirSim Patrol Demo  [{drone_id}]")
    print("=" * 50)
    print("Connecting to AirSim...")

    c = airsim.MultirotorClient()
    c.confirmConnection()
    c.enableApiControl(True)
    print(f"Connected! [{drone_id}] API control enabled.")

    print("Arming and taking off...")
    c.armDisarm(True)
    c.takeoffAsync().join()
    print(f"[{drone_id}] Airborne! Beginning patrol...")

    for idx, (x, y, z) in enumerate(WAYPOINTS, start=1):
        print(f"[{drone_id}] Leg {idx}/{len(WAYPOINTS)}: → ({x}, {y}, alt={abs(z)}m)")
        c.moveToPositionAsync(x, y, z, velocity=SPEED).join()

        state = c.getMultirotorState()
        k = state.kinematics_estimated
        speed = (k.linear_velocity.x_val**2 +
                 k.linear_velocity.y_val**2 +
                 k.linear_velocity.z_val**2) ** 0.5
        print(f"  ✓ Waypoint {idx} reached | alt={abs(k.position.z_val):.1f}m | speed={speed:.1f}m/s")

    print(f"[{drone_id}] Patrol complete. Landing...")
    c.landAsync().join()
    c.armDisarm(False)
    print(f"[{drone_id}] Landed safely. Mission complete!")
    print("=" * 50)


if __name__ == "__main__":
    main()
