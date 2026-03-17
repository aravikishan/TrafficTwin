"""Model and schema tests for TrafficTwin."""

import pytest
from models.schemas import (
    CellType,
    Direction,
    LightState,
    SimulationCreate,
    SimulationStatus,
    IntersectionCreate,
    TrafficLightUpdate,
)


class TestEnums:
    """Tests for model enumerations."""

    def test_direction_values(self):
        assert Direction.NORTH == "north"
        assert Direction.SOUTH == "south"
        assert Direction.EAST == "east"
        assert Direction.WEST == "west"

    def test_light_state_values(self):
        assert LightState.RED == "red"
        assert LightState.GREEN == "green"
        assert LightState.YELLOW == "yellow"

    def test_cell_type_values(self):
        assert CellType.EMPTY == "empty"
        assert CellType.ROAD_H == "road_h"
        assert CellType.ROAD_V == "road_v"
        assert CellType.INTERSECTION == "intersection"

    def test_simulation_status_values(self):
        assert SimulationStatus.CREATED == "created"
        assert SimulationStatus.RUNNING == "running"
        assert SimulationStatus.COMPLETED == "completed"


class TestPydanticSchemas:
    """Tests for Pydantic validation schemas."""

    def test_simulation_create_defaults(self):
        sim = SimulationCreate(name="Test")
        assert sim.grid_width == 40
        assert sim.grid_height == 30
        assert sim.vehicle_count == 60
        assert sim.max_speed == 5
        assert sim.braking_probability == 0.3

    def test_simulation_create_validation(self):
        with pytest.raises(Exception):
            SimulationCreate(name="")

    def test_intersection_create(self):
        isec = IntersectionCreate(name="Main St", x=10, y=5)
        assert isec.name == "Main St"
        assert isec.green_duration == 30

    def test_traffic_light_update_partial(self):
        update = TrafficLightUpdate(green_duration=45)
        assert update.green_duration == 45
        assert update.yellow_duration is None
        assert update.red_duration is None
