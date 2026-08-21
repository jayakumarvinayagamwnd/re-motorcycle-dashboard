# Motorcycle Dashboard

A full-stack motorcycle dashboard system featuring a **FastAPI backend**, a **static web dashboard frontend**, **ESP32 device firmware placeholders**, and **kiosk deployment** configuration for Raspberry Pi / Linux.

The system handles telemetry (speed, RPM, fuel), GPS location, live MJPEG camera streaming with snapshot capture and 30-second recording, trip tracking/history, a media gallery, and a real-time WebSocket channel.

---

## Features

- **FastAPI backend** exposing REST endpoints for telemetry, GPS, cameras, trips, and a WebSocket channel
- **Live camera streaming** — MJPEG streams are proxied through the backend (avoids CORS / mixed-content issues) via a shared upstream connection with single-slot per camera
- **Snapshot capture & video recording** — Capture JPEGs from live feeds (saved to `data/capture/`) or record 30-second MP4 clips via FFmpeg (saved to `data/recordings/`)
- **Media gallery** — Browse captured images and recorded videos with a lightbox overlay
- **Static frontend dashboard** — Single-page UI with speedometer, RPM, fuel/battery, GPS coordinates, current trip, and nine smart cards
- **Multiple views** — Home, Gallery, Live Google Map, Trip History, Settings (camera status + theme picker)
- **Theme system** — 6 selectable themes (Emerald, Ocean, Violet, Sunset, Rose, Slate), persisted in `localStorage`
- **WebSocket support** — `/ws/dashboard` echo channel, used for real-time push
- **Kiosk deployment** — systemd unit + Chromium kiosk autostart files for dedicated display use
- **Dev scripts** — start/stop API and dashboard with PID/log management

---

## Project Structure

```text
motorcycle-dashboard/
├── backend/                  # FastAPI backend
│   ├── app/
│   │   ├── api/              # REST routers (telemetry, gps, camera, trip)
│   │   ├── communication/    # MQTT & Serial client stubs (future integration)
│   │   ├── config/          # Pydantic-settings (env-driven)
│   │   ├── database.py      # SQLite connection + schema init + health check
│   │   ├── models/          # Pydantic request/response models
│   │   ├── services/        # Business logic + camera monitor service
│   │   ├── websocket/       # /ws/dashboard WebSocket endpoint
│   │   └── main.py          # App factory + CORS + lifespan
│   ├── requirements.txt      # Python dependencies
│   └── run.py                # uvicorn entry point
├── frontend/
│   ├── index.html            # Single-page dashboard markup
│   ├── css/dashboard.css     # Dashboard styles + theme overrides
│   ├── js/                   # Polling + rendering modules
│   └── assets/               # Icons, backgrounds, SVG placeholders
├── devices/
│   ├── esp32-c6/             # Placeholder — future ESP32-C6 firmware
│   └── esp32-s3-camera/      # Placeholder — future ESP32-S3 camera firmware
├── scripts/                  # Bash helpers for dev/run lifecycle
├── system/
│   ├── chromium-kiosk.desktop    # Kiosk autostart file
│   └── motorcycle-dashboard.service  # Systemd unit file
├── tests/                    # Pytest suite (test_telemetry, test_websocket)
├── data/                     # Runtime data (SQLite db, captures, recordings)
├── .env.example              # Environment variable template
└── .gitignore
```

---

## Backend

### Tech Stack

- **FastAPI** — API framework
- **Uvicorn** — ASGI server
- **pydantic-settings** — environment-driven config
- **httpx** — MJPEG stream proxying and camera health checks
- **FFmpeg** — Video recording encoder (installed externally)

### Configuration

Settings are defined in `backend/app/config/settings.py` and can be overridden via a `.env` file or environment variables:

| Variable                     | Default                    | Description                    |
|------------------------------|---------------------------|--------------------------------|
| `APP_NAME`                   | `Motorcycle Dashboard API` | Application name shown in docs |
| `APP_VERSION`                | `0.1.0`                   | API version                    |
| `CAMERA_1_URL`               | `http://192.168.1.8/camera/stream` | Camera 1 (front) MJPEG URL  |
| `CAMERA_2_URL`               | `http://192.168.1.6/camera/stream` | Camera 2 (rear) MJPEG URL   |
| `DATABASE_PATH`              | `data/motorcycle.db`      | SQLite database file path     |

Copy `.env.example` to `.env` and adjust as needed:

