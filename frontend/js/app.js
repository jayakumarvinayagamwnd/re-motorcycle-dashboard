const API_BASE = `http://${window.location.hostname}:8000/api`;
const TELEMETRY_API = `${API_BASE}/telemetry/latest`;
const GPS_API = `${API_BASE}/gps/latest`;
const CAMERA_API = `${API_BASE}/camera/status`;
const TRIP_API = `${API_BASE}/trip/current`;

const TELEMETRY_INTERVAL_MS = 1000;
const GPS_INTERVAL_MS = 2000;
const CAMERA_INTERVAL_MS = 2000;
const TRIP_INTERVAL_MS = 2000;

document.addEventListener("DOMContentLoaded", () => {
  // Start separate polling loop per endpoint so slow endpoints don't block others
  startPolling("telemetry", TELEMETRY_API, TELEMETRY_INTERVAL_MS, applyTelemetry);
  startPolling("gps", GPS_API, GPS_INTERVAL_MS, applyGps);
  startPolling("camera", CAMERA_API, CAMERA_INTERVAL_MS, applyCamera);
  startPolling("trip", TRIP_API, TRIP_INTERVAL_MS, applyTrip);
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
}

function applyCamera(data) {
  renderCameraStatus(data.is_streaming, 1, data.source, CAMERA_1_STREAM_URL);
  renderCameraStatus(data.is_streaming, 2, data.source, CAMERA_2_STREAM_URL);
}

function applyTrip(data) {
  renderTrip(data.distance_km, data.duration_min);
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