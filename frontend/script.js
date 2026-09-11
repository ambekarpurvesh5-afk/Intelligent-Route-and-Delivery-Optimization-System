/**
 * Intelligent Route & Delivery Optimization System
 * Interactive Frontend Controller & Leaflet Map Engine
 */

// Global Application State
const state = {
  network: null,
  orders: [],
  vehicles: [],
  optimization: null,
  selectedVehicleId: null,
  networkLayerGroup: null,
  routeLayerGroup: null,
  markerLayerGroup: null,
  vehicleMarkerMap: {},
  simulation: {
    isPlaying: false,
    progress: 0.0,
    speed: 1,
    durationMs: 18000, // base simulation duration
    lastTimestamp: null,
    animFrameId: null
  },
  showEdges: true,
  showLabels: true
};

let map = null;

// Initialize when DOM is ready
document.addEventListener("DOMContentLoaded", () => {
  initMap();
  initEventListeners();
  fetchInitialData();
});

/* =========================================================
   1. MAP INITIALIZATION & TILE LAYERS
   ========================================================= */
function initMap() {
  // Center over Mumbai [19.0178, 72.8478]
  map = L.map("map", {
    center: [19.0178, 72.8478],
    zoom: 12,
    zoomControl: false
  });

  // Reposition zoom control to top-right
  L.control.zoom({ position: "topright" }).addTo(map);

  // CartoDB Dark Matter Base Tiles (Futuristic, High Contrast)
  L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>',
    subdomains: "abcd",
    maxZoom: 19
  }).addTo(map);

  // Layer groups for clean management
  state.networkLayerGroup = L.layerGroup().addTo(map);
  state.routeLayerGroup = L.layerGroup().addTo(map);
  state.markerLayerGroup = L.layerGroup().addTo(map);
}

/* =========================================================
   2. API DATA FETCHING & RENDERING
   ========================================================= */
async function fetchInitialData() {
  try {
    updateSystemStatus("Connecting to Optimization Server...", "connecting");

    const [networkRes, ordersRes, vehiclesRes] = await Promise.all([
      fetch(`${CONFIG.API_BASE_URL}/api/network`),
      fetch(`${CONFIG.API_BASE_URL}/api/orders`),
      fetch(`${CONFIG.API_BASE_URL}/api/vehicles`)
    ]);

    state.network = await networkRes.json();
    state.orders = await ordersRes.json();
    state.vehicles = await vehiclesRes.json();

    renderNetworkOnMap();
    renderOrdersList();
    renderVehiclesList();
    populateSelectDropdowns();

    updateSystemStatus(`Engine Ready • ${state.network.nodes.length} Hubs Online`, "online");

    // Automatically trigger initial optimization run for immediate visual impact
    runOptimization();
  } catch (err) {
    console.error("Failed to load initial data:", err);
    updateSystemStatus("Offline / Server Error", "error");
  }
}

function updateSystemStatus(text, type = "online") {
  const statusEl = document.getElementById("system-status-text");
  if (statusEl) {
    statusEl.textContent = text;
  }
}

function populateSelectDropdowns() {
  if (!state.network) return;

  const nodes = state.network.nodes;
  const populate = (elemId, filterDepot = false) => {
    const select = document.getElementById(elemId);
    if (!select) return;
    select.innerHTML = "";
    nodes.forEach(node => {
      if (filterDepot && node.type !== "depot") return;
      const opt = document.createElement("option");
      opt.value = node.id;
      opt.textContent = `${node.name} (${node.type.toUpperCase()})`;
      select.appendChild(opt);
    });
  };

  populate("lab-start-node");
  populate("lab-goal-node");
  populate("new-order-pickup");
  populate("new-order-dropoff");
  populate("new-veh-base", true);

  // Default selections for lab
  const startSelect = document.getElementById("lab-start-node");
  const goalSelect = document.getElementById("lab-goal-node");
  if (startSelect && goalSelect && nodes.length > 5) {
    startSelect.value = "DEPOT_BKC";
    goalSelect.value = "COLABA";
  }
}

