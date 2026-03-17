"""Pytest fixtures for TrafficTwin tests."""

import os
import sys

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Ensure the project root is on the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import config
config.TESTING = True
config.SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"

from models.database import Base, get_db
from app import app


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh in-memory database session for each test."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestSession()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    """Create a test client with database dependency override."""
    def _override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as tc:
        yield tc
    app.dependency_overrides.clear()


@pytest.fixture
def sample_simulation(client):
    """Create a sample simulation and return its data."""
    resp = client.post(
        "/api/simulations",
        json={
            "name": "Test Simulation",
            "grid_width": 20,
            "grid_height": 15,
            "vehicle_count": 10,
            "max_speed": 5,
            "braking_probability": 0.3,
        },
    )
    assert resp.status_code == 201
    return resp.json()
