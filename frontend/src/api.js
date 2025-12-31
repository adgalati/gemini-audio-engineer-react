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

export async function analyzeAudio({ file, startSec, endSec, prompt, modelId, temperature }) {
  const fd = new FormData();
  fd.append("file", file);
  fd.append("startSec", String(startSec));
  fd.append("endSec", String(endSec));
  fd.append("prompt", prompt);
  fd.append("modelId", modelId);
  fd.append("temperature", String(temperature));

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