/* =========================================================
   3. ROAD NETWORK & NODE VISUALIZATION
   ========================================================= */
function renderNetworkOnMap() {
  if (!state.network) return;

  state.networkLayerGroup.clearLayers();
  state.markerLayerGroup.clearLayers();

  const nodeMap = {};
  state.network.nodes.forEach(n => { nodeMap[n.id] = n; });

  // 1. Draw Road Network Edges
  if (state.showEdges) {
    state.network.edges.forEach(edge => {
      const src = nodeMap[edge.source];
      const tgt = nodeMap[edge.target];
      if (!src || !tgt) return;

      const isCongested = edge.traffic_factor > 1.25;
      const edgeColor = isCongested ? "#ef4444" : "#0284c7";
      const edgeWeight = isCongested ? 2.5 : 1.5;
      const edgeOpacity = isCongested ? 0.65 : 0.35;

      const line = L.polyline([[src.lat, src.lng], [tgt.lat, tgt.lng]], {
        color: edgeColor,
        weight: edgeWeight,
        opacity: edgeOpacity,
        dashArray: isCongested ? "4, 6" : null
      });

      line.bindTooltip(`
        <strong>${edge.road_name || 'Road Link'}</strong><br/>
        Distance: ${edge.distance_km} km | Speed: ${edge.speed_limit_kmh} km/h<br/>
        Traffic Multiplier: ${edge.traffic_factor}x (${edge.travel_time_mins} mins)
      `);

      state.networkLayerGroup.addLayer(line);
    });
  }

  // 2. Draw Network Nodes
  state.network.nodes.forEach(node => {
    const isDepot = node.type === "depot";
    const markerHtml = isDepot 
      ? `<div class="depot-marker-pin" title="${node.name}"><i class="fa-solid fa-warehouse"></i></div>`
      : `<div class="customer-marker-pin" title="${node.name}"></div>`;

    const customIcon = L.divIcon({
      className: "custom-node-icon",
      html: markerHtml,
      iconSize: isDepot ? [28, 28] : [16, 16],
      iconAnchor: isDepot ? [14, 14] : [8, 8]
    });

    const marker = L.marker([node.lat, node.lng], { icon: customIcon });

    marker.bindPopup(`
      <div class="map-popup-card">
        <h4>${node.name}</h4>
        <p>${node.description || 'Junction Node'}</p>
        <div style="font-size: 11px; color: #94a3b8;">
          Type: <strong>${node.type.toUpperCase()}</strong> | ID: <code>${node.id}</code>
        </div>
        <div style="margin-top: 8px; display: flex; gap: 6px;">
          <button onclick="setLabStart('${node.id}')" class="btn btn-xs btn-outline">Set Start</button>
          <button onclick="setLabGoal('${node.id}')" class="btn btn-xs btn-outline">Set Goal</button>
        </div>
      </div>
    `);

    if (state.showLabels && isDepot) {
      marker.bindTooltip(node.name, { permanent: true, direction: "top", offset: [0, -12], className: "depot-tooltip" });
    }

    state.markerLayerGroup.addLayer(marker);
  });
}

// Helpers for popup button actions
window.setLabStart = function(nodeId) {
  const sel = document.getElementById("lab-start-node");
  if (sel) sel.value = nodeId;
  switchTab("tab-lab");
};

window.setLabGoal = function(nodeId) {
  const sel = document.getElementById("lab-goal-node");
  if (sel) sel.value = nodeId;
  switchTab("tab-lab");
};

/* =========================================================
   4. OPTIMIZATION & ROUTE RENDERING
   ========================================================= */