```bash
cp .env.example .env
```

### API Endpoints

| Method | Path                       | Description                                        |
|--------|----------------------------|---------------------------------------------------|
| GET    | `/`                        | Root info                                         |
| GET    | `/api/health`              | Health check (`{"status":"ok"}`)                     |
| GET    | `/healthcheck/db`          | Database health (inserts + verifies a `db_check` row) |
| GET    | `/api/telemetry/latest`    | Latest telemetry (speed, RPM, fuel)                 |
| GET    | `/api/gps/latest`          | Latest GPS coordinates (lat, lon, altitude)          |
| GET    | `/api/camera/status`       | Streaming status for camera 1 & 2                    |
| GET    | `/api/camera/gallery`      | List of saved captures and recordings (newest first) |
| GET    | `/api/camera/gallery/{media_type}/{filename}` | Serve one gallery file (images/videos) |
| GET    | `/api/camera/{id}/stream`  | Proxied MJPEG stream (id = 1 or 2)                   |
| POST   | `/api/camera/{id}/capture` | Save a JPEG snapshot                                  |
| POST   | `/api/camera/{id}/record`  | Record 30 seconds of video                           |
| GET    | `/api/trip/current`        | Current ACTIVE trip (or `{"trip": null}`)            |
| GET    | `/api/trip/startup`        | Startup state (unfinished trip or last completed)    |
| POST   | `/api/trip/start`          | Start a new trip (201 Created, 409 if active)        |
| POST   | `/api/trip/{id}/pause`     | Pause an ACTIVE trip (409 if not ACTIVE)             |
| POST   | `/api/trip/{id}/finish`    | Finish an ACTIVE/PAUSED trip -> COMPLETED            |
| GET    | `/api/trip/history`        | Historic trips                                      |
| WS     | `/ws/dashboard`            | WebSocket echo/event channel                         |

### Camera System

- `services/camera_service.py` manages two cameras with runtime state:
  - A **shared upstream MJPEG connection** per camera — only one connection is opened and all browser/fullscreen/recording consumers receive the same bytes. This avoids competing with each camera's limited simultaneous-connection support.
  - Frame buffering → JPEG frame extraction — incoming chunks are searched for `SOI`/`EOI` markers so snapshots are always complete JPEGs.
  - Connectivity monitoring — background task probes camera availability every 5 seconds (skipped while streams are active).
- The frontend polls `/api/camera/status` every 2s to toggle streams and placeholders.
- `POST /api/camera/{id}/capture` reads the latest frame and saves it to `data/captures/*.jpg`.
- `POST /api/camera/{id}/record` feeds 20 FPS JPEGs to a 30-second FFmpeg `libx264` encode, then saves the MP4 to `data/recordings/`.

### Database

The backend uses a **SQLite** database (`data/motorcycle.db` by default) for trip storage:

- `backend/app/database.py` manages the connection, schema initialization, and health checks.
- The `trips` table is created automatically on startup (or on module import).
- The trip service reads current trip and history data from the database.
- `GET /healthcheck/db` performs a full health check: it opens SQLite, inserts a row into the `db_check` table, selects it back to verify, and returns the health status via the `DBHealthResponse` model:

**Trips table schema:**

```sql
CREATE TABLE trips (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trip_name TEXT NOT NULL,
    status TEXT NOT NULL,
    started_at TEXT NOT NULL,
    ended_at TEXT,
    distance_km REAL NOT NULL DEFAULT 0.0,
    duration_sec INTEGER NOT NULL DEFAULT 0,
    avg_speed_kmh REAL NOT NULL DEFAULT 0.0,
    max_speed_kmh REAL NOT NULL DEFAULT 0.0,
    start_latitude REAL,
    start_longitude REAL,
    end_latitude REAL,
    end_longitude REAL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
```

**`GET /api/trip/current`** returns the most recent ACTIVE trip via the `CurrentTripResponse` model:

**200 OK — Active trip:**

```json
{
  "trip": {
    "id": 10,
    "trip_name": "Morning Commute",
    "status": "ACTIVE",
    "started_at": "2026-08-20T07:30:00+05:30",
    "distance_km": 22.31,
    "duration_sec": 3120,
    "avg_speed_kmh": 25.78,
    "max_speed_kmh": 72.4
  }
}
```

**200 OK — No active trip:**

```json
{
  "trip": null
}
```

