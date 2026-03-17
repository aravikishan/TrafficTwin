"""TrafficTwin -- FastAPI application entry point.

Urban traffic simulation using Nagel-Schreckenberg cellular automata
with real-time grid visualization and congestion heatmaps.
"""

from __future__ import annotations

import json
import os

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

import config
from models.database import init_db, SessionLocal
from models.schemas import Simulation, Intersection, TrafficLight, Vehicle, Direction, LightState
from routes.api import router as api_router
from routes.views import router as views_router

app = FastAPI(
    title=config.APP_NAME,
    version=config.APP_VERSION,
    description=config.APP_DESCRIPTION,
)

# v1.0.1 - Mount static files
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.isdir(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Include routers
app.include_router(api_router)
app.include_router(views_router)


@app.on_event("startup")
# Updated for clarity
def startup():
    """Initialize database and load seed data on startup."""
    init_db()
    _load_seed_data()


def _load_seed_data():
    """Load seed data from JSON file if the database is empty."""
    db = SessionLocal()
    try:
        count = db.query(Simulation).count()
        if count > 0:
            return

        seed_path = config.SEED_DATA_PATH
        if not os.path.exists(seed_path):
            return

        with open(seed_path, "r") as f:
            data = json.load(f)

        for sim_data in data.get("simulations", []):
            sim = Simulation(
                name=sim_data["name"],
                grid_width=sim_data.get("grid_width", config.DEFAULT_GRID_WIDTH),
                grid_height=sim_data.get("grid_height", config.DEFAULT_GRID_HEIGHT),
                vehicle_count=sim_data.get("vehicle_count", config.DEFAULT_VEHICLE_COUNT),
                max_speed=sim_data.get("max_speed", config.MAX_SPEED),
                braking_probability=sim_data.get(
                    "braking_probability", config.RANDOM_BRAKING_PROBABILITY
                ),
                preset=sim_data.get("preset"),
            )
            db.add(sim)
            db.flush()

            for isec_data in sim_data.get("intersections", []):
                isec = Intersection(
                    simulation_id=sim.id,
                    name=isec_data["name"],
                    x=isec_data["x"],
                    y=isec_data["y"],
                )
                db.add(isec)
                db.flush()

                for tl_data in isec_data.get("traffic_lights", []):
                    tl = TrafficLight(
                        intersection_id=isec.id,
                        direction=Direction(tl_data["direction"]),
                        state=LightState(tl_data.get("state", "red")),
                        green_duration=tl_data.get("green_duration", 30),
                        yellow_duration=tl_data.get("yellow_duration", 5),
                        red_duration=tl_data.get("red_duration", 30),
                    )
                    db.add(tl)

        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()