async function runOptimization() {
  try {
    const optBtn = document.getElementById("btn-run-optimization");
    if (optBtn) {
      optBtn.disabled = true;
      optBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Solving VRP...';
    }

    const response = await fetch(`${CONFIG.API_BASE_URL}/api/optimize`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ cost_metric: "time" })
    });

    state.optimization = await response.json();
    renderOptimizationResults(state.optimization);

    // Refresh orders to display vehicle assignments
    const ordersRes = await fetch(`${CONFIG.API_BASE_URL}/api/orders`);
    state.orders = await ordersRes.json();
    renderOrdersList();

    // Restart route simulation
    resetSimulation();
    startSimulation();

  } catch (err) {
    console.error("Optimization failed:", err);
    alert("Optimization request failed. Please ensure the backend server is running.");
  } finally {
    const optBtn = document.getElementById("btn-run-optimization");
    if (optBtn) {
      optBtn.disabled = false;
      optBtn.innerHTML = '<i class="fa-solid fa-bolt"></i> Run Optimization';
    }
  }
}

function renderOptimizationResults(data) {
  const opt = data.optimized;
  const comp = data.comparison;
  const naive = data.naive;

  // Update KPI counters
  animateCounter("kpi-opt-distance", opt.summary.total_distance_km);
  animateCounter("kpi-opt-time", opt.summary.total_time_mins);
  animateCounter("kpi-naive-time", naive.summary.total_time_mins);
  animateCounter("kpi-co2-saved", comp.co2_saved_kg);
  animateCounter("kpi-fuel-saved", comp.fuel_saved_liters);
  animateCounter("kpi-dist-saved-pct", comp.distance_saved_percent);

  document.getElementById("kpi-orders-dispatched").textContent = comp.assigned_orders_count;
  document.getElementById("kpi-orders-total").textContent = state.orders.length;
  document.getElementById("kpi-active-vehicles").textContent = opt.summary.active_vehicles;

  // Render Routes on Map
  renderVehicleRoutes(opt.vehicles);

  // Update vehicle cards with assigned orders & progress
  renderVehiclesList(opt.vehicles);
}

function renderVehicleRoutes(vehicleRoutes) {
  state.routeLayerGroup.clearLayers();
  state.vehicleMarkerMap = {};

  vehicleRoutes.forEach(vRoute => {
    if (vRoute.polyline.length <= 1) return;

    const color = vRoute.vehicle.color || "#00f0ff";

    // Glowing Underlay Polyline
    const glowLine = L.polyline(vRoute.polyline, {
      color: color,
      weight: 8,
      opacity: 0.25,
      lineCap: "round",
      lineJoin: "round"
    });

    // Sharp Core Polyline
    const mainLine = L.polyline(vRoute.polyline, {
      color: color,
      weight: 3.5,
      opacity: 0.9,
      lineCap: "round",
      lineJoin: "round"
    });

    mainLine.bindTooltip(`
      <strong>${vRoute.vehicle.name}</strong><br/>
      Assigned Orders: ${vRoute.orders_handled.length}<br/>
      Route Distance: ${vRoute.total_distance_km} km<br/>
      Transit Time: ${vRoute.total_time_mins} mins
    `);

    state.routeLayerGroup.addLayer(glowLine);
    state.routeLayerGroup.addLayer(mainLine);

    // Create Animated Moving Marker for Vehicle
    const startCoord = vRoute.polyline[0];
    const iconClass = vRoute.vehicle.type === "bike" ? "fa-motorcycle" : "fa-truck";
    const vehIcon = L.divIcon({
      className: "animated-vehicle-marker-wrapper",
      html: `
        <div class="animated-vehicle-marker" style="background: ${color}; color: #000;">
          <i class="fa-solid ${iconClass}"></i>
        </div>
      `,
      iconSize: [30, 30],
      iconAnchor: [15, 15]
    });

    const vMarker = L.marker(startCoord, { icon: vehIcon, zIndexOffset: 1000 });
    vMarker.bindPopup(`
      <div class="map-popup-card">
        <h4>${vRoute.vehicle.name}</h4>
        <p>Type: <strong>${vRoute.vehicle.type.toUpperCase()}</strong></p>
        <p>Payload: <strong>${vRoute.payload_kg} / ${vRoute.vehicle.capacity_kg} kg</strong></p>
        <p>Stops: <strong>${vRoute.stops.length} points</strong></p>
      </div>
    `);

    state.routeLayerGroup.addLayer(vMarker);
    state.vehicleMarkerMap[vRoute.vehicle.id] = {
      marker: vMarker,
      polyline: vRoute.polyline,
      vRoute: vRoute
    };
  });
}

