"""SQLAlchemy ORM models and Pydantic schemas for TrafficTwin."""

from __future__ import annotations

import json
from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional

from pydantic import BaseModel, Field
from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import relationship

from models.database import Base


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class Direction(str, PyEnum):
    NORTH = "north"
    SOUTH = "south"
    EAST = "east"
    WEST = "west"


class LightState(str, PyEnum):
    RED = "red"
    YELLOW = "yellow"
    GREEN = "green"


class CellType(str, PyEnum):
    EMPTY = "empty"
    ROAD_H = "road_h"
    ROAD_V = "road_v"
    INTERSECTION = "intersection"
    BLOCKED = "blocked"


class SimulationStatus(str, PyEnum):
    CREATED = "created"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"


# ---------------------------------------------------------------------------
# SQLAlchemy Models
# ---------------------------------------------------------------------------


class Simulation(Base):
    __tablename__ = "simulations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    status = Column(
        Enum(SimulationStatus), default=SimulationStatus.CREATED, nullable=False
    )
    grid_width = Column(Integer, nullable=False, default=40)
    grid_height = Column(Integer, nullable=False, default=30)
    vehicle_count = Column(Integer, nullable=False, default=60)
    max_speed = Column(Integer, nullable=False, default=5)
    braking_probability = Column(Float, nullable=False, default=0.3)
    total_steps = Column(Integer, default=0)
    preset = Column(String(50), nullable=True)
    grid_state = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    intersections = relationship(
        "Intersection", back_populates="simulation", cascade="all, delete-orphan"
    )
    vehicles = relationship(
        "Vehicle", back_populates="simulation", cascade="all, delete-orphan"
    )

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "status": self.status.value if self.status else None,
            "grid_width": self.grid_width,
            "grid_height": self.grid_height,
            "vehicle_count": self.vehicle_count,
            "max_speed": self.max_speed,
            "braking_probability": self.braking_probability,
            "total_steps": self.total_steps,
            "preset": self.preset,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class Intersection(Base):
    __tablename__ = "intersections"

    id = Column(Integer, primary_key=True, autoincrement=True)
    simulation_id = Column(Integer, ForeignKey("simulations.id"), nullable=False)
    name = Column(String(100), nullable=False)
    x = Column(Integer, nullable=False)
    y = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=func.now())

    simulation = relationship("Simulation", back_populates="intersections")
    traffic_lights = relationship(
        "TrafficLight", back_populates="intersection", cascade="all, delete-orphan"
    )

    def to_dict(self):
        return {
            "id": self.id,
            "simulation_id": self.simulation_id,
            "name": self.name,
            "x": self.x,
            "y": self.y,
            "traffic_lights": [tl.to_dict() for tl in self.traffic_lights],
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class TrafficLight(Base):
    __tablename__ = "traffic_lights"

    id = Column(Integer, primary_key=True, autoincrement=True)
    intersection_id = Column(Integer, ForeignKey("intersections.id"), nullable=False)
    direction = Column(Enum(Direction), nullable=False)
    state = Column(Enum(LightState), default=LightState.RED, nullable=False)
    green_duration = Column(Integer, default=30)
    yellow_duration = Column(Integer, default=5)
    red_duration = Column(Integer, default=30)
    timer = Column(Integer, default=0)
    created_at = Column(DateTime, default=func.now())

    intersection = relationship("Intersection", back_populates="traffic_lights")

    def to_dict(self):
        return {
            "id": self.id,
            "intersection_id": self.intersection_id,
            "direction": self.direction.value if self.direction else None,
            "state": self.state.value if self.state else None,
            "green_duration": self.green_duration,
            "yellow_duration": self.yellow_duration,
            "red_duration": self.red_duration,
            "timer": self.timer,
        }


class Vehicle(Base):
    __tablename__ = "vehicles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    simulation_id = Column(Integer, ForeignKey("simulations.id"), nullable=False)
    x = Column(Integer, nullable=False)
    y = Column(Integer, nullable=False)
    speed = Column(Integer, default=0)
    max_speed = Column(Integer, default=5)
    direction = Column(Enum(Direction), nullable=False)
    created_at = Column(DateTime, default=func.now())

    simulation = relationship("Simulation", back_populates="vehicles")

    def to_dict(self):
        return {
            "id": self.id,
            "simulation_id": self.simulation_id,
            "x": self.x,
            "y": self.y,
            "speed": self.speed,
            "max_speed": self.max_speed,
            "direction": self.direction.value if self.direction else None,
        }


# ---------------------------------------------------------------------------
# Pydantic Schemas
# ---------------------------------------------------------------------------


class SimulationCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    grid_width: int = Field(default=40, ge=10, le=100)
    grid_height: int = Field(default=30, ge=10, le=100)
    vehicle_count: int = Field(default=60, ge=1, le=500)
    max_speed: int = Field(default=5, ge=1, le=10)
    braking_probability: float = Field(default=0.3, ge=0.0, le=1.0)
    preset: Optional[str] = None


class SimulationResponse(BaseModel):
    id: int
    name: str
    status: str
    grid_width: int
    grid_height: int
    vehicle_count: int
    max_speed: int
    braking_probability: float
    total_steps: int
    preset: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    model_config = {"from_attributes": True}


class IntersectionCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    x: int = Field(..., ge=0)
    y: int = Field(..., ge=0)
    green_duration: int = Field(default=30, ge=5, le=120)
    yellow_duration: int = Field(default=5, ge=2, le=15)
    red_duration: int = Field(default=30, ge=5, le=120)


class IntersectionResponse(BaseModel):
    id: int
    simulation_id: int
    name: str
    x: int
    y: int
    traffic_lights: list = Field(default_factory=list)
    created_at: Optional[str] = None

    model_config = {"from_attributes": True}


class TrafficLightUpdate(BaseModel):
    green_duration: Optional[int] = Field(None, ge=5, le=120)
    yellow_duration: Optional[int] = Field(None, ge=2, le=15)
    red_duration: Optional[int] = Field(None, ge=5, le=120)


class VehicleResponse(BaseModel):
    id: int
    simulation_id: int
    x: int
    y: int
    speed: int
    max_speed: int
    direction: str

    model_config = {"from_attributes": True}


class SimulationStepResult(BaseModel):
    step: int
    vehicle_count: int
    average_speed: float
    max_congestion: float
    vehicles: list[dict] = Field(default_factory=list)
    traffic_lights: list[dict] = Field(default_factory=list)
    heatmap: list[list[float]] = Field(default_factory=list)


class AnalyticsResponse(BaseModel):
    simulation_id: int
    total_steps: int
    average_speed: float
    throughput: float
    density: float
    congestion_index: float
    flow_rate: float
    vehicles_stopped: int
    vehicles_moving: int
    speed_distribution: dict = Field(default_factory=dict)
    congestion_zones: list[dict] = Field(default_factory=list)


class PresetResponse(BaseModel):
    name: str
    vehicle_count: int
    max_speed: int
    braking_probability: float
    green_duration: int
    red_duration: int
    description: str
