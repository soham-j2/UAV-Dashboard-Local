const API_BASE_URL = "http://127.0.0.1:5000/api";

async function request(endpoint, options = {}) {
  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(
      errorText || `API request failed: ${response.status}`
    );
  }

  return response.json();
}


// ============================================================
// LIVE ENGINE DATA
// ============================================================

export async function getLiveEngineData() {
  return request("/engine/live");
}


// ============================================================
// DIGITAL TWIN
// ============================================================

export async function getDigitalTwin() {
  return request("/digital-twin");
}


// ============================================================
// AI ANALYSIS
// ============================================================

export async function getAIAnalysis() {
  return request("/ai/predict");
}


// ============================================================
// COMPLETE ENGINE STATUS
// ============================================================

export async function getEngineStatus() {
  return request("/engine/status");
}


// ============================================================
// FAULT INJECTION
// ============================================================

export async function injectFault(fault) {
  return request("/fault/inject", {
    method: "POST",
    body: JSON.stringify({
      fault,
    }),
  });
}


// ============================================================
// CLEAR FAULT
// ============================================================

export async function clearFault() {
  return request("/fault/clear", {
    method: "POST",
  });
}


// ============================================================
// MISSION FITNESS
// ============================================================

export async function evaluateMission(mission) {
  return request("/mission/evaluate", {
    method: "POST",
    body: JSON.stringify(mission),
  });
}