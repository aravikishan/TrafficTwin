"""Traffic flow analysis and congestion metrics."""

from __future__ import annotations

from typing import Optional

import config
from services.simulator import TrafficSimulator


def compute_analytics(sim: TrafficSimulator) -> dict:
    """Compute comprehensive traffic analytics from a simulator instance.

    Returns a dictionary with throughput, density, congestion zones,
    speed distribution, and flow rate metrics.
    """
    stats = sim.get_statistics()
    vehicle_count = stats["vehicle_count"]
    road_cells = _count_road_cells(sim)
    density = vehicle_count / road_cells if road_cells > 0 else 0.0

    avg_speed = stats["average_speed"]
    flow_rate = density * avg_speed

    throughput = _compute_throughput(sim)
    congestion_zones = _find_congestion_zones(sim)

    avg_hist_speed = 0.0
    if sim._speed_history:
        avg_hist_speed = sum(sim._speed_history) / len(sim._speed_history)

    return {
        "simulation_id": 0,
        "total_steps": sim.step_count,
        "average_speed": round(avg_hist_speed, 2) if sim._speed_history else round(avg_speed, 2),
        "throughput": round(throughput, 2),
        "density": round(density, 4),
        "congestion_index": stats["congestion_index"],
        "flow_rate": round(flow_rate, 4),
        "vehicles_stopped": stats["vehicles_stopped"],
        "vehicles_moving": stats["vehicles_moving"],
        "speed_distribution": stats["speed_distribution"],
        "congestion_zones": congestion_zones,
    }


def _count_road_cells(sim: TrafficSimulator) -> int:
    """Count total road cells in the grid."""
    count = 0
    for row in range(sim.height):
        for col in range(sim.width):
            if sim.grid[row][col].is_road():
                count += 1
    return count


def _compute_throughput(sim: TrafficSimulator) -> float:
    """Compute throughput as average vehicles passing per step.

    Uses the flow history (vehicles moving each step).
    """
    if not sim._flow_history:
        return 0.0
    return sum(sim._flow_history) / len(sim._flow_history)


def _find_congestion_zones(
    sim: TrafficSimulator, zone_size: int = 5, threshold: float = 0.6
) -> list[dict]:
    """Identify congested zones in the grid.

    Divides the grid into zone_size x zone_size blocks and flags those
    where vehicle density exceeds the threshold.
    """
    zones = []
    heatmap = sim.generate_heatmap()

    for block_y in range(0, sim.height, zone_size):
        for block_x in range(0, sim.width, zone_size):
            total = 0.0
            count = 0
            for dy in range(zone_size):
                for dx in range(zone_size):
                    y = block_y + dy
                    x = block_x + dx
                    if y < sim.height and x < sim.width:
                        total += heatmap[y][x]
                        count += 1
            if count > 0:
                avg_density = total / count
                if avg_density >= threshold:
                    zones.append({
                        "x": block_x,
                        "y": block_y,
                        "width": min(zone_size, sim.width - block_x),
                        "height": min(zone_size, sim.height - block_y),
                        "density": round(avg_density, 3),
                        "severity": _severity_label(avg_density),
                    })
    return zones


def _severity_label(density: float) -> str:
    """Map a density value to a human-readable severity label."""
    if density >= config.CONGESTION_SEVERE:
        return "severe"
    elif density >= config.CONGESTION_HIGH:
        return "high"
    elif density >= config.CONGESTION_MODERATE:
        return "moderate"
    elif density >= config.CONGESTION_LOW:
        return "low"
    return "none"


def compute_intersection_stats(sim: TrafficSimulator) -> list[dict]:
    """Compute per-intersection traffic statistics."""
    results = []
    for intersection in sim.intersections:
        nearby_vehicles = 0
        total_speed = 0
        radius = 3
        for v in sim.vehicles:
            dist = abs(v.x - intersection.x) + abs(v.y - intersection.y)
            if dist <= radius:
                nearby_vehicles += 1
                total_speed += v.speed

        avg_speed = total_speed / nearby_vehicles if nearby_vehicles > 0 else 0.0
        light_states = {}
        for tl in intersection.traffic_lights:
            light_states[tl.direction.value] = tl.state.value

        results.append({
            "intersection_id": intersection.id,
            "name": intersection.name,
            "x": intersection.x,
            "y": intersection.y,
            "nearby_vehicles": nearby_vehicles,
            "average_speed": round(avg_speed, 2),
            "light_states": light_states,
            "congestion_level": _severity_label(
                nearby_vehicles / max(1, (2 * radius + 1) ** 2)
            ),
        })
    return results


def generate_time_series(sim: TrafficSimulator) -> dict:
    """Generate time series data from simulation history."""
    return {
        "speed_history": [round(s, 2) for s in sim._speed_history],
        "flow_history": sim._flow_history,
        "steps": list(range(1, sim.step_count + 1)),
    }
