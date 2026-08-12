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