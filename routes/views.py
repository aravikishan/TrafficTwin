"""HTML-serving routes using Jinja2Templates."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

import config
from models.database import get_db
from models.schemas import Simulation

router = APIRouter(tags=["views"])
templates = Jinja2Templates(directory="templates")


@router.get("/")
def index(request: Request, db: Session = Depends(get_db)):
    """Dashboard / home page."""
    simulations = db.query(Simulation).order_by(Simulation.id.desc()).limit(10).all()
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "simulations": simulations,
            "presets": config.PRESETS,
            "app_name": config.APP_NAME,
        },
    )


@router.get("/simulate")
def simulate_page(request: Request, db: Session = Depends(get_db)):
    """Simulation runner page."""
    simulations = db.query(Simulation).order_by(Simulation.id.desc()).all()
    return templates.TemplateResponse(
        "simulate.html",
        {
            "request": request,
            "simulations": simulations,
            "presets": config.PRESETS,
            "app_name": config.APP_NAME,
            "default_width": config.DEFAULT_GRID_WIDTH,
            "default_height": config.DEFAULT_GRID_HEIGHT,
        },
    )


@router.get("/analytics")
def analytics_page(request: Request, db: Session = Depends(get_db)):
    """Traffic analytics page."""
    simulations = db.query(Simulation).order_by(Simulation.id.desc()).all()
    return templates.TemplateResponse(
        "analytics.html",
        {
            "request": request,
            "simulations": simulations,
            "app_name": config.APP_NAME,
        },
    )


@router.get("/intersections")
def intersections_page(request: Request, db: Session = Depends(get_db)):
    """Intersection management page."""
    simulations = db.query(Simulation).order_by(Simulation.id.desc()).all()
    return templates.TemplateResponse(
        "intersections.html",
        {
            "request": request,
            "simulations": simulations,
            "app_name": config.APP_NAME,
        },
    )


@router.get("/about")
def about_page(request: Request):
    """About page."""
    return templates.TemplateResponse(
        "about.html",
        {
            "request": request,
            "app_name": config.APP_NAME,
            "version": config.APP_VERSION,
            "description": config.APP_DESCRIPTION,
        },
    )
