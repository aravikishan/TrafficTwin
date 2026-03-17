"""API endpoint tests for TrafficTwin."""

import pytest


class TestSimulationAPI:
    """Tests for simulation CRUD and control endpoints."""

    def test_create_simulation(self, client):
        resp = client.post(
            "/api/simulations",
            json={"name": "City Grid", "grid_width": 20, "grid_height": 15, "vehicle_count": 10},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "City Grid"
        assert data["grid_width"] == 20
        assert data["grid_height"] == 15
        assert data["vehicle_count"] == 10
        assert data["status"] == "created"

    def test_list_simulations(self, client, sample_simulation):
        resp = client.get("/api/simulations")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_get_simulation(self, client, sample_simulation):
        sim_id = sample_simulation["id"]
        resp = client.get(f"/api/simulations/{sim_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == sim_id
        assert data["name"] == "Test Simulation"

    def test_get_simulation_not_found(self, client):
        resp = client.get("/api/simulations/9999")
        assert resp.status_code == 404

    def test_step_simulation(self, client, sample_simulation):
        sim_id = sample_simulation["id"]
        resp = client.post(f"/api/simulations/{sim_id}/step?steps=3")
        assert resp.status_code == 200
        data = resp.json()
        assert data["step"] == 3
        assert "average_speed" in data
        assert "vehicles" in data
        assert "heatmap" in data

    def test_reset_simulation(self, client, sample_simulation):
        sim_id = sample_simulation["id"]
        client.post(f"/api/simulations/{sim_id}/step?steps=5")
        resp = client.post(f"/api/simulations/{sim_id}/reset")
        assert resp.status_code == 200
        assert resp.json()["message"] == "Simulation reset"

    def test_get_grid(self, client, sample_simulation):
        sim_id = sample_simulation["id"]
        resp = client.get(f"/api/simulations/{sim_id}/grid")
        assert resp.status_code == 200
        data = resp.json()
        assert data["width"] == 20
        assert data["height"] == 15
        assert len(data["grid"]) == 15
        assert len(data["grid"][0]) == 20

    def test_get_heatmap(self, client, sample_simulation):
        sim_id = sample_simulation["id"]
        resp = client.get(f"/api/simulations/{sim_id}/heatmap")
        assert resp.status_code == 200
        data = resp.json()
        assert "heatmap" in data
        assert len(data["heatmap"]) == 15

    def test_delete_simulation(self, client, sample_simulation):
        sim_id = sample_simulation["id"]
        resp = client.delete(f"/api/simulations/{sim_id}")
        assert resp.status_code == 204
        resp = client.get(f"/api/simulations/{sim_id}")
        assert resp.status_code == 404

    def test_list_presets(self, client):
        resp = client.get("/api/presets")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 4
        names = [p["name"] for p in data]
        assert "rush_hour" in names
        assert "light_traffic" in names


class TestAnalyticsAPI:
    """Tests for analytics endpoints."""

    def test_get_analytics(self, client, sample_simulation):
        sim_id = sample_simulation["id"]
        client.post(f"/api/simulations/{sim_id}/step?steps=5")
        resp = client.get(f"/api/simulations/{sim_id}/analytics")
        assert resp.status_code == 200
        data = resp.json()
        assert "average_speed" in data
        assert "throughput" in data
        assert "density" in data
        assert "congestion_index" in data

    def test_get_intersection_analytics(self, client, sample_simulation):
        sim_id = sample_simulation["id"]
        client.post(f"/api/simulations/{sim_id}/step?steps=3")
        resp = client.get(f"/api/simulations/{sim_id}/analytics/intersections")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
