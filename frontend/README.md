# Frontend — Motorcycle Dashboard

The dashboard is a static web app that runs from `frontend/index.html` and talks to the FastAPI backend on port `8000`.

## Structure

```text
frontend/
├── index.html              # Single-page dashboard markup
├── css/
│   └── dashboard.css       # All dashboard styles (extracted from inline <style>)
├── js/
│   ├── app.js              # Polling loops + applying telemetry/GPS/camera/trip data
│   ├── camera.js           # Camera capture / record / fullscreen + render status
│   ├── gallery.js          # Saved images & videos gallery
│   ├── navigation.js       # Dashboard toggle + nav-view switching
│   ├── speedometer.js      # Speedometer rendering
│   ├── trip.js             # Trip rendering
│   └── websocket.js        # WebSocket connection helper
└── assets/
    ├── royal-enfield-classic-350.png   # Dashboard background image
    ├── icons/
    └── images/
        └── no-streaming.svg            # "NO STREAMING" placeholder
```

## Key Details

### Styling
All CSS lives in `css/dashboard.css`. It is the only stylesheet for the dashboard UI (Bootstrap and Bootstrap Icons are loaded from CDN in `index.html`).

The background image (`assets/royal-enfield-classic-350.png`) is applied on the `body` element and is **preserved for every theme** (emerald, ocean, violet, sunset, rose, slate). Each theme only overrides the gradient layers, not the background image.

### Camera Streaming
- Cameras 1 (front) and 2 (rear) stream through the backend proxy at `/api/camera/{id}/stream`.
- The frontend polls `/api/camera/status` every 2 seconds and toggles the visible stream element.
- When a camera is offline, the page hides the `<img class="camera-stream">` element (via the `hidden` attribute + `.camera-stream[hidden] { display: none }` rule) and shows the `assets/images/no-streaming.svg` placeholder.

### Scripts
| File | Responsibility |
|------|----------------|
| `app.js` | Sets up separate polling loops per endpoint and applies received data |
| `camera.js` | Capture, record, fullscreen, and stream status rendering |
| `gallery.js` | Loads and displays saved captures/recordings |
| `navigation.js` | Toggles the dashboard nav panel and switches between views |
| `speedometer.js` | Renders current speed |
| `trip.js` | Renders current trip distance/time |
| `websocket.js` | Opens the `/ws/dashboard` WebSocket |

## Running

The frontend is served as a static site from port `5500`:

```bash
bash scripts/start-dashboard.sh
```

Or serve it manually from the project root:

```bash
python -m http.server 5500 --directory frontend
```

Then open `http://localhost:5500`.

The backend API must be running for telemetry, GPS, camera, and trip data:

```bash
python backend/run.py   # http://localhost:8000
```

## Notes
- The old `frontend/components/` placeholder directory has been removed — all UI markup lives directly in `index.html`.
- The inline `<style>` block was extracted to `css/dashboard.css`.
- The inline dashboard/nav script was extracted to `js/navigation.js`.