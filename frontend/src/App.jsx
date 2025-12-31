import React, { useMemo, useState } from "react";
import Waveform from "./components/Waveform.jsx";
import { analyzeAudio, fetchSpectrogram } from "./api.js";

export default function App() {
  const [file, setFile] = useState(null);
  const [selection, setSelection] = useState({ startSec: 0, endSec: 0, durationSec: 0 });

  const [modelId, setModelId] = useState("gemini-3-flash-preview");
  const [temperature, setTemperature] = useState(0.2);

  const [prompt, setPrompt] = useState(
    "Analyze the low-end balance between the kick and bass. Is it muddy around 150–300 Hz? Suggest specific EQ and compression moves."
  );

  const [spectrogramB64, setSpectrogramB64] = useState("");
  const [advice, setAdvice] = useState("");
  const [error, setError] = useState("");

  const [loadingSpec, setLoadingSpec] = useState(false);
  const [loadingAnalyze, setLoadingAnalyze] = useState(false);

  const canAct = useMemo(() => {
    return !!file && selection.endSec > selection.startSec;
  }, [file, selection]);

  const onPickFile = (e) => {
    const f = e.target.files?.[0] || null;
    setFile(f);
    setAdvice("");
    setError("");
    setSpectrogramB64("");
  };

  const onSelectionChange = (sel) => {
    setSelection(sel);
  };

  const generateSpectrogram = async () => {
    if (!canAct) return;
    setError("");
    setLoadingSpec(true);
    try {
      const data = await fetchSpectrogram({
        file,
        startSec: selection.startSec,
        endSec: selection.endSec,
      });
      setSpectrogramB64(data.spectrogramPngBase64);
    } catch (e) {
      setError(e?.message || String(e));
    } finally {
      setLoadingSpec(false);
    }
  };

  const runAnalysis = async () => {
    if (!canAct) return;
    setError("");
    setLoadingAnalyze(true);
    try {
      const data = await analyzeAudio({
        file,
        startSec: selection.startSec,
        endSec: selection.endSec,
        prompt,
        modelId,
        temperature,
      });
      setAdvice(data.advice);
      setSpectrogramB64(data.spectrogramPngBase64);
    } catch (e) {
      setError(e?.message || String(e));
    } finally {
      setLoadingAnalyze(false);
    }
  };

  return (
    <div className="container">
      <div className="card stack">
        <div>
          <h1>🎛️ Mix Assistant (Gemini)</h1>
          <p>Upload a track, select a region, then request technical mix/mastering feedback.</p>
        </div>

        <div className="row">
          <div className="card stack">
            <div>
              <label>1) Upload audio</label>
              <input type="file" accept="audio/*" onChange={onPickFile} />
              <div className="muted">Supports WAV/MP3/FLAC/etc (browser-dependent). No Gemini calls happen until you click Analyze.</div>
            </div>

            {file && (
              <>
                <div className="hr" />
                <div>
                  <label>2) Waveform + selection (local)</label>
                  <Waveform file={file} onSelectionChange={onSelectionChange} />
                </div>

                <div className="kpi">
                  <span className="pill">Start: {selection.startSec.toFixed(2)}s</span>
                  <span className="pill">End: {selection.endSec.toFixed(2)}s</span>
                  <span className="pill">Len: {(selection.endSec - selection.startSec).toFixed(2)}s</span>
                </div>
              </>
            )}
          </div>

          <div className="card stack">
            <div>
              <label>Model</label>
              <select value={modelId} onChange={(e) => setModelId(e.target.value)}>
                <option value="gemini-3-flash-preview">gemini-3-flash-preview</option>
                <option value="gemini-3-pro-preview">gemini-3-pro-preview</option>
                <option value="gemini-2.5-flash">gemini-2.5-flash</option>
              </select>
              <div className="muted">If one fails due to access/region, try another.</div>
            </div>

            <div>
              <label>Temperature</label>
              <input
                type="number"
                min="0"
                max="1"
                step="0.05"
                value={temperature}
                onChange={(e) => setTemperature(Number(e.target.value))}
              />
            </div>

            <div>
              <label>3) Prompt</label>
              <textarea value={prompt} onChange={(e) => setPrompt(e.target.value)} />
            </div>

            <div className="kpi">
              <button className="btn secondary" disabled={!canAct || loadingSpec} onClick={generateSpectrogram}>
                {loadingSpec ? "Generating..." : "Generate Spectrogram"}
              </button>
              <button className="btn" disabled={!canAct || loadingAnalyze} onClick={runAnalysis}>
                {loadingAnalyze ? "Analyzing..." : "Analyze (Gemini)"}
              </button>
            </div>

            {error && (
              <div className="card" style={{ borderColor: "#ffb3b3", background: "#fff7f7" }}>
                <strong>Error</strong>
                <div className="muted">{error}</div>
              </div>
            )}
          </div>
        </div>

        {(spectrogramB64 || advice) && <div className="hr" />}

        <div className="row">
          <div className="card stack">
            <label>Spectrogram (server preview)</label>
            {spectrogramB64 ? (
              <img src={`data:image/png;base64,${spectrogramB64}`} alt="Spectrogram" />
            ) : (
              <div className="muted">Click “Generate Spectrogram” (no Gemini) or “Analyze” to render it.</div>
            )}
          </div>

          <div className="card stack">
            <label>Mix Assistant response</label>
            {advice ? <pre>{advice}</pre> : <div className="muted">Your Gemini response will appear here after analysis.</div>}
          </div>
        </div>
      </div>
    </div>
  );
}
