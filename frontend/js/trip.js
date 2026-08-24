let currentTripId = null;
let lastCompletedTrip = null;
let pausedTrip = null;
let displayedTrip = null;

function initialiseTripStartControls() {
  const button = document.getElementById("trip-start-button");
  const pauseButton = document.getElementById("trip-pause-button");
  const resumeButton = document.getElementById("trip-resume-button");
  const finishButton = document.getElementById("trip-finish-button");
  const form = document.getElementById("trip-start-form");
  if (!button || !pauseButton || !resumeButton || !finishButton || !form) return;

  button.addEventListener("click", showTripStartForm);
  pauseButton.addEventListener("click", pauseCurrentTrip);
  resumeButton.addEventListener("click", resumeCurrentTrip);
  finishButton.addEventListener("click", finishCurrentTrip);
  form.addEventListener("submit", startNewTrip);
}

async function pauseCurrentTrip() {
  await changeTripState("pause");
}

async function resumeCurrentTrip() {
  await changeTripState("resume");
}

async function changeTripState(action) {
  const button = document.getElementById(`trip-${action}-button`);
  if (!button || currentTripId === null) return;

  const sourceTrip = displayedTrip;
  button.disabled = true;
  setTripStartMessage(`${action === "pause" ? "Pausing" : "Resuming"} trip…`);

  try {
    const response = await fetch(getTripActionUrl(action), { method: "POST" });
    const state = await response.json();
    if (!response.ok) throw new Error(state.message || `HTTP ${response.status}`);

    if (action === "pause") {
      pausedTrip = { ...sourceTrip, ...state };
      renderTrip(pausedTrip);
      setTripStartMessage(`Trip ID ${state.id} paused.`);
    } else {
      pausedTrip = null;
      renderTrip({ ...sourceTrip, ...state });
      setTripStartMessage(`Trip ID ${state.id} resumed.`);
    }
  } catch (error) {
    setTripStartMessage(`Unable to ${action} trip: ${error.message}`, true);
  } finally {
    button.disabled = false;
  }
}

async function showTripStartForm() {
  const button = document.getElementById("trip-start-button");
  const form = document.getElementById("trip-start-form");
  const nameInput = document.getElementById("trip-start-name");
  if (!button || !form || !nameInput) return;

  button.disabled = true;
  setTripStartMessage("Checking trip status…");

  try {
    const response = await fetch(`${API_BASE}/trip/startup`);
    const startup = await response.json();
    if (!response.ok) throw new Error(startup.message || `HTTP ${response.status}`);

    if (startup.state !== "READY") {
      const currentTrip = startup.current_trip;
      const description = currentTrip
        ? `Trip ID ${currentTrip.id} is ${currentTrip.status}.`
        : "A trip cannot be started right now.";
      setTripStartMessage(description, true);
      return;
    }

    form.hidden = false;
    button.hidden = true;
    const previousTrip = startup.previous_trip;
    setTripStartMessage(previousTrip ? `Last trip: ${previousTrip.trip_name} (ID ${previousTrip.id})` : "Enter a name for the new trip.");
    nameInput.focus();
  } catch (error) {
    setTripStartMessage(`Unable to check trip status: ${error.message}`, true);
  } finally {
    button.disabled = false;
  }
}

async function startNewTrip(event) {
  event.preventDefault();

  const form = event.currentTarget;
  const nameInput = document.getElementById("trip-start-name");
  const submitButton = form.querySelector("button[type='submit']");
  const tripName = nameInput?.value.trim();
  if (!tripName || !submitButton) return;

  submitButton.disabled = true;
  setTripStartMessage("Starting trip…");

  try {
    const response = await fetch(`${API_BASE}/trip/start`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ trip_name: tripName }),
    });
    const trip = await response.json();
    if (!response.ok) throw new Error(trip.message || `HTTP ${response.status}`);

    renderTrip(trip);
    form.hidden = true;
    const startButton = document.getElementById("trip-start-button");
    if (startButton) startButton.hidden = true;
    setTripStartMessage(`Trip ID ${trip.id} started.`);
  } catch (error) {
    setTripStartMessage(`Unable to start trip: ${error.message}`, true);
  } finally {
    submitButton.disabled = false;
  }
}