/* =========================================================
   5. SIMULATION ANIMATION ENGINE
   ========================================================= */
function startSimulation() {
  state.simulation.isPlaying = true;
  state.simulation.lastTimestamp = performance.now();
  updatePlayPauseUI();
  requestAnimationFrame(simulationLoop);
}

function pauseSimulation() {
  state.simulation.isPlaying = false;
  updatePlayPauseUI();
  if (state.simulation.animFrameId) {
    cancelAnimationFrame(state.simulation.animFrameId);
    state.simulation.animFrameId = null;
  }
}

function resetSimulation() {
  pauseSimulation();
  state.simulation.progress = 0.0;
  updateSimulationProgressUI(0.0);

  // Reset markers to origin
  Object.values(state.vehicleMarkerMap).forEach(item => {
    if (item.polyline && item.polyline.length > 0) {
      item.marker.setLatLng(item.polyline[0]);
    }
  });

  // Reset order status tags
  state.orders.forEach(o => { o.status = "ASSIGNED"; });
  renderOrdersList();
}

function simulationLoop(timestamp) {
  if (!state.simulation.isPlaying) return;

  const delta = timestamp - (state.simulation.lastTimestamp || timestamp);
  state.simulation.lastTimestamp = timestamp;

  // Advance progress based on duration & speed multiplier
  const progressStep = (delta / state.simulation.durationMs) * state.simulation.speed;
  state.simulation.progress += progressStep;

  if (state.simulation.progress >= 1.0) {
    state.simulation.progress = 1.0;
    state.simulation.isPlaying = false;
    updateSimulationProgressUI(1.0);
    updatePlayPauseUI();
    markAllOrdersDelivered();
    return;
  }

  updateSimulationProgressUI(state.simulation.progress);
  updateVehiclePositions(state.simulation.progress);

  state.simulation.animFrameId = requestAnimationFrame(simulationLoop);
}

function updateSimulationProgressUI(progress) {
  const progressBar = document.getElementById("sim-progress-bar");
  const timeDisplay = document.getElementById("sim-time-display");

  if (progressBar) {
    progressBar.style.width = `${Math.min(100, Math.round(progress * 100))}%`;
  }

  if (timeDisplay) {
    const totalSimMinutes = state.optimization?.optimized?.summary?.total_time_mins || 60;
    const elapsedMinutes = Math.round(totalSimMinutes * progress);
    const hrs = Math.floor(elapsedMinutes / 60).toString().padStart(2, "0");
    const mins = (elapsedMinutes % 60).toString().padStart(2, "0");
    timeDisplay.textContent = `${hrs}:${mins}`;
  }
}

function updateVehiclePositions(progress) {
  Object.entries(state.vehicleMarkerMap).forEach(([vehId, item]) => {
    const coords = item.polyline;
    if (!coords || coords.length < 2) return;

    // Calculate interpolated position along coordinate list
    const totalSegments = coords.length - 1;
    const exactIndex = progress * totalSegments;
    const lowerIdx = Math.floor(exactIndex);
    const upperIdx = Math.min(totalSegments, lowerIdx + 1);
    const segmentT = exactIndex - lowerIdx;

    const p1 = coords[lowerIdx];
    const p2 = coords[upperIdx];

    const currentLat = p1[0] + (p2[0] - p1[0]) * segmentT;
    const currentLng = p1[1] + (p2[1] - p1[1]) * segmentT;

    item.marker.setLatLng([currentLat, currentLng]);
  });

  // Dynamic order status progression based on progress threshold
  if (progress > 0.1 && progress < 0.85) {
    state.orders.forEach(o => {
      if (o.status !== "IN_TRANSIT" && o.status !== "DELIVERED") {
        o.status = "IN_TRANSIT";
      }
    });
    renderOrdersList();
  } else if (progress >= 0.85) {
    markAllOrdersDelivered();
  }
}

