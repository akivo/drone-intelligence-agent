from simulation.airsim_client import TelemetrySnapshot


def is_low_battery(snapshot: TelemetrySnapshot, threshold: float = 20.0) -> bool:
    return snapshot.battery_pct < threshold


def is_altitude_breach(snapshot: TelemetrySnapshot, max_altitude: float = 100.0) -> bool:
    return snapshot.altitude_m > max_altitude


def is_overspeed(snapshot: TelemetrySnapshot, max_speed: float = 20.0) -> bool:
    return snapshot.speed_ms > max_speed


def summarise(snapshot: TelemetrySnapshot) -> str:
    status = "FLYING" if snapshot.is_flying else "GROUNDED"
    return (
        f"[{snapshot.drone_id}] {status} | "
        f"Alt {snapshot.altitude_m:.1f}m | "
        f"Bat {snapshot.battery_pct:.0f}% | "
        f"Speed {snapshot.speed_ms:.1f}m/s"
    )


def check_all_anomalies(snapshot: TelemetrySnapshot) -> list[str]:
    anomalies = []
    if is_low_battery(snapshot):
        anomalies.append(f"LOW_BATTERY ({snapshot.battery_pct:.0f}%)")
    if is_altitude_breach(snapshot):
        anomalies.append(f"ALTITUDE_BREACH ({snapshot.altitude_m:.1f}m)")
    if is_overspeed(snapshot):
        anomalies.append(f"OVERSPEED ({snapshot.speed_ms:.1f}m/s)")
    return anomalies