async function finishCurrentTrip() {
  const finishButton = document.getElementById("trip-finish-button");
  if (!finishButton || currentTripId === null) return;

  finishButton.disabled = true;
  setTripStartMessage("Finishing trip…");

  try {
    const response = await fetch(getTripActionUrl("finish"), { method: "POST" });
    const trip = await response.json();
    if (!response.ok) throw new Error(trip.message || `HTTP ${response.status}`);

    lastCompletedTrip = trip;
    pausedTrip = null;
    renderTrip(null);
    setTripStartMessage(`Trip ID ${trip.id} completed. You can start a new trip.`);
    fetchJson(TRIP_HISTORY_API).then(applyTripHistory).catch(() => {});
  } catch (error) {
    setTripStartMessage(`Unable to finish trip: ${error.message}`, true);
  } finally {
    finishButton.disabled = false;
  }
}

function setTripStartMessage(message, isError = false) {
  const element = document.getElementById("trip-start-message");
  if (!element) return;

  element.textContent = message;
  element.classList.toggle("is-error", isError);
}

function renderTrip(trip) {
  const elements = {
    card: document.querySelector(".trip-card"),
    id: document.getElementById("trip-id"),
    status: document.getElementById("trip-status"),
    name: document.getElementById("trip-name"),
    startedAt: document.getElementById("trip-started-at"),
    distance: document.getElementById("trip-value"),
    duration: document.getElementById("tripTime"),
    avgSpeed: document.getElementById("trip-avg-speed"),
    maxSpeed: document.getElementById("trip-max-speed"),
  };

  if (!elements.distance) return;

  // A /trip/current poll started before a pause can return stale ACTIVE data.
  // Keep the locally confirmed PAUSED state until the user resumes it.
  if (pausedTrip && trip?.id === pausedTrip.id && trip.status === "ACTIVE") {
    trip = pausedTrip;
  }
  if (!trip && pausedTrip) trip = pausedTrip;

  if (!trip) {
    currentTripId = null;
    displayedTrip = null;
    const startButton = document.getElementById("trip-start-button");
    const startForm = document.getElementById("trip-start-form");
    const pauseButton = document.getElementById("trip-pause-button");
    const resumeButton = document.getElementById("trip-resume-button");
    const finishButton = document.getElementById("trip-finish-button");
    if (lastCompletedTrip) {
      elements.card?.setAttribute("data-trip-id", String(lastCompletedTrip.id));
      elements.id.textContent = `ID ${lastCompletedTrip.id}`;
      elements.status.textContent = lastCompletedTrip.status || "COMPLETED";
      elements.name.textContent = lastCompletedTrip.trip_name || "Completed trip";
      elements.startedAt.textContent = `Completed ${formatTripDate(lastCompletedTrip.ended_at)}`;
      elements.distance.textContent = formatTripNumber(lastCompletedTrip.distance_km);
      elements.duration.textContent = formatTripDuration(lastCompletedTrip.duration_sec);
      elements.avgSpeed.textContent = formatTripNumber(lastCompletedTrip.avg_speed_kmh);
      elements.maxSpeed.textContent = formatTripNumber(lastCompletedTrip.max_speed_kmh);
      if (finishButton) finishButton.hidden = true;
      if (pauseButton) pauseButton.hidden = true;
      if (resumeButton) resumeButton.hidden = true;
      if (startButton && startForm?.hidden) startButton.hidden = false;
      return;
    }
    if (startButton && startForm?.hidden) startButton.hidden = false;
    if (finishButton) finishButton.hidden = true;
    if (pauseButton) pauseButton.hidden = true;
    if (resumeButton) resumeButton.hidden = true;
    elements.card?.removeAttribute("data-trip-id");
    elements.id.textContent = "ID —";
    elements.status.textContent = "No active trip";
    elements.name.textContent = "No active trip";
    elements.startedAt.textContent = "Started —";
    elements.distance.textContent = "—";
    elements.duration.textContent = "—";
    elements.avgSpeed.textContent = "—";
    elements.maxSpeed.textContent = "—";
    return;
  }

  lastCompletedTrip = null;
  displayedTrip = trip;
  const isPaused = trip.status === "PAUSED";
  if (!isPaused) pausedTrip = null;
  const startForm = document.getElementById("trip-start-form");
  const startButton = document.getElementById("trip-start-button");
  const pauseButton = document.getElementById("trip-pause-button");
  const resumeButton = document.getElementById("trip-resume-button");
  const finishButton = document.getElementById("trip-finish-button");
  if (startForm) startForm.hidden = true;
  if (startButton) startButton.hidden = true;
  if (finishButton) finishButton.hidden = false;
  if (pauseButton) pauseButton.hidden = isPaused;
  if (resumeButton) resumeButton.hidden = !isPaused;

  currentTripId = Number.isInteger(Number(trip.id)) && Number(trip.id) > 0
    ? Number(trip.id)
    : null;
  elements.card?.toggleAttribute("data-trip-id", currentTripId !== null);
  if (currentTripId !== null) {
    elements.card.dataset.tripId = String(currentTripId);
  }
  elements.id.textContent = currentTripId === null ? "ID —" : `ID ${currentTripId}`;
  elements.status.textContent = trip.status || "ACTIVE";
  elements.name.textContent = trip.trip_name || "Unnamed trip";
  elements.startedAt.textContent = `Started ${formatTripDate(trip.started_at)}`;
  elements.distance.textContent = formatTripNumber(trip.distance_km);
  elements.duration.textContent = formatTripDuration(trip.duration_sec);
  elements.avgSpeed.textContent = formatTripNumber(trip.avg_speed_kmh);
  elements.maxSpeed.textContent = formatTripNumber(trip.max_speed_kmh);
}