function markAllOrdersDelivered() {
  state.orders.forEach(o => { o.status = "DELIVERED"; });
  renderOrdersList();
}

function updatePlayPauseUI() {
  const playBtn = document.getElementById("btn-sim-play");
  const pauseBtn = document.getElementById("btn-sim-pause");
  if (playBtn && pauseBtn) {
    if (state.simulation.isPlaying) {
      playBtn.style.opacity = "0.5";
      pauseBtn.style.opacity = "1";
    } else {
      playBtn.style.opacity = "1";
      pauseBtn.style.opacity = "0.5";
    }
  }
}

/* =========================================================
   6. SIDEBAR LISTS RENDERING (FLEET & ORDERS)
   ========================================================= */
function renderVehiclesList(vehicleRoutes = null) {
  const container = document.getElementById("vehicles-list");
  if (!container) return;
  container.innerHTML = "";

  const routesMap = {};
  if (vehicleRoutes) {
    vehicleRoutes.forEach(vr => { routesMap[vr.vehicle.id] = vr; });
  }

  state.vehicles.forEach(veh => {
    const vRoute = routesMap[veh.id];
    const card = document.createElement("div");
    card.className = "vehicle-card";
    card.id = `veh-card-${veh.id}`;

    const dist = vRoute ? vRoute.total_distance_km : 0;
    const time = vRoute ? vRoute.total_time_mins : 0;
    const load = vRoute ? vRoute.payload_kg : 0;
    const loadPct = Math.round((load / veh.capacity_kg) * 100);

    card.innerHTML = `
      <div class="vehicle-header">
        <div class="vehicle-name-tag">
          <span class="vehicle-color-dot" style="background: ${veh.color}; color: ${veh.color};"></span>
          <span>${veh.name}</span>
        </div>
        <span class="badge" style="background: rgba(255,255,255,0.06); font-size: 10px; color: ${veh.color};">
          ${veh.type.toUpperCase()}
        </span>
      </div>

      <div class="vehicle-stats-row">
        <div class="vehicle-stat-item">
          <span>Distance</span>
          <strong>${dist} km</strong>
        </div>
        <div class="vehicle-stat-item">
          <span>Transit</span>
          <strong>${time} min</strong>
        </div>
        <div class="vehicle-stat-item">
          <span>Deliveries</span>
          <strong>${vRoute ? vRoute.orders_handled.length : 0}</strong>
        </div>
      </div>

      <div class="capacity-bar-wrap">
        <div style="display: flex; justify-content: space-between;">
          <span>Payload Capacity</span>
          <span><strong>${load}</strong> / ${veh.capacity_kg} kg (${loadPct}%)</span>
        </div>
        <div class="capacity-bar-track">
          <div class="capacity-bar-fill" style="width: ${Math.min(100, loadPct)}%; background: ${veh.color};"></div>
        </div>
      </div>

      ${vRoute && vRoute.stops.length > 0 ? `
        <div class="vehicle-stops-accordion">
          ${vRoute.stops.map(s => `
            <div class="stop-item">
              <span class="stop-badge ${s.type}">${s.type}</span>
              <span style="font-weight: 500;">${s.node_id}</span>
              <span style="margin-left: auto; color: #94a3b8; font-size: 10px;">${s.order_id}</span>
            </div>
          `).join('')}
        </div>
      ` : ''}
    `;

    // Click vehicle card to center on its route
    card.addEventListener("click", () => {
      if (vRoute && vRoute.polyline.length > 1) {
        map.fitBounds(L.polyline(vRoute.polyline).getBounds(), { padding: [40, 40] });
      }
    });

    container.appendChild(card);
  });
}

