import React, { useMemo, useState, useCallback, useRef, useEffect } from "react";
import Waveform from "./components/Waveform.jsx";
import { analyzeAudio, fetchSpectrogram, sendChatMessage } from "./api.js";
import placeholderImg from "./assets/placeholder.png";
import logoImg from "./assets/logo.png";

export default function App() {
  const [file, setFile] = useState(null);
  const [selection, setSelection] = useState({ startSec: 0, endSec: 0, durationSec: 0 });

  const [modelId, setModelId] = useState("gemini-3-pro-preview"); // Default to newer model
  const [temperature, setTemperature] = useState(0.2);
  const [thinkingBudget, setThinkingBudget] = useState(0);

  // Check if using GPT Audio model (has limitations: no images, no thinking)
  const isGptAudio = modelId.startsWith("gpt-");

  const [prompt, setPrompt] = useState("");

  const SUGGESTIONS = [
    "Check the overall frequency balance.",
    "Are the vocals sitting correctly in the mix?",
    "Evaluate the stereo width and mono compatibility.",
    "Is the low-end (kick/bass) well-defined?",
    "Suggest mastering moves for a commercial polish."
  ];

  const [spectrogramB64, setSpectrogramB64] = useState("");

  // Chat State
  const [sessionId, setSessionId] = useState(null);
  const [chatMessages, setChatMessages] = useState([]);
  const [replyInput, setReplyInput] = useState("");

  const [error, setError] = useState("");
  const [loadingSpec, setLoadingSpec] = useState(false);
  const [loadingAnalyze, setLoadingAnalyze] = useState(false);
  const [loadingReply, setLoadingReply] = useState(false);

  const chatEndRef = useRef(null);

  // Auto-scroll to bottom of chat
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatMessages]);

  const canAct = useMemo(() => {
    return !!file && selection.endSec > selection.startSec;
  }, [file, selection]);

  const onPickFile = (e) => {
    const f = e.target.files?.[0] || null;
    setFile(f);
    setChatMessages([]);
    setSessionId(null);
    setError("");
    setSpectrogramB64("");
  };

  const onSelectionChange = useCallback((sel) => {
    setSelection(sel);
  }, []);

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
    setChatMessages([]); // Reset chat on new analysis
    setSessionId(null);

    try {
      // Optimistic update
      setChatMessages([{ role: "user", text: prompt }]);

      const data = await analyzeAudio({
        file,
        startSec: selection.startSec,
        endSec: selection.endSec,
        prompt,
        modelId,
        temperature,
        thinkingBudget,
      });

      setSessionId(data.sessionId);
      setSpectrogramB64(data.spectrogramPngBase64);
      setChatMessages(prev => [...prev, { role: "model", text: data.advice }]);
    } catch (e) {
      setError(e?.message || String(e));
      setChatMessages(prev => prev.filter(m => m.text !== prompt)); // Remove failed prompt
    } finally {
      setLoadingAnalyze(false);
    }
  };

  const sendReply = async () => {
    if (!sessionId || !replyInput.trim()) return;
    setLoadingReply(true);
    const msg = replyInput;
    setReplyInput("");

    setChatMessages(prev => [...prev, { role: "user", text: msg }]);

    try {
      const data = await sendChatMessage(sessionId, msg);
      setChatMessages(prev => [...prev, { role: "model", text: data.reply }]);
    } catch (e) {
      setError(e?.message || String(e));
    } finally {
      setLoadingReply(false);
    }
  };

  return (
    <div className="container">
      <header className="hero-section">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '20px', marginBottom: '16px' }}>
          <img src={logoImg} alt="App Logo" className="app-logo" />
          <h1>Mix Assistant AI</h1>
        </div>
        <p>Professional Grade Audio Engineering & Critical Listening</p>
      </header>

      <div className="row">
        {/* LEFT COLUMN: Source + Visualization */}
        <div className="stack">
          <section className="card stack">
            <div>
              <label>1) Studio Source</label>
              <input type="file" accept="audio/*" onChange={onPickFile} />
              <div className="muted" style={{ marginTop: '8px' }}>
                WAV / MP3 / FLAC supported.
              </div>
            </div>

            {file && (
              <>
                <div className="hr" />
                <div>
                  <label>2) Signal Selection</label>
                  <Waveform file={file} onSelectionChange={onSelectionChange} />
                </div>

                <div className="kpi">
                  <span className="pill">Start: {selection.startSec.toFixed(2)}s</span>
                  <span className="pill">End: {selection.endSec.toFixed(2)}s</span>
                  <span className="pill">Region: {(selection.endSec - selection.startSec).toFixed(2)}s</span>
                </div>
              </>
            )}
          </section>

          {/* Spectrogram now lives in left column */}
          <section className="card spectrogram-card">
            <label>Spectrogram Reference</label>
            {spectrogramB64 ? (
              <img src={`data:image/png;base64,${spectrogramB64}`} alt="Spectrogram" />
            ) : (
              <div className="spectrogram-placeholder">
                <div className="muted">Visual data will appear after analysis</div>
              </div>
            )}
          </section>
        </div>

        {/* RIGHT COLUMN: Settings + Chat */}
        <div className="stack">
          <section className="card stack">
            {/* Compact 3-column settings row */}
            <div className="row" style={{ gridTemplateColumns: "1fr 1fr 1fr", gap: '12px' }}>
              <div>
                <label>Model</label>
                <select value={modelId} onChange={(e) => setModelId(e.target.value)}>
                  <optgroup label="OpenAI">
                    <option value="gpt-audio">GPT Audio</option>
                  </optgroup>
                  <optgroup label="Gemini">
                    <option value="gemini-3-pro-preview">gemini-3-pro</option>
                    <option value="gemini-3-flash-preview">gemini-3-flash</option>
                    <option value="gemini-2.0-flash-thinking-exp">gemini-2.0-thinking</option>
                    <option value="gemini-2.0-flash-exp">gemini-2.0-flash</option>
                  </optgroup>
                </select>
              </div>
              <div>
                <label>Style</label>
                <select
                  value={temperature}
                  onChange={(e) => setTemperature(Number(e.target.value))}
                >
                  <option value={0.1}>Focused</option>
                  <option value={0.4}>Balanced</option>
                  <option value={0.7}>Creative</option>
                  <option value={1.0}>Unusual</option>
                </select>
              </div>
              <div>
                <label style={{ opacity: isGptAudio ? 0.5 : 1 }}>Thinking {isGptAudio && <span style={{ fontSize: '0.7em', color: '#fbbf24' }}>(N/A)</span>}</label>
                <select
                  value={isGptAudio ? 0 : thinkingBudget}
                  onChange={(e) => setThinkingBudget(Number(e.target.value))}
                  disabled={isGptAudio}
                  style={{ opacity: isGptAudio ? 0.5 : 1 }}
                >
                  <option value={0}>None</option>
                  <option value={1024}>Low</option>
                  <option value={4096}>Medium</option>
                  <option value={8192}>High</option>
                </select>
              </div>
            </div>

            {isGptAudio && (
              <div className="muted" style={{ fontSize: '0.8em', padding: '8px 12px', background: 'rgba(251, 191, 36, 0.1)', borderRadius: '6px', borderLeft: '3px solid #fbbf24' }}>
                <strong style={{ color: '#fbbf24' }}>GPT Audio Mode:</strong> Spectrogram image will not be sent (audio-only analysis). Thinking mode is not available.
              </div>
            )}

            <div className="hr" />

            <div>
              <label>3) Engineer Directives</label>
              <textarea
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                disabled={!!sessionId}
                placeholder="Describe the style and direction..."
                style={{ minHeight: '80px' }}
              />
              <div className="kpi" style={{ marginTop: "10px", gap: "6px" }}>
                {SUGGESTIONS.map((s, i) => (
                  <button
                    key={i}
                    className="suggestion-pill"
                    onClick={() => !sessionId && setPrompt(s)}
                    disabled={!!sessionId}
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>

            <div className="row" style={{ gridTemplateColumns: "1fr 1fr", gap: '12px' }}>
              <button className="btn secondary" disabled={!canAct || loadingSpec} onClick={generateSpectrogram}>
                {loadingSpec ? "Rendering..." : "Preview"}
              </button>
              <button className="btn" disabled={!canAct || loadingAnalyze || !!sessionId} onClick={runAnalysis}>
                {loadingAnalyze ? (
                  <span className="loading-text">Analyzing...</span>
                ) : !!sessionId ? (
                  "Session Live"
                ) : (
                  "Start Analysis"
                )}
              </button>
            </div>

            {error && (
              <div className="card" style={{ background: "rgba(239, 68, 68, 0.1)", borderColor: "rgba(239, 68, 68, 0.2)" }}>
                <label style={{ color: "#ef4444" }}>Error Occurred</label>
                <div className="muted" style={{ color: "#fca5a5" }}>{error}</div>
              </div>
            )}
          </section>

          {/* Chat Section - now directly below settings */}
          <section className="card chat-container">
            <label>Engineer Consultation</label>
            <div className="chat-messages">
              {chatMessages.length === 0 && (
                <div className="muted" style={{ textAlign: "center", marginTop: "40px" }}>
                  Consultation inactive. Start analysis to begin chat.
                </div>
              )}

              {chatMessages.map((msg, idx) => (
                <div key={idx} className={`message ${msg.role}`}>
                  <div className="message-label">
                    {msg.role === "user" ? "Producer" : "Engineer"}
                  </div>
                  <div style={{ whiteSpace: 'pre-wrap' }}>{msg.text}</div>
                </div>
              ))}
              <div ref={chatEndRef} />
            </div>

            <div className="chat-input-wrapper">
              <input
                className="chat-input"
                type="text"
                placeholder={sessionId ? "Ask follow-up..." : "Analysis required..."}
                value={replyInput}
                onChange={e => setReplyInput(e.target.value)}
                onKeyDown={e => e.key === "Enter" && !e.shiftKey && sendReply()}
                disabled={!sessionId || loadingReply}
              />
              <button
                className="btn"
                disabled={!sessionId || loadingReply || !replyInput.trim()}
                onClick={sendReply}
              >
                {loadingReply ? "..." : "Send"}
              </button>
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
