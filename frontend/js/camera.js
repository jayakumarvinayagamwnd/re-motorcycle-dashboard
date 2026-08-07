// Use the FastAPI proxy to avoid CORS / mixed-content issues
const CAMERA_1_STREAM_URL = `http://${window.location.hostname}:8000/api/camera/stream`;
const CAMERA_2_STREAM_URL = CAMERA_1_STREAM_URL;

function renderCameraStatus(isStreaming, cameraId = "camera-1", source = "none", streamUrl = null) {
  const stateNode = document.getElementById(`${cameraId}-state`);
  const tileNode = document.getElementById(cameraId);
  const sourceNode = document.getElementById(`${cameraId}-source`);
  const streamNode = document.getElementById(`${cameraId}-stream`);
  if (!stateNode || !tileNode) {
    return;
  }

  stateNode.textContent = isStreaming ? "Streaming" : "Offline";
  tileNode.style.borderColor = isStreaming ? "#1f9d55" : "#d4dbe4";

  if (sourceNode) {
    sourceNode.textContent = source || "none";
  }

  if (streamNode) {
    if (isStreaming && streamUrl) {
      streamNode.src = streamUrl;
      streamNode.hidden = false;
    } else {
      streamNode.src = "";
      streamNode.hidden = true;
    }
  }

  // Keep the fullscreen overlay in sync with the active camera tile
  const overlayImg = document.getElementById("camera-overlay-img");
  const overlayState = document.getElementById("camera-overlay-state");
  const activeCamera = document.body.dataset.activeCamera || "camera-1";
  if (cameraId === activeCamera) {
    if (isStreaming && streamUrl) {
      overlayImg.src = streamUrl;
      overlayState.textContent = "Streaming";
    } else {
      overlayImg.src = "";
      overlayState.textContent = "Offline";
    }
  }
}

function openCameraOverlay(cameraId = "camera-1") {
  const overlay = document.getElementById("camera-overlay");
  const overlayImg = document.getElementById("camera-overlay-img");
  const tileStream = document.getElementById(`${cameraId}-stream`);

  if (!overlay || !overlayImg) {
    return;
  }

  // Only allow opening fullscreen when the camera is streaming
  if (tileStream && tileStream.hidden) {
    return;
  }

  document.body.dataset.activeCamera = cameraId;
  overlayImg.alt = `${cameraId === "camera-2" ? "Camera 2" : "Camera 1"} fullscreen`;
  overlay.classList.add("open");
  document.body.style.overflow = "hidden";
}

function closeCameraOverlay() {
  const overlay = document.getElementById("camera-overlay");
  if (!overlay) {
    return;
  }
  overlay.classList.remove("open");
  document.body.style.overflow = "";
}

document.addEventListener("DOMContentLoaded", () => {
  const camera1Tile = document.getElementById("camera-1");
  const camera2Tile = document.getElementById("camera-2");
  const overlayClose = document.getElementById("camera-overlay-close");
  const overlay = document.getElementById("camera-overlay");

  const bindTile = (tile, cameraId) => {
    if (!tile) {
      return;
    }
    tile.addEventListener("click", () => openCameraOverlay(cameraId));
    tile.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        openCameraOverlay(cameraId);
      }
    });
  };

  bindTile(camera1Tile, "camera-1");
  bindTile(camera2Tile, "camera-2");

  if (overlayClose) {
    overlayClose.addEventListener("click", closeCameraOverlay);
  }

  if (overlay) {
    overlay.addEventListener("click", (event) => {
      if (event.target === overlay) {
        closeCameraOverlay();
      }
    });
  }

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      closeCameraOverlay();
    }
  });
});