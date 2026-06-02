"""
AirSim flight script — tornado 6 / Python 3.13 compatible.
Run while Blocks.exe (AirSim) is open.

Fixes applied:
  - tornado upgraded to 6.5.6
  - msgpackrpc patches applied for tornado 6 API changes
  - WindowsSelectorEventLoopPolicy applied before any imports
"""
import warnings
warnings.filterwarnings("ignore")

# ── CRITICAL: must be FIRST before any other imports ──────────────────────────
# tornado 6 needs asyncio SelectorEventLoop on Windows.
import asyncio
import sys
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
asyncio.set_event_loop(asyncio.new_event_loop())
# ─────────────────────────────────────────────────────────────────────────────

sys.path.insert(0, ".")
import airsim

print("Connecting to AirSim...")
c = airsim.MultirotorClient()
c.confirmConnection()
print("Connected!")

c.enableApiControl(True)
c.armDisarm(True)

print("Taking off...")
c.takeoffAsync().join()

print("Flying patrol box...")
c.moveToPositionAsync(20, 0, -15, velocity=5).join()
c.moveToPositionAsync(20, 20, -15, velocity=5).join()
c.moveToPositionAsync(0, 20, -15, velocity=5).join()
c.moveToPositionAsync(0, 0, -15, velocity=5).join()

print("Landing...")
c.landAsync().join()
c.armDisarm(False)
print("Done.")