**`POST /api/trip/start`** starts a new trip via the `TripStartRequest` / `TripStartResponse` models:

**201 Created:**

```json
{
  "id": 11,
  "trip_name": "Morning Commute",
  "status": "ACTIVE",
  "started_at": "2026-08-20T07:30:00+05:30",
  "distance_km": 0.0,
  "duration_sec": 0,
  "avg_speed_kmh": 0.0,
  "max_speed_kmh": 0.0
}
```

**409 Conflict — Another trip is already active:**

```json
{
  "error": "TRIP_ALREADY_ACTIVE",
  "message": "Trip 10 is already active."
}
```

**`POST /api/trip/{id}/pause`** pauses an ACTIVE trip via the `TripPauseResponse` model:

**200 OK:**

```json
{
  "id": 11,
  "status": "PAUSED",
  "distance_km": 22.31,
  "duration_sec": 3120,
  "avg_speed_kmh": 25.78
}
```

**409 Conflict — Trip is not ACTIVE:**

```json
{
  "error": "TRIP_NOT_ACTIVE",
  "message": "Trip 11 is not active (status: PAUSED)."
}
```

**`POST /api/trip/{id}/finish`** finishes an ACTIVE or PAUSED trip via the `TripFinishResponse` model:

**200 OK:**

```json
{
  "id": 11,
  "trip_name": "Morning Commute",
  "status": "COMPLETED",
  "started_at": "2026-08-20T07:30:00+05:30",
  "ended_at": "2026-08-20T08:25:32+05:30",
  "distance_km": 42.71,
  "duration_sec": 3332,
  "avg_speed_kmh": 46.12,
  "max_speed_kmh": 82.4
}
```

**409 Conflict — Trip is not ACTIVE or PAUSED:**

```json
{
  "error": "TRIP_NOT_FINISHABLE",
  "message": "Trip 11 cannot be finished (status: COMPLETED)."
}
```

**`GET /api/trip/startup`** returns the startup state via the `TripStartupResponse` model:

**200 OK — No unfinished trip (READY):**

```json
{
  "state": "READY",
  "current_trip": null,
  "previous_trip": {
    "id": 9,
    "trip_name": "Evening Ride",
    "status": "COMPLETED",
    "date": "2026-08-19"
  }
}
```

**200 OK — Unfinished trip (CONTINUE_OR_NEW):**

```json
{
  "state": "CONTINUE_OR_NEW",
  "current_trip": {
    "id": 9,
    "trip_name": "Evening Ride",
    "status": "PAUSED",
    "distance_km": 72.42
  }
}
```

**503 Service Unavailable — Database error:**

```json
{
  "status": "unhealthy",
  "database": "sqlite",
  "error": "Database health check failed"
}
```

**200 OK — Healthy:**

```json
{
  "status": "healthy",
  "database": "sqlite",
  "check_date": "2026-08-20T23:30:00+05:30",
  "created_by": "healthcheck"
}
```

**503 Service Unavailable — Unhealthy:**

```json
{
  "status": "unhealthy",
  "database": "sqlite",
  "error": "Database health check failed"
}
```

### WebSocket

`/ws/dashboard` accepts a connection and echoes any received message back as `echo:<message>`. This is a placeholders feed channel — the frontend `websocket.js` provides the connection helper.

### Communication Stubs

