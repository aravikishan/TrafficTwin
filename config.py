"""Application configuration for TrafficTwin."""

import os

# Server
HOST = "0.0.0.0"
PORT = int(os.environ.get("TRAFFICTWIN_PORT", 8007))
DEBUG = os.environ.get("TRAFFICTWIN_DEBUG", "false").lower() == "true"

# Database
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATABASE_PATH = os.path.join(BASE_DIR, "instance", "traffictwin.db")
SQLALCHEMY_DATABASE_URI = os.environ.get(
    "DATABASE_URL", f"sqlite:///{DATABASE_PATH}"
)

# Application
APP_NAME = "TrafficTwin"
APP_VERSION = "1.0.0"
APP_DESCRIPTION = "Urban Traffic Simulation with Cellular Automata"

# Grid defaults
DEFAULT_GRID_WIDTH = 40
DEFAULT_GRID_HEIGHT = 30
DEFAULT_CELL_SIZE = 16

# Nagel-Schreckenberg model parameters
MAX_SPEED = 5
RANDOM_BRAKING_PROBABILITY = 0.3
DEFAULT_VEHICLE_COUNT = 60

# Traffic light defaults
DEFAULT_GREEN_DURATION = 30
DEFAULT_YELLOW_DURATION = 5
DEFAULT_RED_DURATION = 30

# Simulation presets
PRESETS = {
    "light_traffic": {
        "vehicle_count": 20,
        "max_speed": 5,
        "braking_probability": 0.15,
        "green_duration": 40,
        "red_duration": 20,
        "description": "Low density traffic with favorable light timing",
    },
    "moderate_traffic": {
        "vehicle_count": 60,
        "max_speed": 5,
        "braking_probability": 0.3,
        "green_duration": 30,
        "red_duration": 30,
        "description": "Normal urban traffic conditions",
    },
    "rush_hour": {
        "vehicle_count": 120,
        "max_speed": 3,
        "braking_probability": 0.5,
        "green_duration": 25,
        "red_duration": 35,
        "description": "High density peak-hour traffic",
    },
    "accident_scenario": {
        "vehicle_count": 80,
        "max_speed": 2,
        "braking_probability": 0.7,
        "green_duration": 20,
        "red_duration": 40,
        "description": "Simulates blocked lanes and slow-moving traffic",
    },
}

# Congestion thresholds (vehicles per cell density)
CONGESTION_LOW = 0.2
CONGESTION_MODERATE = 0.5
CONGESTION_HIGH = 0.75
CONGESTION_SEVERE = 0.9

# Seed data
SEED_DATA_PATH = os.path.join(BASE_DIR, "seed_data", "data.json")

# Testing
TESTING = False
