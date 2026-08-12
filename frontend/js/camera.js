// Use the FastAPI proxy to avoid CORS / mixed-content issues
const CAMERA_1_STREAM_URL = `http://${window.location.hostname}:8000/api/camera/1/stream`;
const CAMERA_2_STREAM_URL = `http://${window.location.hostname}:8000/api/camera/2/stream`;
const CAMERA_CAPTURE_URL = (cameraId) => `http://${window.location.hostname}:8000/api/camera/${cameraId}/capture`;
const CAMERA_RECORD_URL = (cameraId) => `http://${window.location.hostname}:8000/api/camera/${cameraId}/record`;

const camera = {
  capture: async (cameraId) => {
    try {
      if (![1, 2].includes(cameraId)) {
        console.error(`Invalid camera ID: ${cameraId}`);
        return;
      }

      var cameraPosition = { "camera": "front" };
      if (cameraId === 1) {
        cameraPosition.camera = "front";
      }

      if (cameraId === 2) {
        cameraPosition.camera = "rear";
      }

      console.log(`Capturing camera ${cameraPosition.camera} frame...`);
      const response = await fetch(CAMERA_CAPTURE_URL(cameraId), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(cameraPosition),
      });
      if (!response.ok) {
        throw new Error((await response.json()).detail || "Capture request failed");
      }
      console.log(await response.json());
    } catch (error) {
      console.error(`Failed to capture camera ${cameraId}:`, error);
    }
  },

  toggleRecording: async (cameraId) => {
    const button = document.getElementById(`camera-${cameraId}-recording`);
    if (!button) {
      return;
    }

    if (button.classList.contains("recording")) {
      return;
    }

    button.classList.add("recording");
    button.title = "Stop Recording";
    const icon = button.querySelector("i");
    if (icon) {
      icon.classList.remove("bi-record-circle");
      icon.classList.add("bi-stop-circle");
    }
    button.disabled = true;
    console.info(`Camera ${cameraId} 30-second recording started`);

    try {
      const response = await fetch(CAMERA_RECORD_URL(cameraId), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ camera: cameraId === 1 ? "front" : "rear" }),
      });
      if (!response.ok) {
        throw new Error((await response.json()).detail || "Recording request failed");
      }
      console.info(`Camera ${cameraId} recording stopped`, await response.json());
    } catch (error) {
      console.error(`Camera ${cameraId} recording failed`, error);
    } finally {
      button.disabled = false;
      button.classList.remove("recording");
      button.title = "Start Recording";
      if (icon) {
        icon.classList.remove("bi-stop-circle");
        icon.classList.add("bi-record-circle");
      }
    }
  },

  openFullscreen: (cameraId) => {
    const streamNode = document.getElementById(`camera-${cameraId}-stream`);
    const overlay = document.getElementById("camera-overlay");
    const overlayStream = document.getElementById("camera-overlay-stream");
    const overlayTitle = document.getElementById("camera-overlay-title");

    if (!streamNode?.src || streamNode.hidden || !overlay || !overlayStream) {
      console.warn(`Cannot open Camera ${cameraId}: stream is not active`);
      return;
    }

    overlayStream.src = streamNode.currentSrc || streamNode.src;
    overlayStream.alt = `Camera ${cameraId} fullscreen stream`;
    if (overlayTitle) {
      overlayTitle.textContent = `Camera ${cameraId}`;
    }
    overlay.classList.add("open");
    document.body.classList.add("camera-overlay-open");
  },

  closeFullscreen: () => {
    const overlay = document.getElementById("camera-overlay");
    const overlayStream = document.getElementById("camera-overlay-stream");
    if (!overlay) {
      return;
    }

    overlay.classList.remove("open");
    document.body.classList.remove("camera-overlay-open");
    if (overlayStream) {
      overlayStream.src = "";
    }
  },
};

document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("camera-overlay-close")?.addEventListener("click", () => {
    camera.closeFullscreen();
  });

  document.getElementById("camera-overlay")?.addEventListener("click", (event) => {
    if (event.target.id === "camera-overlay") {
      camera.closeFullscreen();
    }
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      camera.closeFullscreen();
    }
  });
});

function renderCameraStatus(isStreaming, cameraId, source, streamUrl) {
  const streamNode = document.getElementById(`camera-${cameraId}-stream`);
  const placeholderNode = document.getElementById(`camera-${cameraId}-placeholder`);
  const liveIndicator = streamNode?.closest(".camera-card")?.querySelector(".camera-live");
  const liveDot = liveIndicator?.querySelector(".live-dot");

  if (streamNode) {
    if (streamUrl) {
      // Only set src once so the browser doesn't reload the MJPEG stream on every poll
      if (streamNode.src !== streamUrl) {
        streamNode.src = streamUrl;
      }
      streamNode.hidden = false;
      if (placeholderNode) {
        placeholderNode.style.display = "none";
      }
    } else {
      streamNode.src = "";
      streamNode.hidden = true;
      if (placeholderNode) {
        placeholderNode.style.display = "block";
      }
    }
  }

  if (liveIndicator) {
    liveIndicator.style.display = isStreaming ? "flex" : "none";
  }
  if (liveDot) {
    liveDot.style.background = isStreaming ? "#00d6a3" : "#666";
    liveDot.style.boxShadow = isStreaming ? "0 0 8px rgba(0,214,163,0.8)" : "none";
  }
}
