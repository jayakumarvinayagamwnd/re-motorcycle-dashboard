document.addEventListener("DOMContentLoaded", () => {
  const toggle = document.getElementById("dashboard-toggle");
  const panel = document.getElementById("nav-panel");
  if (!toggle || !panel) {
    return;
  }

  toggle.addEventListener("click", () => {
    const isOpen = panel.classList.toggle("open");
    toggle.classList.toggle("open", isOpen);
    toggle.setAttribute("aria-expanded", String(isOpen));
  });

  const telemetryToggle = document.getElementById("telemetry-toggle");
  const telemetryPanel = document.getElementById("telemetry-panel");
  if (telemetryToggle && telemetryPanel) {
    telemetryToggle.addEventListener("click", () => {
      const isOpen = telemetryPanel.classList.toggle("open");
      telemetryToggle.classList.toggle("open", isOpen);
      telemetryToggle.setAttribute("aria-expanded", String(isOpen));
      telemetryToggle.querySelector("i").className = isOpen
        ? "bi bi-chevron-double-down"
        : "bi bi-chevron-double-up";
    });
  }

  const navItems = document.querySelectorAll(".nav-item[data-view]");
  const viewSections = document.querySelectorAll(".view-section");

  navItems.forEach((item) => {
    item.addEventListener("click", (event) => {
      event.preventDefault();
      const targetId = item.dataset.view;
      viewSections.forEach((section) => {
        section.classList.toggle("active", section.id === targetId);
      });
      panel.classList.remove("open");
      toggle.classList.remove("open");
      toggle.setAttribute("aria-expanded", "false");
    });
  });
});