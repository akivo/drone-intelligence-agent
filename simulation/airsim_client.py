"""
simulation/airsim_client.py

Provides:
  - TelemetrySnapshot  — typed telemetry data class
  - AirSimClient       — connects to live AirSim (requires tornado 6 + patches)
  - get_client()       — returns real client (Mock client has been removed per user request)

REQUIREMENTS (applied system-wide via pip + msgpackrpc patches):
  - tornado >= 6.0 (pip install tornado)
  - msgpackrpc address.py, loop.py, transport/tcp.py patched for tornado 6 API
  - asyncio.WindowsSelectorEventLoopPolicy set before any import (done in main.py)
"""
import asyncio
import time
from dataclasses import dataclass, asdict

try:
    import airsim as _airsim_mod
    AIRSIM_AVAILABLE = True
except ImportError:
    AIRSIM_AVAILABLE = False


@dataclass
class TelemetrySnapshot:
    timestamp: float
    drone_id: str
    battery_pct: float
    altitude_m: float
    lat: float
    lon: float
    speed_ms: float
    is_flying: bool

    def to_dict(self) -> dict:
        return asdict(self)


# ─── Live AirSim client ───────────────────────────────────────────────────────

class AirSimClient:
    """
    Connects to a running AirSim instance and streams live drone telemetry.

    Requires:
     - tornado 6.5+ (pip install tornado)
     - msgpackrpc patches applied for tornado 6 API compatibility
     - asyncio.WindowsSelectorEventLoopPolicy set at program startup (done in main.py)
    """

    def __init__(self, drone_id: str = "Drone1", control: bool = True):
        self.drone_id = drone_id
        import airsim
        self.client = airsim.MultirotorClient()
        self.client.confirmConnection()
        if control:
            self.client.enableApiControl(True)
        print(f"[LIVE] Connected to AirSim - {drone_id} ready (control={control})")

    def get_telemetry(self) -> TelemetrySnapshot:
        import airsim
        state = self.client.getMultirotorState()
        gps = self.client.getGpsData()
        kinematics = state.kinematics_estimated

        vx = kinematics.linear_velocity.x_val
        vy = kinematics.linear_velocity.y_val
        vz = kinematics.linear_velocity.z_val
        speed = (vx**2 + vy**2 + vz**2) ** 0.5

        # AirSim does not expose battery natively.
        # We set it to a fixed 100% so it doesn't interrupt the demo with a LOW_BATTERY anomaly prompt.
        battery_pct = 100.0

        return TelemetrySnapshot(
            timestamp=time.time(),
            drone_id=self.drone_id,
            battery_pct=battery_pct,
            altitude_m=abs(kinematics.position.z_val),
            lat=gps.gnss.geo_point.latitude,
            lon=gps.gnss.geo_point.longitude,
            speed_ms=speed,
            is_flying=state.landed_state == airsim.LandedState.Flying,
        )

    def takeoff_and_patrol(self):
        """
        Fly a square patrol pattern using AirSim's blocking RPC calls.
        Runs synchronously.
        """
        import airsim
        import asyncio

        def ensure_loop():
            try:
                asyncio.get_event_loop()
            except RuntimeError:
                asyncio.set_event_loop(asyncio.new_event_loop())

        ensure_loop()
        self.client.armDisarm(True)
        ensure_loop()
        self.client.takeoffAsync().join()
        print(f"[{self.drone_id}] Airborne - ascending to safe altitude for speed test")

        # Fly higher (-30 is 30 meters UP in AirSim) to avoid crashing into trees/buildings.
        # Keep the test short to comfortably finish within the 60-second telemetry window.
        waypoints = [
            (0, 0, -30, 5),       # Ascend straight up to 30m height safely
            (40, 0, -30, 15),     # Short sprint forward (15 m/s)
            (0, 0, -30, 15),      # Short sprint backward (15 m/s)
            (0, 0, 0, 2)          # Descend smoothly all the way to the ground (z=0)
        ]
        for x, y, z, v in waypoints:
            ensure_loop()
            self.client.moveToPositionAsync(x, y, z, velocity=v).join()
            print(f"[{self.drone_id}] Reached waypoint ({x}, {y}, {z}) at {v} m/s")

        ensure_loop()
        self.client.landAsync().join()
        ensure_loop()
        self.client.armDisarm(False)
        print(f"[{self.drone_id}] Landed safely")


# ─── TCP reachability probe ───────────────────────────────────────────────────

def _airsim_reachable(host: str = "127.0.0.1", port: int = 41451, timeout: float = 2.0) -> bool:
    """Quick TCP check — returns True only if AirSim binary is actually listening."""
    import socket
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (OSError, ConnectionRefusedError):
        return False


# ─── Factory ─────────────────────────────────────────────────────────────────

def get_client(drone_id: str = "Drone1", control: bool = True) -> AirSimClient:
    """
    Return a live AirSimClient. 
    If AirSim is not reachable, this will now fail loudly so the user knows
    there is an actual connection issue rather than silently falling back to a mock.
    """
    if not AIRSIM_AVAILABLE:
        raise RuntimeError("airsim package is not installed or importable.")

    if not _airsim_reachable():
        raise ConnectionError("AirSim is not running (port 41451 closed). Please open Blocks.exe and try again.")

    print(f"[LIVE] Attempting to connect to AirSim for {drone_id} (control={control})...")
    
    # We create the client directly on the calling thread. 
    # Because main.py is no longer using asyncio.run(), the thread's event loop 
    # is free for AirSim (tornado) to start and stop as needed.
    import sys
    if sys.platform == "win32":
        import asyncio
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        # CRITICAL FIX: tornado 6 requires an event loop to exist in the current thread 
        # in order to create asyncio.Future objects for its IOStream.
        try:
            asyncio.get_event_loop()
        except RuntimeError:
            asyncio.set_event_loop(asyncio.new_event_loop())
        
    return AirSimClient(drone_id, control)
