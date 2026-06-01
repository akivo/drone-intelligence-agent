import asyncio
import time
from dataclasses import dataclass, asdict

try:
    import airsim
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


class MockAirSimClient:
    """Fallback when AirSim binary is not running - generates realistic synthetic telemetry."""

    def __init__(self, drone_id: str = "Drone1"):
        self.drone_id = drone_id
        self._step = 0
        self._is_flying = False
        print(f"[MOCK] AirSim not available - using MockAirSimClient for {drone_id}")

    def get_telemetry(self) -> TelemetrySnapshot:
        import math
        self._step += 1
        t = self._step
        altitude = 15.0 + 5.0 * math.sin(t * 0.2) if self._is_flying else 0.0
        battery = max(5.0, 100.0 - t * 3.5)  # hits ~19% at cycle 23 -> triggers LOW_BATTERY
        speed = 4.5 + math.sin(t * 0.3) if self._is_flying else 0.0
        return TelemetrySnapshot(
            timestamp=time.time(),
            drone_id=self.drone_id,
            battery_pct=battery,
            altitude_m=altitude,
            lat=37.7749 + t * 0.00001,
            lon=-122.4194 + t * 0.00001,
            speed_ms=speed,
            is_flying=self._is_flying,
        )

    async def takeoff_and_patrol(self):
        print("[MOCK] Takeoff initiated")
        self._is_flying = True
        await asyncio.sleep(2)
        for leg, (x, y) in enumerate([(20, 0), (20, 20), (0, 20), (0, 0)], start=1):
            print(f"[MOCK] Patrol leg {leg}: moving to ({x}, {y})")
            await asyncio.sleep(12)   # 4 legs x 12s = 48s — covers most of the 60s monitor window
        print("[MOCK] Landing")
        self._is_flying = False


class AirSimClient:
    """Connects to a running AirSim instance and streams live drone telemetry."""

    def __init__(self, drone_id: str = "Drone1"):
        self.drone_id = drone_id

        if not AIRSIM_AVAILABLE:
            raise RuntimeError("airsim package not installed")

        self.client = airsim.MultirotorClient()
        self.client.confirmConnection()
        self.client.enableApiControl(True)
        print(f"Connected to AirSim - {drone_id} ready")

    def get_telemetry(self) -> TelemetrySnapshot:
        state = self.client.getMultirotorState()
        gps = self.client.getGpsData()
        kinematics = state.kinematics_estimated

        vx = kinematics.linear_velocity.x_val
        vy = kinematics.linear_velocity.y_val
        vz = kinematics.linear_velocity.z_val
        speed = (vx**2 + vy**2 + vz**2) ** 0.5

        # AirSim does not expose battery natively; use a simulated decay value
        battery_pct = max(0.0, 100.0 - (time.time() % 3600) / 36.0)

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

    async def takeoff_and_patrol(self):
        self.client.armDisarm(True)
        self.client.takeoffAsync().join()
        print(f"[{self.drone_id}] Airborne - beginning patrol")

        waypoints = [(20, 0, -15), (20, 20, -15), (0, 20, -15), (0, 0, -15)]
        for x, y, z in waypoints:
            self.client.moveToPositionAsync(x, y, z, velocity=5).join()
            print(f"[{self.drone_id}] Reached waypoint ({x}, {y})")

        self.client.landAsync().join()
        self.client.armDisarm(False)
        print(f"[{self.drone_id}] Landed safely")


def get_client(drone_id: str = "Drone1") -> AirSimClient | MockAirSimClient:
    """Return a real AirSimClient if AirSim is reachable, otherwise fall back to mock."""
    if not AIRSIM_AVAILABLE:
        return MockAirSimClient(drone_id)
    try:
        return AirSimClient(drone_id)
    except Exception as e:
        print(f"[WARN] Could not connect to AirSim ({e}). Using mock client.")
        return MockAirSimClient(drone_id)