function renderOrdersList() {
  const container = document.getElementById("orders-list");
  const countBadge = document.getElementById("orders-count-tab");
  if (!container) return;

  const priorityFilter = document.getElementById("order-priority-filter")?.value || "ALL";
  const statusFilter = document.getElementById("order-status-filter")?.value || "ALL";

  const filtered = state.orders.filter(o => {
    const matchesPriority = priorityFilter === "ALL" || o.priority === priorityFilter;
    const matchesStatus = statusFilter === "ALL" || (o.status || "PENDING") === statusFilter;
    return matchesPriority && matchesStatus;
  });

  if (countBadge) {
    countBadge.textContent = state.orders.length;
  }

  container.innerHTML = "";

  if (filtered.length === 0) {
    container.innerHTML = `<div style="text-align: center; color: #64748b; padding: 20px;">No matching orders found.</div>`;
    return;
  }

  filtered.forEach(order => {
    const card = document.createElement("div");
    card.className = "order-card";

    const status = order.status || "PENDING";

    card.innerHTML = `
      <div class="order-card-header">
        <span class="order-id-pill">${order.id}</span>
        <span class="order-priority-badge priority-${order.priority}">${order.priority}</span>
      </div>

      <div style="font-weight: 600; font-size: 12px; margin-bottom: 6px; color: #fff;">
        ${order.customer}
      </div>

      <div class="order-route-endpoints">
        <div class="order-endpoint">
          <i class="fa-solid fa-arrow-up-from-bracket" style="color: #00f0ff;"></i>
          <span>Pickup: <strong>${order.pickup}</strong></span>
        </div>
        <div class="order-endpoint">
          <i class="fa-solid fa-location-dot" style="color: #f43f5e;"></i>
          <span>Dropoff: <strong>${order.dropoff}</strong></span>
        </div>
      </div>

      <div class="order-meta-footer">
        <span><i class="fa-solid fa-weight-hanging"></i> ${order.weight_kg} kg</span>
        <span><i class="fa-solid fa-clock"></i> ${order.deadline_mins} min</span>
        <span class="order-status-tag status-${status}">${status.replace('_', ' ')}</span>
      </div>
    `;

    container.appendChild(card);
  });
}

/* =========================================================
   7. PATHFINDING BENCHMARK (DIJKSTRA VS A*)
   ========================================================= */
async function runPathfindBenchmark(e) {
  e.preventDefault();

  const start = document.getElementById("lab-start-node").value;
  const goal = document.getElementById("lab-goal-node").value;
  const metric = document.querySelector('input[name="lab-metric"]:checked')?.value || "time";

  if (start === goal) {
    alert("Please choose distinct Start and Goal junctions.");
    return;
  }

  try {
    const res = await fetch(`${CONFIG.API_BASE_URL}/api/pathfind`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ start, goal, cost_metric: metric })
    });

    const data = await res.json();
    displayBenchmarkResults(data);
  } catch (err) {
    console.error("Pathfind benchmark error:", err);
  }
}

function displayBenchmarkResults(data) {
  const labResults = document.getElementById("lab-results");
  if (!labResults) return;

  labResults.style.display = "flex";

  const dijk = data.dijkstra;
  const astar = data.astar;
  const comp = data.comparison;

  document.getElementById("res-dijk-nodes").textContent = `${dijk.nodes_explored} junctions`;
  document.getElementById("res-dijk-cost").textContent = `${dijk.distance_km} km (${dijk.time_mins} min)`;
  document.getElementById("res-dijk-time").textContent = `${dijk.execution_time_ms} ms`;

  document.getElementById("res-astar-nodes").textContent = `${astar.nodes_explored} junctions`;
  document.getElementById("res-astar-cost").textContent = `${astar.distance_km} km (${astar.time_mins} min)`;
  document.getElementById("res-astar-time").textContent = `${astar.execution_time_ms} ms`;

  document.getElementById("res-nodes-saved-pct").textContent = comp.nodes_saved_percent;

  // Draw benchmark path prominently on map
  drawBenchmarkPath(astar.path);
}