function getCurrentTripId() {
  return currentTripId;
}

function getTripActionUrl(action) {
  if (!["pause", "resume", "finish"].includes(action)) {
    throw new Error(`Unsupported trip action: ${action}`);
  }

  if (currentTripId === null) {
    throw new Error("No active trip is available for this action.");
  }

  return `${API_BASE}/trip/${currentTripId}/${action}`;
}

function formatTripNumber(value) {
  const number = Number(value);
  return Number.isFinite(number) ? number.toFixed(1) : "—";
}

function formatTripDuration(value) {
  const totalSeconds = Math.max(0, Math.round(Number(value) || 0));
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;
  return `${String(hours).padStart(2, "0")}:${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
}

function formatTripDate(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";

  return new Intl.DateTimeFormat(undefined, {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

function renderTripHistory(data) {
  const container = document.getElementById("trip-history-list");
  if (!container) return;

  if (!Array.isArray(data) || data.length === 0) {
    container.innerHTML = `<div class="trip-history-empty"><span>No trip records yet</span></div>`;
    return;
  }

  container.innerHTML = data.map((trip) => {
    const tripId = Number.isInteger(Number(trip.id)) && Number(trip.id) > 0
      ? Number(trip.id)
      : null;
    return `
      <article class="trip-history-item" data-trip-id="${tripId ?? ""}">
        <div class="trip-history-header">
          <span class="trip-history-name">${escapeHtml(trip.trip_name || "Unnamed trip")}</span>
          <span class="trip-history-reference">ID ${tripId ?? "—"}</span>
        </div>
        <div class="trip-history-meta">
          <span>${escapeHtml(trip.status || "UNKNOWN")}</span>
          <span>${escapeHtml(formatTripDate(trip.started_at))}</span>
        </div>
        <div class="trip-history-metrics">
          <span><small>Distance</small>${formatTripNumber(trip.distance_km)} <em>km</em></span>
          <span><small>Duration</small>${formatTripDuration(trip.duration_sec)}</span>
          <span><small>Avg speed</small>${formatTripNumber(trip.avg_speed_kmh)} <em>km/h</em></span>
          <span><small>Max speed</small>${formatTripNumber(trip.max_speed_kmh)} <em>km/h</em></span>
        </div>
      </article>
    `;
  }).join("");
}

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}
