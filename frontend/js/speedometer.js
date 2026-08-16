function renderSpeedometer(speedKmh) {
  const speedValue = document.getElementById("speed-value");
  if (!speedValue) {
    return;
  }

  const rounded = Math.max(0, Math.round(speedKmh));
  speedValue.textContent = String(rounded);
}