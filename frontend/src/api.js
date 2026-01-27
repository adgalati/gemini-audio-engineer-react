const API_BASE = "http://localhost:8000";

export async function fetchSpectrogram({ file, startSec, endSec }) {
  const fd = new FormData();
  fd.append("file", file);
  fd.append("startSec", String(startSec));
  fd.append("endSec", String(endSec));

  const res = await fetch(`${API_BASE}/api/spectrogram`, {
    method: "POST",
    body: fd,
  });

  if (!res.ok) {
    const msg = await res.text();
    throw new Error(msg || "Failed to generate spectrogram.");
  }
  return res.json();
}

export async function analyzeAudio({ file, startSec, endSec, prompt, modelId, temperature, thinkingBudget, mode, bpm, chords }) {
  const fd = new FormData();
  fd.append("file", file);
  fd.append("startSec", String(startSec));
  fd.append("endSec", String(endSec));
  fd.append("prompt", prompt);
  fd.append("modelId", modelId);
  fd.append("temperature", String(temperature));
  if (thinkingBudget) fd.append("thinkingBudget", String(thinkingBudget));
  fd.append("mode", mode || "engineer");

  // Pass user-edited BPM and chords for Producer mode
  if (bpm) fd.append("bpm", String(bpm));
  if (chords && chords.length > 0) fd.append("chords", JSON.stringify(chords));

  const res = await fetch(`${API_BASE}/api/analyze`, {
    method: "POST",
    body: fd,
  });

  if (!res.ok) {
    const msg = await res.text();
    throw new Error(msg || "Failed to analyze audio.");
  }
  return res.json();
}

export async function sendChatMessage(sessionId, message) {
  const fd = new FormData();
  fd.append("sessionId", sessionId);
  fd.append("message", message);

  const res = await fetch(`${API_BASE}/api/chat`, {
    method: "POST",
    body: fd,
  });

  if (!res.ok) {
    const msg = await res.text();
    throw new Error(msg || "Failed to send message.");
  }
  return res.json();
}