`app/communication/mqtt_client.py` and `serial_client.py` are placeholder classes for future MQTT and serial (e.g., UART from the bike's ECU) integration. They currently implement no-ops.

---

## Frontend

The dashboard is a static web app that runs from `frontend/index.html` and talks to the FastAPI backend on port `8000`.

### Views

| View           | Description                                               |
|----------------|-----------------------------------------------------------|
| Home           | Camera feeds + speed, RPM, battery, GPS, trip cards        |
| Gallery        | Saved snapshots and video recordings                      |
| Google Map     | Live-embedded map at the current GPS coordinates           |
| Trip History   | List of past trips from the API                            |
| Settings       | Camera binding info + theme picker (6 themes)              |

The dashboard uses a custom **glassmorphism** dark theme on the Royal Enfield background, with 6 selectable themes persisted in `localStorage`.

### JavaScript Modules

| File            | Responsibility                                            |
|-----------------|-------------------------------------------------------|
| `app.js`        | Polling loops (telemetry/ gps/ camera/ trip/ trip-history) + data application |
| `camera.js`     | Stream URL management, capture/record/fullscreen/status rendering  |
| `gallery.js`    | Loads and renders the images/videos gallery, overlay handling   |
| `navigation.js` | Nav toggle + section switching                          |
| `speedometer.js`| Renders the current speed value                        |
| `trip.js`       | Renders current trip + trip history                    |
| `websocket.js`  | Opens the `/ws/dashboard` WebSocket channel            |

---

## Running the Project

### Prerequisites

- **Python 3.10+**
- **FFmpeg** (for video recording; optional for telemetry/GPS — the app will fail only when recording)
  - Windows: `winget install Gyan.FFmpeg` or via Chocolatey
  - Linux/Mac: `sudo apt install ffmpeg` / `brew install ffmpeg`
- **Node.js (not required)** for serving static files — any static file server works; Python's `http.server` is used in the scripts.

### 1. Create & activate a virtual environment

**Windows (PowerShell):**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**Linux/macOS (bash):**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Install backend dependencies

```bash
pip install -r backend/requirements.txt
```

### 3. Configure environment

```bash
cp .env.example .env    # adjust CAMERA_1_URL / CAMERA_2_URL as needed
```

### 4. Start the backend API

```bash
python backend/run.py
```

Or with uvicorn directly:

```bash
uvicorn backend.app.main:app --reload
```

Backend URL: `http://localhost:8000`

API docs:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### 5. Start the frontend

Serve `frontend/` with any static file server — the included scripts use Python's built-in server on port **5500**:

```bash
python -m http.server 5500 --directory frontend
```

Open `http://localhost:5500`.

---

## Dev Scripts (Bash / PowerShell)

The scripts directory contains cross-platform start/stop helpers that write PID files to `.run/`:

| Script                    | Action                                   |
|---------------------------|------------------------------------------|
| `scripts/start-dev-api.sh`  | Start FastAPI on port 8000 (`uvicorn`)   |
| `scripts/start-dashboard.sh`| Serve frontend on port 5500              |
| `scripts/start-dev.sh`      | Start API, wait, then serve dashboard     |
| `scripts/stop-dev-api.sh` | Stop the API process                      |
| `scripts/stop-dashboard.sh`  | Stop the dashboard process                |
| `scripts/stop-dev.sh`      | Stop both                                 |

```bash
# One-shot dev environment
bash scripts/start-dev.sh
# teardown
bash scripts/stop-dev.sh
```

---

## Testing

Run the pytest suite locally:

```bash
pytest
```

Integration smoke tests are in `tests/`:

- `test_database.py` — verifies `/healthcheck/db`, `/api/trip/current`, `/api/trip/startup`, and `/api/trip/history`
- `test_telemetry.py` — verifies `GET /api/telemetry/latest` returns speed/RPM fields
- `test_websocket.py` — verifies `/ws/dashboard` echo and `/api/health`

---

## Kiosk Deployment (Raspberry Pi)

### `~/.config/autostart/chromium-kiosk.desktop`

```ini
[Desktop Entry]
Type=Application
Name=Motorcycle Dashboard Kiosk
Exec=chromium --kiosk --noerrdialogs --disable-infobars http://localhost:5500
X-GNOME-Autostart-enabled=true
```

### systemd service unit — `system/motorcycle-dashboard.service`

Place in `/etc/systemd/system/motorcycle-dashboard.service` and adjust `WorkingDirectory` / `ExecStart` paths. It launches the backend as `pi` user and restarts on failure.

---

## Development Roadmap / Placeholders

The following areas are **stubs** awaiting implementation:

- `backend/app/communication/mqtt_client.py` — MQTT client stub
- `backend/app/communication/serial_client.py` — Serial client stub
- `devices/esp32-c6/` — Host-side firmware directory for the ESP32-C6 (future integration)
- `devices/esp32-s3-camera/` — Host-side firmware directory for the ESP32-S3 camera module

---

## Environment Variables

Copy `.env.example` to `.env` and adjust:

| Variable      | Purpose                               |
|---------------|---------------------------------------|
| `APP_NAME`    | App name (shown in FastAPI title)      |
| `APP_VERSION` | Version string                        |
| `CAMERA_1_URL`| Camera 1 (front) MJPEG stream URL      |
| `CAMERA_2_URL`| Camera 2 (rear) MJPEG stream URL       |
| `DATABASE_PATH`| SQLite database file path             |

---

## License

*(No license specified — all rights reserved unless otherwise noted.)*