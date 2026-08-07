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
  startClock();
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
  if (fuelNode) {
    const fuel = Math.max(0, Math.min(100, Math.round(data.fuel_percent)));
    fuelNode.textContent = `${fuel}%`;
  }
}

function applyGps(data) {
  const gpsNode = document.getElementById("gps-value");
  const coordsNode = document.getElementById("gps-coords");
  if (gpsNode) {
    gpsNode.textContent = "LOCK";
  }
  if (coordsNode) {
    coordsNode.textContent = `${data.lat.toFixed(4)}, ${data.lon.toFixed(4)}`;
  }
}

function applyCamera(data) {
  renderCameraStatus(data.is_streaming, "camera-1", data.source, CAMERA_1_STREAM_URL);
  renderCameraStatus(data.is_streaming, "camera-2", data.source, CAMERA_2_STREAM_URL);
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

function startClock() {
  const clockNode = document.getElementById("clock-value");
  if (!clockNode) {
    return;
  }

  const updateClock = () => {
    const now = new Date();
    clockNode.textContent = now.toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
      hour12: true,
    });
  };

  updateClock();
  window.setInterval(updateClock, 1000);
}