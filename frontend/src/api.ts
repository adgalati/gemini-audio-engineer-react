const API_BASE = "";

// Helper function to handle response errors safely
async function handleResponse(res: Response, defaultMsg: string) {
  if (!res.ok) {
    const textBody = await res.text(); // Read stream ONCE
    try {
      // Try to parse as JSON to get the "detail" field from Python
      const jsonBody = JSON.parse(textBody);
      throw new Error(jsonBody.detail || jsonBody.message || textBody);
    } catch (e: any) {
      // If JSON parse fails, throw the raw text body
      // If the thrown error is the one we just threw above, rethrow it
      if (e.message && !e.message.includes("Unexpected token")) {
        throw e;
      }
      throw new Error(textBody || defaultMsg);
    }
  }
  return res.json();
}

interface FetchSpectrogramParams {
  file: File;
  startSec: number;
  endSec: number;
}

export async function fetchSpectrogram({ file, startSec, endSec }: FetchSpectrogramParams) {
  const fd = new FormData();
  fd.append("startSec", String(startSec));
  fd.append("endSec", String(endSec));
  fd.append("file", file);

  const res = await fetch(`${API_BASE}/api/spectrogram`, {
    method: "POST",
    body: fd,
  });

  return handleResponse(res, "Failed to generate spectrogram.");
}

interface AnalyzeAudioParams {
  file: File;
  startSec: number;
  endSec: number;
  prompt: string;
  modelId: string;
  temperature: number;
  thinkingBudget?: number;
  mode?: string;
}

export async function analyzeAudio({ file, startSec, endSec, prompt, modelId, temperature, thinkingBudget, mode }: AnalyzeAudioParams) {
  const fd = new FormData();
  fd.append("prompt", prompt);
  fd.append("modelId", modelId);
  fd.append("mode", mode || "engineer");
  fd.append("startSec", String(startSec));
  fd.append("endSec", String(endSec));
  fd.append("temperature", String(temperature));
  if (thinkingBudget) fd.append("thinkingBudget", String(thinkingBudget));
  fd.append("file", file);

  const res = await fetch(`${API_BASE}/api/analyze`, {
    method: "POST",
    body: fd,
  });

  return handleResponse(res, "Failed to analyze audio.");
}

export async function sendChatMessage(sessionId: string, message: string) {
  const fd = new FormData();
  fd.append("sessionId", sessionId);
  fd.append("message", message);

  const res = await fetch(`${API_BASE}/api/chat`, {
    method: "POST",
    body: fd,
  });

  return handleResponse(res, "Failed to send message.");
}
export async function startAudioProcessing(file: File, model: string = "demucs") {
  const fd = new FormData();
  fd.append("file", file);
  fd.append("model", model);

  const res = await fetch(`${API_BASE}/api/process`, {
    method: "POST",
    body: fd,
  });

  return handleResponse(res, "Failed to start processing job.");
}


export async function getJobStatus(jobId: string) {
  const res = await fetch(`${API_BASE}/api/process/${jobId}`);
  return handleResponse(res, "Failed to fetch job status.");
}

