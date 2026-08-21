function renderTrip(distanceKm, durationMin) {
  const tripValue = document.getElementById("trip-value");
  const tripTime = document.getElementById("tripTime");
  if (!tripValue) {
    return;
  }

  const distance = Number(distanceKm).toFixed(1);
  tripValue.textContent = distance;

  if (tripTime) {
    const duration = Math.max(0, Math.round(durationMin));
    const hours = Math.floor(duration / 60);
    const minutes = duration % 60;
    const seconds = 0;
    tripTime.textContent = `${String(hours).padStart(2, "0")}:${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
  }
}

function renderTripHistory(data) {
  const container = document.getElementById("trip-history-list");
  if (!container) return;

  if (!data || data.length === 0) {
    container.innerHTML = `<div class="trip-history-empty"><span>No trip records yet</span></div>`;
    return;
  }

  container.innerHTML = data.map((trip) => {
    const km = Number(trip.distance_km).toFixed(1);
    const date = trip.started_at ? trip.started_at.slice(0, 10) : "";
    return `
      <div class="trip-history-item">
        <span class="trip-history-name">${escapeHtml(trip.trip_name)}</span>
        <span class="trip-history-km">${km} <small>km</small></span>
        <span class="trip-history-date">${escapeHtml(date)}</span>
      </div>
    `;
  }).join("");
}

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}
