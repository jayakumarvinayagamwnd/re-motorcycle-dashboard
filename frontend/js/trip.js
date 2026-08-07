function renderTrip(distanceKm, durationMin) {
  const tripValue = document.getElementById("trip-value");
  if (!tripValue) {
    return;
  }

  const distance = Number(distanceKm).toFixed(1);
  const duration = Math.max(0, Math.round(durationMin));
  tripValue.textContent = `${distance} km (${duration} min)`;
}
