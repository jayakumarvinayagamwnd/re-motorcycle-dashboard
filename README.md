# Motorcycle Dashboard

Motorcycle dashboard starter project with:

- FastAPI backend for telemetry, GPS, trip, camera, and websocket data
- Static frontend dashboard shell
- Service and system script placeholders for kiosk deployment

## Project Structure

```text
motorcycle-dashboard/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── communication/
│   │   ├── config/
│   │   ├── models/
│   │   ├── services/
│   │   ├── websocket/
│   │   └── main.py
│   ├── requirements.txt
│   └── run.py
├── frontend/
│   ├── index.html
│   ├── css/
│   ├── js/
│   ├── components/
│   └── assets/
├── data/
├── scripts/
├── system/
├── tests/
├── .env
└── .gitignore
```

## Backend Setup

1. Create and activate a virtual environment.
2. Install dependencies:

```bash
pip install -r backend/requirements.txt
```

## Windows Quick Start (PowerShell)

Run from the project root:

```powershell
Set-Location "G:\git\motorcycle-dashboard"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r backend\requirements.txt
python backend\run.py
```

In a second PowerShell terminal (with the same venv activated), run tests:

```powershell
Set-Location "G:\git\motorcycle-dashboard"
.\.venv\Scripts\Activate.ps1
pytest
```

If script execution is blocked:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

cmd.exe alternative:

```bat
cd /d G:\git\motorcycle-dashboard
python -m venv .venv
.venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r backend\requirements.txt
python backend\run.py
```

## Run Backend

Option 1:

```bash
python backend/run.py
```

Option 2:

```bash
uvicorn backend.app.main:app --reload
```

Backend URL: `http://localhost:8000`

API docs:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Frontend

Open `frontend/index.html` directly in a browser, or serve `frontend/` with any static file server.

## Available Endpoints

- `GET /`
- `GET /api/health`
- `GET /api/telemetry/latest`
- `GET /api/gps/latest`
- `GET /api/camera/status`
- `GET /api/trip/current`
- `WS /ws/dashboard`

## Run Tests

```bash
pytest
```

## Environment Variables

Default values are in `.env` and `.env.example`:

- `APP_NAME`
- `APP_VERSION`
