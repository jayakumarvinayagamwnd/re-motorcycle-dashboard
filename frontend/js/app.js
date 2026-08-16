const API_BASE = `http://${window.location.hostname}:8000/api`;
const TELEMETRY_API = `${API_BASE}/telemetry/latest`;
const GPS_API = `${API_BASE}/gps/latest`;
const CAMERA_API = `${API_BASE}/camera/status`;
const TRIP_API = `${API_BASE}/trip/current`;
const TRIP_HISTORY_API = `${API_BASE}/trip/history`;

const TELEMETRY_INTERVAL_MS = 1000;
const GPS_INTERVAL_MS = 2000;
const CAMERA_INTERVAL_MS = 2000;
const TRIP_INTERVAL_MS = 2000;
const TRIP_HISTORY_INTERVAL_MS = 10000;

document.addEventListener("DOMContentLoaded", () => {
  initialiseCameraSettings();
  initialiseThemeSettings();
  // Start separate polling loop per endpoint so slow endpoints don't block others
  startPolling("telemetry", TELEMETRY_API, TELEMETRY_INTERVAL_MS, applyTelemetry);
  startPolling("gps", GPS_API, GPS_INTERVAL_MS, applyGps);
  startPolling("camera", CAMERA_API, CAMERA_INTERVAL_MS, applyCamera);
  startPolling("trip", TRIP_API, TRIP_INTERVAL_MS, applyTrip);
  startPolling("trip-history", TRIP_HISTORY_API, TRIP_HISTORY_INTERVAL_MS, applyTripHistory);
});

function applyTelemetry(data) {
  renderSpeedometer(data.speed_kmh);

  const rpmNode = document.getElementById("rpm-value");
  if (rpmNode) {
    rpmNode.textContent = String(Math.max(0, Math.round(data.engine_rpm)));
  }

  const fuelNode = document.getElementById("fuel-value");
  const batteryLevel = document.getElementById("batteryLevel");
  if (fuelNode) {
    const fuel = Math.max(0, Math.min(100, Math.round(data.fuel_percent)));
    fuelNode.textContent = `${fuel}%`;
    if (batteryLevel) {
      batteryLevel.style.width = `${fuel}%`;
    }
  }
}

function applyGps(data) {
  const gpsNode = document.getElementById("gps-value");
  const coordsNode = document.getElementById("gpsCoordinates");
  if (gpsNode) {
    gpsNode.textContent = "Connected";
  }
  if (coordsNode) {
    coordsNode.textContent = `${data.lat.toFixed(4)}, ${data.lon.toFixed(4)}`;
  }
  updateLiveMap(data.lat, data.lon);
}

function updateLiveMap(lat, lon) {
  const map = document.getElementById("live-map");
  const status = document.getElementById("map-location-status");
  if (status) status.textContent = `Live location: ${lat.toFixed(4)}, ${lon.toFixed(4)}`;
  if (!map) return;
  const newSrc = `https://www.google.com/maps?q=${lat},${lon}&z=15&output=embed`;
  // Only update the iframe src when the coordinates actually change
  if (map.src !== newSrc) {
    map.src = newSrc;
  }
}

function applyCamera(data) {
  const cam1 = data.camera_1 || {};
  const cam2 = data.camera_2 || {};
  renderCameraStatus(cam1.is_streaming, 1, cam1.source, CAMERA_1_STREAM_URL);
  renderCameraStatus(cam2.is_streaming, 2, cam2.source, CAMERA_2_STREAM_URL);
  updateCameraSettingStatus(1, cam1.is_streaming, cam1.source);
  updateCameraSettingStatus(2, cam2.is_streaming, cam2.source);
}

function initialiseCameraSettings() {
  const systemAddress = document.getElementById("system-address");
  if (systemAddress) {
    systemAddress.textContent = `Dashboard host: ${window.location.hostname || "localhost"}`;
  }
}

function updateCameraSettingStatus(cameraId, isStreaming, source) {
  const status = document.getElementById(`settings-camera-${cameraId}-status`);
  const address = document.getElementById(`settings-camera-${cameraId}-address`);

  if (address) {
    let host = "—";
    if (source && source !== "none") {
      try {
        host = new URL(source).hostname;
      } catch {
        host = source;
      }
    }
    address.textContent = `Stream IP: ${host}`;
  }

  if (status) {
    status.innerHTML = `<span class="status-dot"></span>${isStreaming ? "Online" : "Offline"}`;
    status.style.color = isStreaming ? "#00c49a" : "rgba(255,255,255,0.48)";
  }
}

function initialiseThemeSettings() {
  const savedTheme = localStorage.getItem("dashboard-theme") || "emerald";
  applyTheme(savedTheme);
  document.querySelectorAll(".theme-option").forEach((option) => {
    option.addEventListener("click", () => {
      const theme = option.dataset.theme;
      localStorage.setItem("dashboard-theme", theme);
      applyTheme(theme);
    });
  });
}

function applyTheme(theme) {
  const themeName = theme.charAt(0).toUpperCase() + theme.slice(1);
  document.body.dataset.theme = theme;
  document.querySelectorAll(".theme-option").forEach((option) => {
    const active = option.dataset.theme === theme;
    option.classList.toggle("active", active);
    option.setAttribute("aria-checked", String(active));
  });
  const label = document.getElementById("active-theme-label");
  if (label) label.textContent = themeName;
}

function applyTrip(data) {
  renderTrip(data.distance_km, data.duration_min);
}

function applyTripHistory(data) {
  renderTripHistory(data);
}

async function fetchJson(url) {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`HTTP ${response.status} for ${url}`);
  }
  return response.json();
}

function startPolling(name, url, intervalMs, apply) {
  const poll = async () => {
    try {
      const data = await fetchJson(url);
      apply(data);
    } catch (error) {
      console.error(`Failed to fetch ${name}:`, error);
    }
  };

  poll();
  window.setInterval(poll, intervalMs);
}