function drawBenchmarkPath(nodeIds) {
  if (!state.network || !nodeIds || nodeIds.length < 2) return;

  state.routeLayerGroup.clearLayers();
  const nodeMap = {};
  state.network.nodes.forEach(n => { nodeMap[n.id] = n; });

  const coords = nodeIds.map(nid => [nodeMap[nid].lat, nodeMap[nid].lng]);

  const pathLine = L.polyline(coords, {
    color: "#00f0ff",
    weight: 5,
    dashArray: "8, 8"
  }).addTo(state.routeLayerGroup);

  map.fitBounds(pathLine.getBounds(), { padding: [60, 60] });
}

/* =========================================================
   8. EVENT LISTENERS & MODALS
   ========================================================= */
function initEventListeners() {
  // Tab Switching
  document.querySelectorAll(".tab-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      const tabId = btn.getAttribute("data-tab");
      switchTab(tabId);
    });
  });

  // Action Buttons
  document.getElementById("btn-run-optimization")?.addEventListener("click", runOptimization);
  document.getElementById("btn-reset-data")?.addEventListener("click", resetToDefaults);

  // Simulation Controls
  document.getElementById("btn-sim-play")?.addEventListener("click", startSimulation);
  document.getElementById("btn-sim-pause")?.addEventListener("click", pauseSimulation);
  document.getElementById("btn-sim-reset")?.addEventListener("click", resetSimulation);

  document.querySelectorAll(".speed-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".speed-btn").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      state.simulation.speed = parseFloat(btn.getAttribute("data-speed") || "1");
    });
  });

  // Pathfinding Benchmark Form
  document.getElementById("pathfind-form")?.addEventListener("submit", runPathfindBenchmark);

  // Filter Selects
  document.getElementById("order-priority-filter")?.addEventListener("change", renderOrdersList);
  document.getElementById("order-status-filter")?.addEventListener("change", renderOrdersList);

  // Map Layer Toggles
  document.getElementById("toggle-network-edges")?.addEventListener("click", (e) => {
    state.showEdges = !state.showEdges;
    e.currentTarget.classList.toggle("active", state.showEdges);
    renderNetworkOnMap();
  });

  document.getElementById("toggle-labels")?.addEventListener("click", (e) => {
    state.showLabels = !state.showLabels;
    e.currentTarget.classList.toggle("active", state.showLabels);
    renderNetworkOnMap();
  });

  // Modal Triggers
  document.getElementById("btn-open-viva-modal")?.addEventListener("click", () => openModal("modal-viva"));
  document.getElementById("btn-open-add-order")?.addEventListener("click", () => openModal("modal-add-order"));
  document.getElementById("btn-add-vehicle")?.addEventListener("click", () => openModal("modal-add-vehicle"));

  // Modal Closers
  document.querySelectorAll("[data-close]").forEach(btn => {
    btn.addEventListener("click", () => {
      const targetModalId = btn.getAttribute("data-close");
      closeModal(targetModalId);
    });
  });

  // Close modals on backdrop click
  document.querySelectorAll(".modal-backdrop").forEach(backdrop => {
    backdrop.addEventListener("click", (e) => {
      if (e.target === backdrop) {
        backdrop.classList.remove("open");
      }
    });
  });

  // Forms Submission
  document.getElementById("form-add-order")?.addEventListener("submit", handleAddOrder);
  document.getElementById("form-add-vehicle")?.addEventListener("submit", handleAddVehicle);
}

