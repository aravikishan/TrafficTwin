<div align="center">

# TrafficTwin

[![CI](https://github.com/username/traffictwin/actions/workflows/ci.yml/badge.svg)](https://github.com/username/traffictwin/actions/workflows/ci.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109-009688.svg)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

**Urban Traffic Simulation with Cellular Automata**

Real-time traffic flow modeling using the Nagel-Schreckenberg model,
canvas-based grid visualization, congestion heatmaps, and traffic analytics.

[Features](#features) | [Quick Start](#quick-start) | [API Reference](#api-reference) | [Architecture](#architecture)

</div>

---

## Features

- **Nagel-Schreckenberg Model** -- Realistic cellular automata traffic simulation
  with four fundamental rules: acceleration, gap-based slowing, random braking,
  and movement
- **Grid-Based Road Network** -- Configurable grid with horizontal roads,
  vertical roads, and intersections automatically generated
- **Traffic Light Management** -- Fully configurable green/yellow/red cycle
  durations per direction at each intersection
- **Real-Time Visualization** -- Canvas-based grid rendering with animation
  loop, vehicle tracking, and traffic light state display
- **Congestion Heatmap** -- Dynamic overlay showing vehicle density hotspots
  using kernel-based density estimation
- **Traffic Analytics** -- Throughput, density, flow rate, speed distribution,
  congestion zone identification, and per-intersection statistics
- **Simulation Presets** -- Pre-configured scenarios: light traffic, moderate
  traffic, rush hour, and accident scenario
- **REST API** -- Full CRUD for simulations, step control, grid/heatmap
  retrieval, analytics endpoints
- **Responsive Dashboard** -- Urban dark theme with map-like styling

## Quick Start

### Prerequisites

- Python 3.10 or higher
- pip

### Installation

```bash
# Clone the repository
git clone https://github.com/username/traffictwin.git
cd traffictwin

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Running

```bash
# Option 1: Using start script
chmod +x start.sh
./start.sh

# Option 2: Direct uvicorn
uvicorn app:app --host 0.0.0.0 --port 8007 --reload

# Option 3: Docker
docker-compose up --build
```

Visit `http://localhost:8007` to open the dashboard.

### Running Tests

```bash
pytest tests/ -v
```

## API Reference

### Simulations

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/simulations` | List all simulations |
| POST | `/api/simulations` | Create a new simulation |
| GET | `/api/simulations/{id}` | Get simulation details |
| DELETE | `/api/simulations/{id}` | Delete a simulation |
| POST | `/api/simulations/{id}/step` | Advance simulation by N steps |
| POST | `/api/simulations/{id}/reset` | Reset simulation to initial state |
| GET | `/api/simulations/{id}/grid` | Get current grid state |
| GET | `/api/simulations/{id}/heatmap` | Get congestion heatmap |
| GET | `/api/simulations/{id}/vehicles` | List vehicles |

### Analytics

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/simulations/{id}/analytics` | Overall traffic analytics |
| GET | `/api/simulations/{id}/analytics/intersections` | Per-intersection stats |
| GET | `/api/simulations/{id}/analytics/timeseries` | Time series data |

### Intersections & Traffic Lights

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/simulations/{id}/intersections` | List intersections |
| POST | `/api/simulations/{id}/intersections` | Add intersection |
| PATCH | `/api/traffic-lights/{id}` | Update light timing |

### Presets

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/presets` | List simulation presets |

## Architecture

```
traffictwin/
├── app.py                  # FastAPI entry point, startup, seed data
├── config.py               # Configuration constants, presets
├── models/
│   ├── database.py         # SQLite/SQLAlchemy engine & session
│   └── schemas.py          # ORM models + Pydantic schemas
├── routes/
│   ├── api.py              # REST API endpoints
│   └── views.py            # Jinja2 HTML routes
├── services/
│   ├── simulator.py        # NaSch cellular automata engine
│   └── analytics.py        # Traffic flow analysis
├── templates/              # Jinja2 HTML templates
├── static/
│   ├── css/style.css       # Urban dark theme
│   └── js/main.js          # Canvas rendering & UI logic
├── tests/                  # pytest test suite
└── seed_data/data.json     # Initial data
```

### Nagel-Schreckenberg Model

The simulation engine implements the classic NaSch cellular automata model
for traffic flow. Each vehicle on the grid follows four rules per time step:

1. **Acceleration**: `v = min(v + 1, v_max)` -- vehicles try to go faster
2. **Slowing**: `v = min(v, gap - 1)` -- vehicles slow for the car ahead
3. **Random Braking**: `v = max(v - 1, 0)` with probability `p` -- models
   human unpredictability
4. **Movement**: `x = x + v` -- vehicles advance by their speed

Traffic lights at intersections block vehicles when red for their direction
of travel, creating realistic stop-and-go patterns and queue formation.

### Congestion Heatmap

The heatmap uses kernel density estimation centered on each vehicle position.
Nearby cells receive weighted contributions (higher weight = closer to vehicle),
and values are normalized to [0, 1] for color mapping in the canvas overlay.

## Configuration

Key settings in `config.py`:

| Setting | Default | Description |
|---------|---------|-------------|
| `DEFAULT_GRID_WIDTH` | 40 | Grid width in cells |
| `DEFAULT_GRID_HEIGHT` | 30 | Grid height in cells |
| `MAX_SPEED` | 5 | Maximum vehicle speed |
| `RANDOM_BRAKING_PROBABILITY` | 0.3 | Probability of random deceleration |
| `DEFAULT_GREEN_DURATION` | 30 | Green light duration (steps) |
| `DEFAULT_RED_DURATION` | 30 | Red light duration (steps) |

## Tech Stack

- **Backend**: Python 3.10+ / FastAPI
- **Database**: SQLite / SQLAlchemy 2.0
- **Templates**: Jinja2
- **Visualization**: HTML5 Canvas
- **Styling**: Custom CSS (urban dark theme)
- **Testing**: pytest / httpx
- **CI/CD**: GitHub Actions

## Docker

```bash
# Build and run
docker-compose up --build

# Run in background
docker-compose up -d

# View logs
docker-compose logs -f traffictwin
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

---

<div align="center">
  <sub>Built with FastAPI and the Nagel-Schreckenberg cellular automata model</sub>
</div>
