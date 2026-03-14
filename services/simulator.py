"""Nagel-Schreckenberg cellular automata traffic simulation engine.

Implements the four NaSch rules:
  1. Acceleration: v -> min(v + 1, v_max)
  2. Slowing down: v -> min(v, gap - 1) if gap < v
  3. Random braking: v -> max(v - 1, 0) with probability p
  4. Movement: x -> x + v

The simulation runs on a 2D grid representing a road network with
intersections, traffic lights, and vehicles.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Optional

import config
from models.schemas import (
    CellType,
    Direction,
    LightState,
)


@dataclass
class Cell:
    """A single cell in the traffic grid."""
    cell_type: CellType = CellType.EMPTY
    vehicle_id: Optional[int] = None
    intersection_id: Optional[int] = None

    def is_road(self) -> bool:
        return self.cell_type in (
            CellType.ROAD_H,
            CellType.ROAD_V,
            CellType.INTERSECTION,
        )

    def is_occupied(self) -> bool:
        return self.vehicle_id is not None

    def to_dict(self) -> dict:
        return {
            "type": self.cell_type.value,
            "vehicle_id": self.vehicle_id,
            "intersection_id": self.intersection_id,
        }


@dataclass
class SimVehicle:
    """A vehicle in the simulation."""
    id: int
    x: int
    y: int
    speed: int = 0
    max_speed: int = 5
    direction: Direction = Direction.EAST
    stopped_steps: int = 0
    total_distance: int = 0

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "x": self.x,
            "y": self.y,
            "speed": self.speed,
            "max_speed": self.max_speed,
            "direction": self.direction.value,
            "stopped_steps": self.stopped_steps,
            "total_distance": self.total_distance,
        }


@dataclass
class SimTrafficLight:
    """A traffic light in the simulation."""
    id: int
    intersection_id: int
    x: int
    y: int
    direction: Direction
    state: LightState = LightState.RED
    green_duration: int = 30
    yellow_duration: int = 5
    red_duration: int = 30
    timer: int = 0

    def cycle_duration(self) -> int:
        return self.green_duration + self.yellow_duration + self.red_duration

    def tick(self) -> None:
        """Advance the traffic light by one time step."""
        self.timer += 1
        cycle = self.cycle_duration()
        phase = self.timer % cycle

        if phase < self.green_duration:
            self.state = LightState.GREEN
        elif phase < self.green_duration + self.yellow_duration:
            self.state = LightState.YELLOW
        else:
            self.state = LightState.RED

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "intersection_id": self.intersection_id,
            "x": self.x,
            "y": self.y,
            "direction": self.direction.value,
            "state": self.state.value,
            "timer": self.timer,
            "green_duration": self.green_duration,
            "yellow_duration": self.yellow_duration,
            "red_duration": self.red_duration,
        }


@dataclass
class SimIntersection:
    """An intersection in the road network."""
    id: int
    name: str
    x: int
    y: int
    traffic_lights: list[SimTrafficLight] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "x": self.x,
            "y": self.y,
            "traffic_lights": [tl.to_dict() for tl in self.traffic_lights],
        }


class TrafficSimulator:
    """Nagel-Schreckenberg cellular automata traffic simulator.

    Manages a 2D grid of cells representing a road network, with
    vehicles that follow the NaSch rules and traffic lights that
    cycle through green/yellow/red states.
    """

    def __init__(
        self,
        width: int = 40,
        height: int = 30,
        vehicle_count: int = 60,
        max_speed: int = 5,
        braking_probability: float = 0.3,
    ):
        self.width = width
        self.height = height
        self.vehicle_count = vehicle_count
        self.max_speed = max_speed
        self.braking_probability = braking_probability
        self.step_count = 0

        self.grid: list[list[Cell]] = []
        self.vehicles: list[SimVehicle] = []
        self.intersections: list[SimIntersection] = []
        self.traffic_lights: list[SimTrafficLight] = []

        self._speed_history: list[float] = []
        self._flow_history: list[int] = []

        self._next_vehicle_id = 1
        self._next_intersection_id = 1
        self._next_light_id = 1

        self._build_grid()
        self._build_road_network()
        self._place_vehicles()

    def _build_grid(self) -> None:
        """Initialize an empty grid."""
        self.grid = [
            [Cell(CellType.EMPTY) for _ in range(self.width)]
            for _ in range(self.height)
        ]

    def _build_road_network(self) -> None:
        """Build horizontal and vertical roads with intersections."""
        h_roads = []
        v_roads = []
        spacing_h = max(6, self.height // 4)
        spacing_v = max(8, self.width // 5)

        y = spacing_h
        while y < self.height - 2:
            h_roads.append(y)
            y += spacing_h

        x = spacing_v
        while x < self.width - 2:
            v_roads.append(x)
            x += spacing_v

        if not h_roads:
            h_roads = [self.height // 2]
        if not v_roads:
            v_roads = [self.width // 2]

        for road_y in h_roads:
            for col in range(self.width):
                self.grid[road_y][col] = Cell(CellType.ROAD_H)

        for road_x in v_roads:
            for row in range(self.height):
                if self.grid[row][road_x].cell_type == CellType.ROAD_H:
                    self.grid[row][road_x] = Cell(CellType.INTERSECTION)
                else:
                    self.grid[row][road_x] = Cell(CellType.ROAD_V)

        for road_y in h_roads:
            for road_x in v_roads:
                self.grid[road_y][road_x] = Cell(CellType.INTERSECTION)
                intersection = self._create_intersection(road_x, road_y)
                self.grid[road_y][road_x].intersection_id = intersection.id

    def _create_intersection(self, x: int, y: int) -> SimIntersection:
        """Create an intersection with four traffic lights."""
        iid = self._next_intersection_id
        self._next_intersection_id += 1
        name = f"Intersection-{iid}"

        intersection = SimIntersection(id=iid, name=name, x=x, y=y)

        ns_offset = random.randint(0, 10)
        ew_offset = random.randint(15, 25)

        for direction in Direction:
            lid = self._next_light_id
            self._next_light_id += 1
            if direction in (Direction.NORTH, Direction.SOUTH):
                timer_start = ns_offset
            else:
                timer_start = ew_offset
            tl = SimTrafficLight(
                id=lid,
                intersection_id=iid,
                x=x,
                y=y,
                direction=direction,
                green_duration=config.DEFAULT_GREEN_DURATION,
                yellow_duration=config.DEFAULT_YELLOW_DURATION,
                red_duration=config.DEFAULT_RED_DURATION,
                timer=timer_start,
            )
            tl.tick()
            intersection.traffic_lights.append(tl)
            self.traffic_lights.append(tl)

        self.intersections.append(intersection)
        return intersection

    def _get_road_cells(self) -> list[tuple[int, int, CellType]]:
        """Collect all road cells."""
        cells = []
        for row in range(self.height):
            for col in range(self.width):
                c = self.grid[row][col]
                if c.is_road():
                    cells.append((col, row, c.cell_type))
        return cells

    def _place_vehicles(self) -> None:
        """Place vehicles randomly on road cells."""
        road_cells = self._get_road_cells()
        random.shuffle(road_cells)

        count = min(self.vehicle_count, len(road_cells))
        for i in range(count):
            x, y, cell_type = road_cells[i]
            if cell_type == CellType.ROAD_H or cell_type == CellType.INTERSECTION:
                direction = random.choice([Direction.EAST, Direction.WEST])
            else:
                direction = random.choice([Direction.NORTH, Direction.SOUTH])

            vid = self._next_vehicle_id
            self._next_vehicle_id += 1
            v = SimVehicle(
                id=vid,
                x=x,
                y=y,
                speed=random.randint(0, self.max_speed),
                max_speed=self.max_speed,
                direction=direction,
            )
            self.vehicles.append(v)
            self.grid[y][x].vehicle_id = vid

    def _gap_ahead(self, vehicle: SimVehicle) -> int:
        """Calculate the number of empty road cells ahead of a vehicle."""
        dx, dy = self._direction_delta(vehicle.direction)
        gap = 0
        cx, cy = vehicle.x, vehicle.y

        for _ in range(vehicle.max_speed + 1):
            nx = (cx + dx) % self.width
            ny = (cy + dy) % self.height
            cell = self.grid[ny][nx]

            if not cell.is_road():
                break
            if cell.is_occupied() and cell.vehicle_id != vehicle.id:
                break

            if cell.cell_type == CellType.INTERSECTION:
                if self._is_red_for(vehicle.direction, nx, ny):
                    break

            gap += 1
            cx, cy = nx, ny

        return gap

    def _is_red_for(self, direction: Direction, x: int, y: int) -> bool:
        """Check if a traffic light is red for the given direction at (x, y)."""
        for tl in self.traffic_lights:
            if tl.x == x and tl.y == y and tl.direction == direction:
                return tl.state == LightState.RED
        return False

    @staticmethod
    def _direction_delta(direction: Direction) -> tuple[int, int]:
        """Get (dx, dy) for a direction."""
        deltas = {
            Direction.NORTH: (0, -1),
            Direction.SOUTH: (0, 1),
            Direction.EAST: (1, 0),
            Direction.WEST: (-1, 0),
        }
        return deltas[direction]

    def step(self) -> dict:
        """Advance the simulation by one time step using NaSch rules.

        Returns a dict with the current simulation state.
        """
        for tl in self.traffic_lights:
            tl.tick()

        for v in self.vehicles:
            self.grid[v.y][v.x].vehicle_id = None

        for v in self.vehicles:
            # Rule 1: Acceleration
            if v.speed < v.max_speed:
                v.speed = min(v.speed + 1, v.max_speed)

            # Rule 2: Slowing down (gap)
            gap = self._gap_ahead(v)
            if v.speed > gap:
                v.speed = max(gap, 0)

            # Rule 3: Random braking
            if v.speed > 0 and random.random() < self.braking_probability:
                v.speed = max(v.speed - 1, 0)

            # Rule 4: Movement
            dx, dy = self._direction_delta(v.direction)
            new_x = v.x
            new_y = v.y
            for _ in range(v.speed):
                nx = (new_x + dx) % self.width
                ny = (new_y + dy) % self.height
                next_cell = self.grid[ny][nx]
                if not next_cell.is_road():
                    self._try_turn(v)
                    dx, dy = self._direction_delta(v.direction)
                    nx = (new_x + dx) % self.width
                    ny = (new_y + dy) % self.height
                    next_cell = self.grid[ny][nx]
                    if not next_cell.is_road():
                        v.speed = 0
                        break
                if next_cell.is_occupied():
                    v.speed = 0
                    break
                new_x, new_y = nx, ny

            distance = abs(new_x - v.x) + abs(new_y - v.y)
            v.total_distance += distance
            v.x = new_x
            v.y = new_y

            if v.speed == 0:
                v.stopped_steps += 1

        for v in self.vehicles:
            self.grid[v.y][v.x].vehicle_id = v.id

        self.step_count += 1

        speeds = [v.speed for v in self.vehicles]
        avg_speed = sum(speeds) / len(speeds) if speeds else 0.0
        self._speed_history.append(avg_speed)

        moving = sum(1 for v in self.vehicles if v.speed > 0)
        self._flow_history.append(moving)

        heatmap = self.generate_heatmap()
        max_congestion = 0.0
        for row in heatmap:
            for val in row:
                if val > max_congestion:
                    max_congestion = val

        return {
            "step": self.step_count,
            "vehicle_count": len(self.vehicles),
            "average_speed": round(avg_speed, 2),
            "max_congestion": round(max_congestion, 2),
            "vehicles": [v.to_dict() for v in self.vehicles],
            "traffic_lights": [tl.to_dict() for tl in self.traffic_lights],
            "heatmap": heatmap,
        }

    def _try_turn(self, vehicle: SimVehicle) -> None:
        """Attempt to turn the vehicle at a dead-end or intersection."""
        possible = []
        for d in Direction:
            if d == vehicle.direction:
                continue
            dx, dy = self._direction_delta(d)
            nx = (vehicle.x + dx) % self.width
            ny = (vehicle.y + dy) % self.height
            if self.grid[ny][nx].is_road() and not self.grid[ny][nx].is_occupied():
                possible.append(d)
        if possible:
            vehicle.direction = random.choice(possible)

    def generate_heatmap(self, kernel_size: int = 3) -> list[list[float]]:
        """Generate a congestion heatmap from vehicle positions.

        Uses a simple kernel density approach: for each cell, count
        nearby vehicles within kernel_size and normalize.
        """
        density = [
            [0.0 for _ in range(self.width)]
            for _ in range(self.height)
        ]

        for v in self.vehicles:
            for dy in range(-kernel_size, kernel_size + 1):
                for dx in range(-kernel_size, kernel_size + 1):
                    ny = (v.y + dy) % self.height
                    nx = (v.x + dx) % self.width
                    dist = abs(dx) + abs(dy)
                    if dist <= kernel_size:
                        weight = 1.0 - (dist / (kernel_size + 1))
                        density[ny][nx] += weight

        max_val = 0.0
        for row in density:
            for val in row:
                if val > max_val:
                    max_val = val

        if max_val > 0:
            for r in range(self.height):
                for c in range(self.width):
                    density[r][c] = round(density[r][c] / max_val, 3)

        return density

    def get_grid_state(self) -> list[list[dict]]:
        """Export the entire grid as a list of lists of dicts."""
        return [
            [self.grid[r][c].to_dict() for c in range(self.width)]
            for r in range(self.height)
        ]

    def add_intersection(
        self,
        x: int,
        y: int,
        name: Optional[str] = None,
        green_duration: int = 30,
        yellow_duration: int = 5,
        red_duration: int = 30,
    ) -> SimIntersection:
        """Add a new intersection to the grid at (x, y)."""
        if x < 0 or x >= self.width or y < 0 or y >= self.height:
            raise ValueError(f"Position ({x}, {y}) out of grid bounds")

        self.grid[y][x] = Cell(CellType.INTERSECTION)
        iid = self._next_intersection_id
        self._next_intersection_id += 1
        if name is None:
            name = f"Intersection-{iid}"

        intersection = SimIntersection(id=iid, name=name, x=x, y=y)
        for direction in Direction:
            lid = self._next_light_id
            self._next_light_id += 1
            tl = SimTrafficLight(
                id=lid,
                intersection_id=iid,
                x=x,
                y=y,
                direction=direction,
                green_duration=green_duration,
                yellow_duration=yellow_duration,
                red_duration=red_duration,
            )
            intersection.traffic_lights.append(tl)
            self.traffic_lights.append(tl)

        self.intersections.append(intersection)
        self.grid[y][x].intersection_id = intersection.id
        return intersection

    def update_traffic_light(
        self,
        light_id: int,
        green_duration: Optional[int] = None,
        yellow_duration: Optional[int] = None,
        red_duration: Optional[int] = None,
    ) -> Optional[SimTrafficLight]:
        """Update a traffic light's cycle durations."""
        for tl in self.traffic_lights:
            if tl.id == light_id:
                if green_duration is not None:
                    tl.green_duration = green_duration
                if yellow_duration is not None:
                    tl.yellow_duration = yellow_duration
                if red_duration is not None:
                    tl.red_duration = red_duration
                return tl
        return None

    def get_statistics(self) -> dict:
        """Return current simulation statistics."""
        speeds = [v.speed for v in self.vehicles]
        avg_speed = sum(speeds) / len(speeds) if speeds else 0.0
        moving = sum(1 for v in self.vehicles if v.speed > 0)
        stopped = len(self.vehicles) - moving
        total_possible_speed = self.max_speed * len(self.vehicles) if self.vehicles else 1

        speed_dist = {}
        for s in range(self.max_speed + 1):
            speed_dist[str(s)] = sum(1 for v in self.vehicles if v.speed == s)

        return {
            "step_count": self.step_count,
            "vehicle_count": len(self.vehicles),
            "average_speed": round(avg_speed, 2),
            "vehicles_moving": moving,
            "vehicles_stopped": stopped,
            "total_distance": sum(v.total_distance for v in self.vehicles),
            "congestion_index": round(1.0 - (avg_speed / self.max_speed), 3) if self.max_speed > 0 else 0,
            "flow_efficiency": round(sum(speeds) / total_possible_speed, 3),
            "speed_distribution": speed_dist,
        }
