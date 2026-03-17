"""Service layer tests for TrafficTwin."""

import pytest

from services.simulator import TrafficSimulator, SimVehicle, Cell, CellType
from services.analytics import compute_analytics, _count_road_cells, _severity_label


class TestTrafficSimulator:
    """Tests for the Nagel-Schreckenberg simulator."""

    def test_initialization(self):
        sim = TrafficSimulator(width=20, height=15, vehicle_count=10)
        assert sim.width == 20
        assert sim.height == 15
        assert len(sim.vehicles) <= 10
        assert sim.step_count == 0

    def test_grid_has_roads(self):
        sim = TrafficSimulator(width=20, height=15, vehicle_count=5)
        road_count = _count_road_cells(sim)
        assert road_count > 0, "Grid should contain road cells"

    def test_step_advances(self):
        sim = TrafficSimulator(width=20, height=15, vehicle_count=5)
        result = sim.step()
        assert result["step"] == 1
        assert "average_speed" in result
        assert "vehicles" in result
        assert "heatmap" in result

    def test_multiple_steps(self):
        sim = TrafficSimulator(width=20, height=15, vehicle_count=5, max_speed=3)
        for _ in range(10):
            result = sim.step()
        assert result["step"] == 10

    def test_heatmap_dimensions(self):
        sim = TrafficSimulator(width=20, height=15, vehicle_count=5)
        heatmap = sim.generate_heatmap()
        assert len(heatmap) == 15
        assert len(heatmap[0]) == 20

    def test_heatmap_values_normalized(self):
        sim = TrafficSimulator(width=20, height=15, vehicle_count=10)
        heatmap = sim.generate_heatmap()
        for row in heatmap:
            for val in row:
                assert 0.0 <= val <= 1.0

    def test_grid_state_export(self):
        sim = TrafficSimulator(width=10, height=8, vehicle_count=3)
        state = sim.get_grid_state()
        assert len(state) == 8
        assert len(state[0]) == 10
        assert "type" in state[0][0]

    def test_intersections_created(self):
        sim = TrafficSimulator(width=30, height=20, vehicle_count=10)
        assert len(sim.intersections) > 0
        for isec in sim.intersections:
            assert len(isec.traffic_lights) == 4

    def test_statistics(self):
        sim = TrafficSimulator(width=20, height=15, vehicle_count=5)
        sim.step()
        stats = sim.get_statistics()
        assert "average_speed" in stats
        assert "vehicles_moving" in stats
        assert "vehicles_stopped" in stats
        assert "speed_distribution" in stats
        assert stats["vehicle_count"] == len(sim.vehicles)

    def test_add_intersection(self):
        sim = TrafficSimulator(width=20, height=15, vehicle_count=5)
        initial_count = len(sim.intersections)
        sim.add_intersection(x=5, y=5, name="Test Intersection")
        assert len(sim.intersections) == initial_count + 1
        new_isec = sim.intersections[-1]
        assert new_isec.name == "Test Intersection"
        assert new_isec.x == 5
        assert new_isec.y == 5


class TestAnalytics:
    """Tests for traffic analytics functions."""

    def test_compute_analytics(self):
        sim = TrafficSimulator(width=20, height=15, vehicle_count=5)
        for _ in range(5):
            sim.step()
        data = compute_analytics(sim)
        assert "average_speed" in data
        assert "throughput" in data
        assert "density" in data
        assert "congestion_zones" in data

    def test_severity_labels(self):
        assert _severity_label(0.0) == "none"
        assert _severity_label(0.25) == "low"
        assert _severity_label(0.55) == "moderate"
        assert _severity_label(0.8) == "high"
        assert _severity_label(0.95) == "severe"
