// Use the FastAPI proxy to avoid CORS / mixed-content issues
const CAMERA_1_STREAM_URL = `http://${window.location.hostname}:8000/api/camera/stream`;
const CAMERA_2_STREAM_URL = CAMERA_1_STREAM_URL;
const CAMERA_CAPTURE_URL = `http://${window.location.hostname}:8000/api/camera/capture`;

async function captureFrame(cameraId) {
  const streamNode = document.getElementById(`${cameraId}-stream`);
  if (!streamNode || streamNode.hidden) {
    console.warn(`Cannot capture ${cameraId}: stream is not active`);
    return;
  }

  const button = document.getElementById(`${cameraId}-snapshot`);
  if (button) {
    button.disabled = true;
  }

  try {
    // Read the current frame from the live <img> element
    const captureCanvas = document.createElement("canvas");
    captureCanvas.width = streamNode.naturalWidth || streamNode.width;
    captureCanvas.height = streamNode.naturalHeight || streamNode.height;
    const ctx = captureCanvas.getContext("2d");
    ctx.drawImage(streamNode, 0, 0);
    const jpegBlob = await new Promise((resolve) => {
      captureCanvas.toBlob(resolve, "image/jpeg", 0.85);
    });
    if (!jpegBlob) {
      throw new Error("Failed to encode frame as JPEG");
    }

    const formData = new FormData();
    formData.append("file", jpegBlob, `${cameraId}_snapshot.jpg`);

    const response = await fetch(CAMERA_CAPTURE_URL, {
      method: "POST",
      body: formData,
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }
    const result = await response.json();
    console.log(`Snapshot saved: ${result.path}`);
  } catch (error) {
    console.error(`Failed to capture ${cameraId}:`, error);
  } finally {
    if (button) {
      button.disabled = false;
    }
  }
}

function renderCameraStatus(isStreaming, cameraId = "camera-1", source = "none", streamUrl = null) {
  const statusNode = document.getElementById(`${cameraId}-status`);
  const statusTextNode = document.getElementById(`${cameraId}-status-text`);
  const statusBadgeNode = document.getElementById(`${cameraId}-status-badge`);
  const tileNode = document.getElementById(cameraId);
  const streamNode = document.getElementById(`${cameraId}-stream`);
  if (!statusNode || !tileNode) {
    return;
  }

  if (statusBadgeNode) {
    statusBadgeNode.textContent = source || "none";
  }
  if (statusTextNode) {
    statusTextNode.textContent = isStreaming ? "Streaming" : "Offline";
  }
  statusNode.classList.toggle("btn-primary", isStreaming);
  statusNode.classList.toggle("btn-info", !isStreaming);
  tileNode.style.borderColor = isStreaming ? "#1f9d55" : "#d4dbe4";

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

function toggleRecording(buttonId) {
  const button = document.getElementById(buttonId);
  if (!button) {
    return;
  }
  const isRecording = button.classList.toggle("btn-danger");
  button.classList.toggle("btn-success", !isRecording);
  const label = button.querySelector(".rec-label");
  if (label) {
    label.textContent = isRecording ? "Stop" : "Recording";
  }
  const dot = button.querySelector(".rec-dot");
  if (dot) {
    dot.classList.toggle("recording-active", isRecording);
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

  // Snapshot buttons
  const snapshot1 = document.getElementById("camera-1-snapshot");
  const snapshot2 = document.getElementById("camera-2-snapshot");
  if (snapshot1) {
    snapshot1.addEventListener("click", (event) => {
      event.stopPropagation();
      captureFrame("camera-1");
    });
  }
  if (snapshot2) {
    snapshot2.addEventListener("click", (event) => {
      event.stopPropagation();
      captureFrame("camera-2");
    });
  }

  // Recording toggle buttons
  const recording1 = document.getElementById("camera-1-recording");
  const recording2 = document.getElementById("camera-2-recording");
  if (recording1) {
    recording1.addEventListener("click", (event) => {
      event.stopPropagation();
      toggleRecording("camera-1-recording");
    });
  }
  if (recording2) {
    recording2.addEventListener("click", (event) => {
      event.stopPropagation();
      toggleRecording("camera-2-recording");
    });
  }

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