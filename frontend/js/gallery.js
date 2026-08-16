const GALLERY_API = `http://${window.location.hostname}:8000/api/camera/gallery`;
const GALLERY_ORIGIN = `http://${window.location.hostname}:8000`;

document.addEventListener("DOMContentLoaded", () => {
  initialiseGalleryOverlay();
  loadGallery();
});

async function loadGallery() {
  try {
    const response = await fetch(GALLERY_API);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const gallery = await response.json();
    renderGalleryGroup("gallery-images", gallery.images || [], "image");
    renderGalleryGroup("gallery-videos", gallery.videos || [], "video");
    updateGalleryCount("gallery-images-count", gallery.images?.length || 0);
    updateGalleryCount("gallery-videos-count", gallery.videos?.length || 0);
  } catch (error) {
    console.error("Unable to load gallery", error);
    renderGalleryError("gallery-images");
    renderGalleryError("gallery-videos");
  }
}

function renderGalleryGroup(containerId, items, mediaKind) {
  const container = document.getElementById(containerId);
  if (!container) return;
  container.replaceChildren();
  if (!items.length) {
    container.append(createGalleryEmpty(`No ${mediaKind === "image" ? "images" : "videos"} saved yet`));
    return;
  }
  items.forEach((item) => container.append(createGalleryThumbnail(item, mediaKind)));
}

function createGalleryThumbnail(item, mediaKind) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = "gallery-thumbnail";
  button.setAttribute("aria-label", `Open ${item.name}`);
  const url = `${GALLERY_ORIGIN}${item.url}`;

  if (mediaKind === "image") {
    const image = document.createElement("img");
    image.src = url;
    image.alt = item.name;
    image.loading = "lazy";
    button.append(image);
  } else {
    const video = document.createElement("video");
    video.src = `${url}#t=0.1`;
    video.muted = true;
    video.preload = "metadata";
    video.setAttribute("aria-hidden", "true");
    button.append(video);
    const play = document.createElement("span");
    play.className = "gallery-play";
    play.innerHTML = '<i class="bi bi-play-fill"></i>';
    button.append(play);
  }

  const label = document.createElement("span");
  label.className = "gallery-thumbnail-label";
  label.textContent = formatMediaName(item.name);
  button.append(label);
  button.addEventListener("click", () => openGalleryMedia(item, mediaKind));
  return button;
}

function createGalleryEmpty(message) {
  const empty = document.createElement("div");
  empty.className = "gallery-empty";
  empty.textContent = message;
  return empty;
}

function renderGalleryError(containerId) {
  const container = document.getElementById(containerId);
  if (!container) return;
  container.replaceChildren(createGalleryEmpty("Gallery is unavailable"));
}

function updateGalleryCount(elementId, count) {
  const countNode = document.getElementById(elementId);
  if (countNode) countNode.textContent = `(${count})`;
}

function openGalleryMedia(item, mediaKind) {
  const overlay = document.getElementById("gallery-overlay");
  const content = document.getElementById("gallery-overlay-content");
  const title = document.getElementById("gallery-overlay-title");
  if (!overlay || !content || !title) return;
  content.replaceChildren();
  const media = document.createElement(mediaKind === "image" ? "img" : "video");
  media.className = "gallery-overlay-media";
  media.src = `${GALLERY_ORIGIN}${item.url}`;
  if (mediaKind === "image") {
    media.alt = item.name;
  } else {
    media.controls = true;
    media.autoplay = true;
    media.playsInline = true;
  }
  title.textContent = formatMediaName(item.name);
  content.append(media);
  overlay.classList.add("open");
  document.body.classList.add("camera-overlay-open");
}

function closeGalleryOverlay() {
  const overlay = document.getElementById("gallery-overlay");
  const content = document.getElementById("gallery-overlay-content");
  content?.querySelector("video")?.pause();
  content?.replaceChildren();
  overlay?.classList.remove("open");
  document.body.classList.remove("camera-overlay-open");
}

function initialiseGalleryOverlay() {
  document.getElementById("gallery-overlay-close")?.addEventListener("click", closeGalleryOverlay);
  document.getElementById("gallery-overlay")?.addEventListener("click", (event) => {
    if (event.target.id === "gallery-overlay") closeGalleryOverlay();
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && document.getElementById("gallery-overlay")?.classList.contains("open")) {
      closeGalleryOverlay();
    }
  });
}

function formatMediaName(name) {
  return name.replace(/\.[^.]+$/, "").replace(/_/g, " ");
}
