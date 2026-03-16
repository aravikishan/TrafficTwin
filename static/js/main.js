/**
 * TrafficTwin -- Canvas-based grid rendering, animation loop, heatmap overlay.
 */

(function () {
    'use strict';

    // ---- State ----
    let activeSimId = null;
    let canvas = null;
    let ctx = null;
    let playInterval = null;
    let showHeatmap = false;
    let lastStepData = null;
    let gridData = null;

    const CELL_COLORS = {
        empty: '#1c2128',
        road_h: '#2d333b',
        road_v: '#2d333b',
        intersection: '#3a424d',
        blocked: '#6e3030'
    };

    const LIGHT_COLORS = {
        green: '#3fb950',
        yellow: '#d29922',
        red: '#f85149'
    };

    const VEHICLE_COLOR = '#58a6ff';
    const VEHICLE_STOPPED_COLOR = '#f0883e';

    // ---- Initialization ----

    document.addEventListener('DOMContentLoaded', function () {
        canvas = document.getElementById('traffic-canvas');
        if (canvas) {
            ctx = canvas.getContext('2d');
        }

        setupSimulationPage();
        setupAnalyticsPage();
        setupIntersectionsPage();
    });

    // ---- Simulation Page ----

    function setupSimulationPage() {
        const createForm = document.getElementById('create-sim-form');
        const activeSim = document.getElementById('active-sim');
        const btnStep = document.getElementById('btn-step');
        const btnPlay = document.getElementById('btn-play');
        const btnPause = document.getElementById('btn-pause');
        const btnReset = document.getElementById('btn-reset');
        const heatmapToggle = document.getElementById('show-heatmap');

        if (!createForm) return;

        createForm.addEventListener('submit', function (e) {
            e.preventDefault();
            createSimulation();
        });

        if (activeSim) {
            activeSim.addEventListener('change', function () {
                const simId = parseInt(this.value);
                if (simId) {
                    activeSimId = simId;
                    enableControls(true);
                    loadGrid(simId);
                } else {
                    activeSimId = null;
                    enableControls(false);
                }
            });
        }

        if (btnStep) btnStep.addEventListener('click', stepSimulation);
        if (btnPlay) btnPlay.addEventListener('click', startPlayback);
        if (btnPause) btnPause.addEventListener('click', stopPlayback);
        if (btnReset) btnReset.addEventListener('click', resetSimulation);
        if (heatmapToggle) {
            heatmapToggle.addEventListener('change', function () {
                showHeatmap = this.checked;
                if (lastStepData && gridData) {
                    renderGrid(gridData, lastStepData);
                }
            });
        }

        // Check URL params for pre-selected simulation
        const params = new URLSearchParams(window.location.search);
        const simIdParam = params.get('sim_id');
        if (simIdParam && activeSim) {
            activeSim.value = simIdParam;
            activeSim.dispatchEvent(new Event('change'));
        }
    }

    function enableControls(enabled) {
        const ids = ['btn-step', 'btn-play', 'btn-pause', 'btn-reset'];
        ids.forEach(function (id) {
            const el = document.getElementById(id);
            if (el) el.disabled = !enabled;
        });
    }

    async function createSimulation() {
        const name = document.getElementById('sim-name').value;
        const preset = document.getElementById('sim-preset').value;
        const width = parseInt(document.getElementById('sim-width').value);
        const height = parseInt(document.getElementById('sim-height').value);
        const vehicles = parseInt(document.getElementById('sim-vehicles').value);
        const speed = parseInt(document.getElementById('sim-speed').value);
        const braking = parseFloat(document.getElementById('sim-braking').value);

        const body = {
            name: name,
            grid_width: width,
            grid_height: height,
            vehicle_count: vehicles,
            max_speed: speed,
            braking_probability: braking
        };
        if (preset) body.preset = preset;

        try {
            const resp = await fetch('/api/simulations', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body)
            });
            if (resp.ok) {
                const sim = await resp.json();
                const sel = document.getElementById('active-sim');
                if (sel) {
                    const opt = document.createElement('option');
                    opt.value = sim.id;
                    opt.textContent = sim.name + ' (#' + sim.id + ')';
                    sel.appendChild(opt);
                    sel.value = sim.id;
                    sel.dispatchEvent(new Event('change'));
                }
            }
        } catch (err) {
            console.error('Failed to create simulation:', err);
        }
    }

    async function loadGrid(simId) {
        try {
            const resp = await fetch('/api/simulations/' + simId + '/grid');
            if (resp.ok) {
                gridData = await resp.json();
                renderGrid(gridData, null);
            }
        } catch (err) {
            console.error('Failed to load grid:', err);
        }
    }

    async function stepSimulation() {
        if (!activeSimId) return;
        const steps = parseInt(document.getElementById('step-count').value) || 1;

        try {
            const resp = await fetch('/api/simulations/' + activeSimId + '/step?steps=' + steps, {
                method: 'POST'
            });
            if (resp.ok) {
                lastStepData = await resp.json();
                updateStepInfo(lastStepData);
                if (gridData) {
                    renderGrid(gridData, lastStepData);
                }
            }
        } catch (err) {
            console.error('Failed to step simulation:', err);
        }
    }

    function startPlayback() {
        if (playInterval) return;
        const speed = parseInt(document.getElementById('play-speed').value) || 200;
        playInterval = setInterval(stepSimulation, speed);
    }

    function stopPlayback() {
        if (playInterval) {
            clearInterval(playInterval);
            playInterval = null;
        }
    }

    async function resetSimulation() {
        if (!activeSimId) return;
        stopPlayback();
        try {
            await fetch('/api/simulations/' + activeSimId + '/reset', { method: 'POST' });
            lastStepData = null;
            await loadGrid(activeSimId);
            updateStepInfo(null);
        } catch (err) {
            console.error('Failed to reset simulation:', err);
        }
    }

    function updateStepInfo(data) {
        const infoPanel = document.getElementById('step-info');
        if (!infoPanel) return;

        if (!data) {
            infoPanel.style.display = 'none';
            return;
        }

        infoPanel.style.display = 'block';
        setText('info-step', data.step);
        setText('info-vehicles', data.vehicle_count);
        setText('info-speed', data.average_speed);
        setText('info-congestion', data.max_congestion);
    }

    // ---- Grid Rendering ----

    function renderGrid(grid, stepData) {
        if (!canvas || !ctx || !grid) return;

        const width = grid.width;
        const height = grid.height;
        const cells = grid.grid;

        const cellSize = Math.min(
            Math.floor((canvas.width - 20) / width),
            Math.floor((canvas.height - 20) / height),
            20
        );
        const offsetX = Math.floor((canvas.width - width * cellSize) / 2);
        const offsetY = Math.floor((canvas.height - height * cellSize) / 2);

        ctx.fillStyle = '#0d1117';
        ctx.fillRect(0, 0, canvas.width, canvas.height);

        // Draw cells
        for (let r = 0; r < height; r++) {
            for (let c = 0; c < width; c++) {
                const cell = cells[r][c];
                const x = offsetX + c * cellSize;
                const y = offsetY + r * cellSize;

                ctx.fillStyle = CELL_COLORS[cell.type] || CELL_COLORS.empty;
                ctx.fillRect(x, y, cellSize - 1, cellSize - 1);

                // Road markings
                if (cell.type === 'road_h') {
                    ctx.fillStyle = '#444c56';
                    ctx.fillRect(x, y + Math.floor(cellSize / 2), cellSize - 1, 1);
                } else if (cell.type === 'road_v') {
                    ctx.fillStyle = '#444c56';
                    ctx.fillRect(x + Math.floor(cellSize / 2), y, 1, cellSize - 1);
                }
            }
        }

        // Draw heatmap overlay
        if (showHeatmap && stepData && stepData.heatmap) {
            drawHeatmap(stepData.heatmap, width, height, cellSize, offsetX, offsetY);
        }

        // Draw traffic lights
        if (stepData && stepData.traffic_lights) {
            for (const tl of stepData.traffic_lights) {
                const x = offsetX + tl.x * cellSize;
                const y = offsetY + tl.y * cellSize;
                const lightColor = LIGHT_COLORS[tl.state] || LIGHT_COLORS.red;

                ctx.fillStyle = lightColor;
                const dotSize = Math.max(3, cellSize / 4);
                let dx = 0, dy = 0;
                if (tl.direction === 'north') dy = -dotSize;
                else if (tl.direction === 'south') dy = cellSize - 1;
                else if (tl.direction === 'east') dx = cellSize - 1;
                else if (tl.direction === 'west') dx = -dotSize;

                ctx.beginPath();
                ctx.arc(
                    x + cellSize / 2 + dx,
                    y + cellSize / 2 + dy,
                    dotSize / 2,
                    0,
                    Math.PI * 2
                );
                ctx.fill();
            }
        }

        // Draw vehicles
        if (stepData && stepData.vehicles) {
            for (const v of stepData.vehicles) {
                const x = offsetX + v.x * cellSize;
                const y = offsetY + v.y * cellSize;
                const pad = Math.max(2, cellSize / 5);

                ctx.fillStyle = v.speed === 0 ? VEHICLE_STOPPED_COLOR : VEHICLE_COLOR;
                ctx.fillRect(x + pad, y + pad, cellSize - pad * 2 - 1, cellSize - pad * 2 - 1);
            }
        }
    }

    function drawHeatmap(heatmap, width, height, cellSize, offsetX, offsetY) {
        for (let r = 0; r < height; r++) {
            for (let c = 0; c < width; c++) {
                const val = heatmap[r] ? (heatmap[r][c] || 0) : 0;
                if (val > 0.05) {
                    const x = offsetX + c * cellSize;
                    const y = offsetY + r * cellSize;

                    // Color gradient: green -> yellow -> red
                    let red, green, blue;
                    if (val < 0.5) {
                        const t = val / 0.5;
                        red = Math.floor(255 * t);
                        green = 255;
                        blue = 0;
                    } else {
                        const t = (val - 0.5) / 0.5;
                        red = 255;
                        green = Math.floor(255 * (1 - t));
                        blue = 0;
                    }

                    ctx.fillStyle = 'rgba(' + red + ',' + green + ',' + blue + ',' + (val * 0.5) + ')';
                    ctx.fillRect(x, y, cellSize - 1, cellSize - 1);
                }
            }
        }
    }

    // ---- Analytics Page ----

    function setupAnalyticsPage() {
        const analyticsSim = document.getElementById('analytics-sim');
        const btnLoad = document.getElementById('btn-load-analytics');
        if (!analyticsSim || !btnLoad) return;

        analyticsSim.addEventListener('change', function () {
            btnLoad.disabled = !this.value;
        });

        btnLoad.addEventListener('click', loadAnalytics);
    }

    async function loadAnalytics() {
        const simId = document.getElementById('analytics-sim').value;
        if (!simId) return;

        try {
            const [analyticsResp, intersectionResp] = await Promise.all([
                fetch('/api/simulations/' + simId + '/analytics'),
                fetch('/api/simulations/' + simId + '/analytics/intersections')
            ]);

            if (analyticsResp.ok) {
                const data = await analyticsResp.json();
                displayAnalytics(data);
            }

            if (intersectionResp.ok) {
                const data = await intersectionResp.json();
                displayIntersectionAnalytics(data);
            }

            document.getElementById('analytics-content').style.display = 'block';
        } catch (err) {
            console.error('Failed to load analytics:', err);
        }
    }

    function displayAnalytics(data) {
        setText('metric-avg-speed', data.average_speed);
        setText('metric-throughput', data.throughput);
        setText('metric-density', data.density);
        setText('metric-congestion', data.congestion_index);
        setText('metric-flow', data.flow_rate);
        setText('metric-moving', data.vehicles_moving + ' / ' + data.vehicles_stopped);

        // Speed distribution bar chart
        const chartEl = document.getElementById('speed-chart');
        if (chartEl && data.speed_distribution) {
            chartEl.innerHTML = '';
            const dist = data.speed_distribution;
            const maxVal = Math.max(...Object.values(dist), 1);

            for (const [speed, count] of Object.entries(dist)) {
                const heightPct = (count / maxVal) * 100;
                const bar = document.createElement('div');
                bar.className = 'bar';
                bar.style.height = heightPct + '%';
                bar.innerHTML = '<span class="bar-value">' + count + '</span><span class="bar-label">v=' + speed + '</span>';
                chartEl.appendChild(bar);
            }
        }

        // Congestion zones
        const zonesEl = document.getElementById('congestion-zones-list');
        if (zonesEl && data.congestion_zones) {
            if (data.congestion_zones.length === 0) {
                zonesEl.innerHTML = '<p class="empty-state">No congestion zones detected</p>';
            } else {
                zonesEl.innerHTML = data.congestion_zones.map(function (z) {
                    return '<span class="zone-pill zone-severity-' + z.severity + '">' +
                        '(' + z.x + ',' + z.y + ') ' + z.severity + ' (' + z.density + ')' +
                        '</span>';
                }).join('');
            }
        }
    }

    function displayIntersectionAnalytics(data) {
        const tbody = document.querySelector('#intersection-analytics-table tbody');
        if (!tbody) return;
        tbody.innerHTML = '';

        for (const isec of data) {
            const row = document.createElement('tr');
            const ns = (isec.light_states.north || '-') + '/' + (isec.light_states.south || '-');
            const ew = (isec.light_states.east || '-') + '/' + (isec.light_states.west || '-');
            row.innerHTML =
                '<td>' + isec.name + '</td>' +
                '<td>(' + isec.x + ', ' + isec.y + ')</td>' +
                '<td>' + isec.nearby_vehicles + '</td>' +
                '<td>' + isec.average_speed + '</td>' +
                '<td><span class="zone-pill zone-severity-' + isec.congestion_level + '">' + isec.congestion_level + '</span></td>' +
                '<td>' + ns + '</td>' +
                '<td>' + ew + '</td>';
            tbody.appendChild(row);
        }
    }

    // ---- Intersections Page ----

    function setupIntersectionsPage() {
        const isecSim = document.getElementById('isec-sim-select');
        const btnLoad = document.getElementById('btn-load-intersections');
        const addForm = document.getElementById('add-intersection-form');
        const lightForm = document.getElementById('light-config-form');

        if (!isecSim || !btnLoad) return;

        isecSim.addEventListener('change', function () {
            btnLoad.disabled = !this.value;
        });

        btnLoad.addEventListener('click', loadIntersections);
        if (addForm) addForm.addEventListener('submit', addIntersection);
        if (lightForm) lightForm.addEventListener('submit', updateLight);
    }

    async function loadIntersections() {
        const simId = document.getElementById('isec-sim-select').value;
        if (!simId) return;
        activeSimId = parseInt(simId);

        try {
            const resp = await fetch('/api/simulations/' + simId + '/intersections');
            if (resp.ok) {
                const data = await resp.json();
                displayIntersections(data);
                document.getElementById('add-intersection-card').style.display = 'block';
                document.getElementById('intersections-list-card').style.display = 'block';
            }
        } catch (err) {
            console.error('Failed to load intersections:', err);
        }
    }

    function displayIntersections(data) {
        const tbody = document.querySelector('#intersections-table tbody');
        if (!tbody) return;
        tbody.innerHTML = '';

        for (const isec of data) {
            const row = document.createElement('tr');
            const lightsInfo = (isec.traffic_lights || []).map(function (tl) {
                return tl.direction + ':' + tl.state;
            }).join(', ');

            row.innerHTML =
                '<td>' + isec.id + '</td>' +
                '<td>' + isec.name + '</td>' +
                '<td>(' + isec.x + ', ' + isec.y + ')</td>' +
                '<td>' + lightsInfo + '</td>' +
                '<td>' + (isec.traffic_lights || []).map(function (tl) {
                    return '<button class="btn btn-sm" onclick="window.configureLight(' + tl.id + ',' + tl.green_duration + ',' + tl.yellow_duration + ',' + tl.red_duration + ')">Edit ' + tl.direction + '</button>';
                }).join(' ') + '</td>';
            tbody.appendChild(row);
        }
    }

    window.configureLight = function (lightId, green, yellow, red) {
        document.getElementById('config-light-id').value = lightId;
        document.getElementById('config-green').value = green;
        document.getElementById('config-yellow').value = yellow;
        document.getElementById('config-red').value = red;
        document.getElementById('light-config-card').style.display = 'block';
    };

    async function addIntersection(e) {
        e.preventDefault();
        if (!activeSimId) return;

        const body = {
            name: document.getElementById('isec-name').value,
            x: parseInt(document.getElementById('isec-x').value),
            y: parseInt(document.getElementById('isec-y').value),
            green_duration: parseInt(document.getElementById('isec-green').value),
            yellow_duration: parseInt(document.getElementById('isec-yellow').value),
            red_duration: parseInt(document.getElementById('isec-red').value)
        };

        try {
            const resp = await fetch('/api/simulations/' + activeSimId + '/intersections', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body)
            });
            if (resp.ok) {
                loadIntersections();
            }
        } catch (err) {
            console.error('Failed to add intersection:', err);
        }
    }

    async function updateLight(e) {
        e.preventDefault();
        const lightId = document.getElementById('config-light-id').value;
        if (!lightId) return;

        const body = {
            green_duration: parseInt(document.getElementById('config-green').value),
            yellow_duration: parseInt(document.getElementById('config-yellow').value),
            red_duration: parseInt(document.getElementById('config-red').value)
        };

        try {
            const resp = await fetch('/api/traffic-lights/' + lightId, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body)
            });
            if (resp.ok) {
                document.getElementById('light-config-card').style.display = 'none';
                loadIntersections();
            }
        } catch (err) {
            console.error('Failed to update traffic light:', err);
        }
    }

    // ---- Utilities ----

    function setText(id, value) {
        const el = document.getElementById(id);
        if (el) el.textContent = value;
    }

})();