function switchTab(tabId) {
  document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
  document.querySelectorAll(".tab-pane").forEach(p => p.classList.remove("active"));

  document.querySelector(`[data-tab="${tabId}"]`)?.classList.add("active");
  document.getElementById(tabId)?.classList.add("active");
}

function openModal(id) {
  document.getElementById(id)?.classList.add("open");
}

function closeModal(id) {
  document.getElementById(id)?.classList.remove("open");
}

async function handleAddOrder(e) {
  e.preventDefault();

  const customer = document.getElementById("new-order-customer").value;
  const pickup = document.getElementById("new-order-pickup").value;
  const dropoff = document.getElementById("new-order-dropoff").value;
  const weight_kg = parseFloat(document.getElementById("new-order-weight").value);
  const priority = document.getElementById("new-order-priority").value;
  const deadline_mins = parseInt(document.getElementById("new-order-deadline").value);

  if (pickup === dropoff) {
    alert("Pickup and Dropoff locations must be different!");
    return;
  }

  try {
    const res = await fetch(`${CONFIG.API_BASE_URL}/api/orders`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ customer, pickup, dropoff, weight_kg, priority, deadline_mins })
    });

    if (res.ok) {
      const newOrder = await res.json();
      state.orders.push(newOrder);
      closeModal("modal-add-order");
      document.getElementById("form-add-order").reset();
      renderOrdersList();
      runOptimization(); // Re-run optimization with new order
    } else {
      const err = await res.json();
      alert(`Error: ${err.error || 'Failed to create order'}`);
    }
  } catch (err) {
    console.error("Failed to add order:", err);
  }
}

async function handleAddVehicle(e) {
  e.preventDefault();

  const name = document.getElementById("new-veh-name").value;
  const type = document.getElementById("new-veh-type").value;
  const base_node = document.getElementById("new-veh-base").value;
  const capacity_kg = parseFloat(document.getElementById("new-veh-capacity").value);
  const speed_kmh = parseFloat(document.getElementById("new-veh-speed").value);
  const color = document.getElementById("new-veh-color").value;

  try {
    const res = await fetch(`${CONFIG.API_BASE_URL}/api/vehicles`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, type, base_node, capacity_kg, speed_kmh, color })
    });

    if (res.ok) {
      const newVeh = await res.json();
      state.vehicles.push(newVeh);
      closeModal("modal-add-vehicle");
      document.getElementById("form-add-vehicle").reset();
      renderVehiclesList();
      runOptimization();
    } else {
      const err = await res.json();
      alert(`Error: ${err.error || 'Failed to add vehicle'}`);
    }
  } catch (err) {
    console.error("Failed to add vehicle:", err);
  }
}

async function resetToDefaults() {
  if (!confirm("Reset all orders and vehicle routes back to defaults?")) return;

  try {
    const res = await fetch(`${CONFIG.API_BASE_URL}/api/orders/reset`, { method: "POST" });
    const data = await res.json();
    state.orders = data.orders;
    renderOrdersList();
    runOptimization();
  } catch (err) {
    console.error("Reset failed:", err);
  }
}

function animateCounter(elemId, targetValue, duration = 800) {
  const el = document.getElementById(elemId);
  if (!el) return;

  const target = parseFloat(targetValue);
  if (isNaN(target)) {
    el.textContent = targetValue;
    return;
  }

  const start = parseFloat(el.textContent) || 0;
  const startTime = performance.now();

  function update(time) {
    const elapsed = time - startTime;
    const progress = Math.min(1, elapsed / duration);
    const ease = 1 - Math.pow(1 - progress, 3); // cubic ease-out
    const current = start + (target - start) * ease;

    el.textContent = current.toFixed(1);

    if (progress < 1) {
      requestAnimationFrame(update);
    } else {
      el.textContent = target.toFixed(1);
    }
  }

  requestAnimationFrame(update);
}
