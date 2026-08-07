function connectDashboardSocket() {
  const ws = new WebSocket("ws://localhost:8000/ws/dashboard");
  ws.onopen = () => console.log("WebSocket connected");
  ws.onmessage = (event) => console.log("WS message", event.data);
  ws.onclose = () => console.log("WebSocket disconnected");
  return ws;
}
