"""REST API endpoints for TrafficTwin."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

import config
from models.database import get_db
from models.schemas import (
    AnalyticsResponse,
    IntersectionCreate,
    IntersectionResponse,
    PresetResponse,
    Simulation,
    SimulationCreate,
    SimulationResponse,
    SimulationStatus,
    SimulationStepResult,
    TrafficLightUpdate,
    Intersection,
    TrafficLight,
    Vehicle,
    Direction,
    LightState,
)
from services.analytics import (
    compute_analytics,
    compute_intersection_stats,
    generate_time_series,
)
from services.simulator import TrafficSimulator

router = APIRouter(prefix="/api", tags=["api"])

# In-memory simulator instances keyed by simulation ID
_simulators: dict[int, TrafficSimulator] = {}


def _get_or_create_simulator(sim: Simulation) -> TrafficSimulator:
    """Retrieve or create a TrafficSimulator for a given simulation record."""
    if sim.id not in _simulators:
        _simulators[sim.id] = TrafficSimulator(
            width=sim.grid_width,
            height=sim.grid_height,
            vehicle_count=sim.vehicle_count,
            max_speed=sim.max_speed,
            braking_probability=sim.braking_probability,
        )
    return _simulators[sim.id]


# ---- Simulation CRUD ----


@router.get("/simulations", response_model=list[SimulationResponse])
def list_simulations(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """List all simulations with pagination."""
    sims = db.query(Simulation).offset(skip).limit(limit).all()
    return [SimulationResponse(**s.to_dict()) for s in sims]


@router.post("/simulations", response_model=SimulationResponse, status_code=201)
def create_simulation(data: SimulationCreate, db: Session = Depends(get_db)):
    """Create a new traffic simulation."""
    params = data.model_dump()
    if data.preset and data.preset in config.PRESETS:
        preset = config.PRESETS[data.preset]
        params["vehicle_count"] = preset["vehicle_count"]
        params["max_speed"] = preset["max_speed"]
        params["braking_probability"] = preset["braking_probability"]

    sim = Simulation(**params)
    db.add(sim)
    db.commit()
    db.refresh(sim)

    simulator = _get_or_create_simulator(sim)

    for isec in simulator.intersections:
        db_isec = Intersection(
            simulation_id=sim.id,
            name=isec.name,
            x=isec.x,
            y=isec.y,
        )
        db.add(db_isec)
        db.flush()
        for tl in isec.traffic_lights:
            db_tl = TrafficLight(
                intersection_id=db_isec.id,
                direction=tl.direction,
                state=tl.state,
                green_duration=tl.green_duration,
                yellow_duration=tl.yellow_duration,
                red_duration=tl.red_duration,
                timer=tl.timer,
            )
            db.add(db_tl)

    for v in simulator.vehicles:
        db_v = Vehicle(
            simulation_id=sim.id,
            x=v.x,
            y=v.y,
            speed=v.speed,
            max_speed=v.max_speed,
            direction=v.direction,
        )
        db.add(db_v)

    db.commit()
    db.refresh(sim)
    return SimulationResponse(**sim.to_dict())


@router.get("/simulations/{sim_id}", response_model=SimulationResponse)
def get_simulation(sim_id: int, db: Session = Depends(get_db)):
    """Get a simulation by ID."""
    sim = db.query(Simulation).filter(Simulation.id == sim_id).first()
    if not sim:
        raise HTTPException(status_code=404, detail="Simulation not found")
    return SimulationResponse(**sim.to_dict())


@router.delete("/simulations/{sim_id}", status_code=204)
def delete_simulation(sim_id: int, db: Session = Depends(get_db)):
    """Delete a simulation."""
    sim = db.query(Simulation).filter(Simulation.id == sim_id).first()
    if not sim:
        raise HTTPException(status_code=404, detail="Simulation not found")
    _simulators.pop(sim_id, None)
    db.delete(sim)
    db.commit()


# ---- Simulation Control ----


@router.post("/simulations/{sim_id}/step", response_model=SimulationStepResult)
def step_simulation(sim_id: int, steps: int = Query(1, ge=1, le=100), db: Session = Depends(get_db)):
    """Advance the simulation by one or more steps."""
    sim = db.query(Simulation).filter(Simulation.id == sim_id).first()
    if not sim:
        raise HTTPException(status_code=404, detail="Simulation not found")

    simulator = _get_or_create_simulator(sim)
    result = None
    for _ in range(steps):
        result = simulator.step()

    sim.total_steps = simulator.step_count
    sim.status = SimulationStatus.RUNNING
    db.commit()

    return SimulationStepResult(**result)


@router.post("/simulations/{sim_id}/reset")
def reset_simulation(sim_id: int, db: Session = Depends(get_db)):
    """Reset a simulation to its initial state."""
    sim = db.query(Simulation).filter(Simulation.id == sim_id).first()
    if not sim:
        raise HTTPException(status_code=404, detail="Simulation not found")

    _simulators[sim_id] = TrafficSimulator(
        width=sim.grid_width,
        height=sim.grid_height,
        vehicle_count=sim.vehicle_count,
        max_speed=sim.max_speed,
        braking_probability=sim.braking_probability,
    )
    sim.total_steps = 0
    sim.status = SimulationStatus.CREATED
    db.commit()
    return {"message": "Simulation reset", "id": sim_id}


@router.get("/simulations/{sim_id}/grid")
def get_grid(sim_id: int, db: Session = Depends(get_db)):
    """Get the current grid state."""
    sim = db.query(Simulation).filter(Simulation.id == sim_id).first()
    if not sim:
        raise HTTPException(status_code=404, detail="Simulation not found")
    simulator = _get_or_create_simulator(sim)
    return {
        "width": simulator.width,
        "height": simulator.height,
        "grid": simulator.get_grid_state(),
    }


@router.get("/simulations/{sim_id}/heatmap")
def get_heatmap(sim_id: int, db: Session = Depends(get_db)):
    """Get the current congestion heatmap."""
    sim = db.query(Simulation).filter(Simulation.id == sim_id).first()
    if not sim:
        raise HTTPException(status_code=404, detail="Simulation not found")
    simulator = _get_or_create_simulator(sim)
    return {
        "width": simulator.width,
        "height": simulator.height,
        "heatmap": simulator.generate_heatmap(),
    }


# ---- Analytics ----


@router.get("/simulations/{sim_id}/analytics", response_model=AnalyticsResponse)
def get_analytics(sim_id: int, db: Session = Depends(get_db)):
    """Get traffic analytics for a simulation."""
    sim = db.query(Simulation).filter(Simulation.id == sim_id).first()
    if not sim:
        raise HTTPException(status_code=404, detail="Simulation not found")
    simulator = _get_or_create_simulator(sim)
    data = compute_analytics(simulator)
    data["simulation_id"] = sim_id
    return AnalyticsResponse(**data)


@router.get("/simulations/{sim_id}/analytics/intersections")
def get_intersection_analytics(sim_id: int, db: Session = Depends(get_db)):
    """Get per-intersection traffic analytics."""
    sim = db.query(Simulation).filter(Simulation.id == sim_id).first()
    if not sim:
        raise HTTPException(status_code=404, detail="Simulation not found")
    simulator = _get_or_create_simulator(sim)
    return compute_intersection_stats(simulator)


@router.get("/simulations/{sim_id}/analytics/timeseries")
def get_time_series(sim_id: int, db: Session = Depends(get_db)):
    """Get time series data for charts."""
    sim = db.query(Simulation).filter(Simulation.id == sim_id).first()
    if not sim:
        raise HTTPException(status_code=404, detail="Simulation not found")
    simulator = _get_or_create_simulator(sim)
    return generate_time_series(simulator)


# ---- Intersections ----


@router.get("/simulations/{sim_id}/intersections", response_model=list[IntersectionResponse])
def list_intersections(sim_id: int, db: Session = Depends(get_db)):
    """List all intersections for a simulation."""
    sim = db.query(Simulation).filter(Simulation.id == sim_id).first()
    if not sim:
        raise HTTPException(status_code=404, detail="Simulation not found")
    intersections = (
        db.query(Intersection)
        .filter(Intersection.simulation_id == sim_id)
        .all()
    )
    return [IntersectionResponse(**i.to_dict()) for i in intersections]


@router.post(
    "/simulations/{sim_id}/intersections",
    response_model=IntersectionResponse,
    status_code=201,
)
def create_intersection(
    sim_id: int, data: IntersectionCreate, db: Session = Depends(get_db)
):
    """Add a new intersection to a simulation."""
    sim = db.query(Simulation).filter(Simulation.id == sim_id).first()
    if not sim:
        raise HTTPException(status_code=404, detail="Simulation not found")

    simulator = _get_or_create_simulator(sim)
    try:
        sim_isec = simulator.add_intersection(
            x=data.x,
            y=data.y,
            name=data.name,
            green_duration=data.green_duration,
            yellow_duration=data.yellow_duration,
            red_duration=data.red_duration,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    db_isec = Intersection(
        simulation_id=sim_id,
        name=data.name,
        x=data.x,
        y=data.y,
    )
    db.add(db_isec)
    db.flush()

    for tl in sim_isec.traffic_lights:
        db_tl = TrafficLight(
            intersection_id=db_isec.id,
            direction=tl.direction,
            state=tl.state,
            green_duration=tl.green_duration,
            yellow_duration=tl.yellow_duration,
            red_duration=tl.red_duration,
            timer=tl.timer,
        )
        db.add(db_tl)

    db.commit()
    db.refresh(db_isec)
    return IntersectionResponse(**db_isec.to_dict())


# ---- Traffic Lights ----


@router.patch("/traffic-lights/{light_id}")
def update_traffic_light(
    light_id: int, data: TrafficLightUpdate, db: Session = Depends(get_db)
):
    """Update a traffic light's timing."""
    db_tl = db.query(TrafficLight).filter(TrafficLight.id == light_id).first()
    if not db_tl:
        raise HTTPException(status_code=404, detail="Traffic light not found")

    if data.green_duration is not None:
        db_tl.green_duration = data.green_duration
    if data.yellow_duration is not None:
        db_tl.yellow_duration = data.yellow_duration
    if data.red_duration is not None:
        db_tl.red_duration = data.red_duration
    db.commit()

    intersection = db.query(Intersection).filter(
        Intersection.id == db_tl.intersection_id
    ).first()
    if intersection:
        sim_id = intersection.simulation_id
        if sim_id in _simulators:
            _simulators[sim_id].update_traffic_light(
                light_id,
                green_duration=data.green_duration,
                yellow_duration=data.yellow_duration,
                red_duration=data.red_duration,
            )

    return {"message": "Traffic light updated", "id": light_id}


# ---- Presets ----


@router.get("/presets", response_model=list[PresetResponse])
def list_presets():
    """List all available simulation presets."""
    results = []
    for name, preset in config.PRESETS.items():
        results.append(PresetResponse(name=name, **preset))
    return results


# ---- Vehicles ----


@router.get("/simulations/{sim_id}/vehicles")
def list_vehicles(sim_id: int, db: Session = Depends(get_db)):
    """List vehicles in the current simulation state."""
    sim = db.query(Simulation).filter(Simulation.id == sim_id).first()
    if not sim:
        raise HTTPException(status_code=404, detail="Simulation not found")
    simulator = _get_or_create_simulator(sim)
    return [v.to_dict() for v in simulator.vehicles]
