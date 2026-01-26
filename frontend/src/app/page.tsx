"use client";

import React, { useMemo, useState, useCallback, useRef, useEffect } from "react";
import Waveform from "../components/Waveform";
import { analyzeAudio, fetchSpectrogram, sendChatMessage, startAudioProcessing, getJobStatus } from "../api";
import StemPlayer from "../components/StemPlayer";
import MidiPreview from "../components/MidiPreview";


import logoImg from "../assets/logo.png";
import Image from "next/image";

interface ChatMessage {
    role: "user" | "model";
    text: string;
    midiDownloadUrl?: string;
}

export default function Page() {
    const [file, setFile] = useState<File | null>(null);
    const [selection, setSelection] = useState({ startSec: 0, endSec: 0, durationSec: 0 });
    const [modelId, setModelId] = useState("gemini-3-pro-preview");
    const [temperature, setTemperature] = useState(0.2);
    const [thinkingBudget, setThinkingBudget] = useState(0);
    const [mode, setMode] = useState("engineer");
    const isGptAudio = modelId.startsWith("gpt-");
    const [prompt, setPrompt] = useState("");
    const ENGINEER_SUGGESTIONS = [
        "Check the overall frequency balance.",
        "Are the vocals sitting correctly in the mix?",
        "Evaluate the stereo width and mono compatibility.",
        "Is the low-end (kick/bass) well-defined?",
        "Suggest mastering moves for a commercial polish."
    ];

    const PRODUCER_SUGGESTIONS = [
        "Suggest additional layers to fill out the arrangement.",
        "What bass line would complement these chords?",
        "Recommend melodic counter-parts or harmonies.",
        "What percussion layers would add energy?",
        "Suggest synth textures or pad layers for depth."
    ];

    const SUGGESTIONS = mode === "engineer" ? ENGINEER_SUGGESTIONS : PRODUCER_SUGGESTIONS;
    const [spectrogramB64, setSpectrogramB64] = useState("");
    const [sessionId, setSessionId] = useState<string | null>(null);
    const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
    const [replyInput, setReplyInput] = useState("");
    const [error, setError] = useState("");
    const [loadingSpec, setLoadingSpec] = useState(false);
    const [loadingAnalyze, setLoadingAnalyze] = useState(false);
    const [loadingReply, setLoadingReply] = useState(false);

    // Phase 1 Expansion State
    const [jobId, setJobId] = useState<string | null>(null);
    const [jobStatus, setJobStatus] = useState<any>(null);
    const [jobLoading, setJobLoading] = useState(false);
    const [pollingActive, setPollingActive] = useState(false);
    const [profModel, setProfModel] = useState("demucs");

    const chatEndRef = useRef<HTMLDivElement>(null);


    useEffect(() => {
        chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [chatMessages]);

    const canAct = useMemo(() => {
        return !!file && selection.endSec > selection.startSec;
    }, [file, selection]);

    const onPickFile = (e: React.ChangeEvent<HTMLInputElement>) => {
        const f = e.target.files?.[0] || null;
        setFile(f);
        setChatMessages([]);
        setSessionId(null);
        setError("");
        setSpectrogramB64("");
    };

    const onSelectionChange = useCallback((sel: { startSec: number; endSec: number; durationSec: number }) => {
        setSelection(sel);
    }, []);

    const generateSpectrogram = async () => {
        if (!file || !canAct) return;

        setError("");
        setLoadingSpec(true);
        try {
            const data = await fetchSpectrogram({
                file,
                startSec: selection.startSec,
                endSec: selection.endSec,
            });
            setSpectrogramB64(data.spectrogramPngBase64);
        } catch (e: any) {
            setError(e?.message || String(e));
        } finally {
            setLoadingSpec(false);
        }
    };

    const runAnalysis = async () => {
        if (!file || !canAct) return;

        setError("");
        setLoadingAnalyze(true);
        setChatMessages([]);
        setSessionId(null);
        try {
            setChatMessages([{ role: "user", text: prompt }]);

            const data = await analyzeAudio({
                file,
                startSec: selection.startSec,
                endSec: selection.endSec,
                prompt,
                modelId,
                temperature,
                thinkingBudget,
                mode,
            });

            setSessionId(data.sessionId);
            setSpectrogramB64(data.spectrogramPngBase64);
            setChatMessages(prev => [...prev, {
                role: "model",
                text: data.advice,
                midiDownloadUrl: data.midiDownloadUrl
            }]);
        } catch (e: any) {
            setError(e?.message || String(e));
            setChatMessages(prev => prev.filter(m => m.text !== prompt));
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
            setChatMessages(prev => [...prev, {
                role: "model",
                text: data.reply,
                midiDownloadUrl: data.midiDownloadUrl
            }]);
        } catch (e: any) {
            setError(e?.message || String(e));
        } finally {
            setLoadingReply(false);
        }
    };

    // Phase 1: Professional Pipeline Handlers
    const runProfessionalPipeline = async () => {
        if (!file) return;
        setError("");
        setJobLoading(true);
        setJobStatus(null);
        try {
            const data = await startAudioProcessing(file, profModel);
            setJobId(data.job_id);
            setPollingActive(true);
        } catch (e: any) {

            setError(e?.message || "Failed to start pipeline");
        } finally {
            setJobLoading(false);
        }
    };

    useEffect(() => {
        let timer: any;
        if (pollingActive && jobId) {
            const poll = async () => {
                try {
                    const status = await getJobStatus(jobId);
                    setJobStatus(status);
                    if (status.state === "success" || status.state === "failed") {
                        setPollingActive(false);
                    }
                } catch (e) {
                    console.error("Polling error", e);
                    setPollingActive(false);
                }
            };
            poll();
            timer = setInterval(poll, 3000);
        }
        return () => clearInterval(timer);
    }, [pollingActive, jobId]);


    return (
        <div className="container">
            <header className="hero-section">
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '20px', marginBottom: '16px' }}>
                    <Image src={logoImg} alt="App Logo" className="app-logo" width={64} height={64} priority />
                    <h1>Mix Assistant AI</h1>
                </div>
            </header>
            <div className="row">
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
                <div className="stack">
                    <section className="card stack">
                        <div className="row" style={{ gridTemplateColumns: "1fr 1fr", gap: '8px', marginBottom: '12px' }}>
                            <button
                                className={`btn ${mode === "engineer" ? "" : "secondary"}`}
                                onClick={() => !sessionId && setMode("engineer")}
                                disabled={!!sessionId}
                                style={{ opacity: sessionId ? 0.6 : 1 }}
                            >
                                🎛️ Engineer
                            </button>
                            <button
                                className={`btn ${mode === "producer" ? "" : "secondary"}`}
                                onClick={() => !sessionId && setMode("producer")}
                                disabled={!!sessionId}
                                style={{ opacity: sessionId ? 0.6 : 1 }}
                            >
                                🎹 Producer
                            </button>
                        </div>
                        <div className="row" style={{ gridTemplateColumns: "1fr 1fr 1fr", gap: '12px' }}>
                            <div>
                                <label>Model</label>
                                <select value={modelId} onChange={(e) => setModelId(e.target.value)}>
                                    {/* Option 1: The Reliable Workhorses (Use these to avoid errors) */}
                                    <optgroup label="Recommended (Stable & Fast)">
                                        <option value="gemini-2.0-flash">Gemini 2.0 Flash (Best Balance)</option>
                                        <option value="gemini-2.0-flash-lite-preview-02-05">Gemini 2.0 Flash Lite (Fastest)</option>
                                    </optgroup>

                                    {/* Option 2: High Intelligence (May hit rate limits) */}
                                    <optgroup label="High Intelligence (Pro)">
                                        <option value="gemini-2.5-pro">Gemini 2.5 Pro</option>
                                        <option value="gemini-2.5-flash">Gemini 2.5 Flash</option>
                                    </optgroup>

                                    {/* Option 3: Experimental / Bleeding Edge (Expect 429 Errors) */}
                                    <optgroup label="Experimental (Low Rate Limits)">
                                        <option value="gemini-3-pro-preview">Gemini 3 Pro Preview</option>
                                        <option value="gemini-3-flash-preview">Gemini 3 Flash Preview</option>
                                        <option value="gemini-2.0-flash-exp">Gemini 2.0 Flash Experimental</option>
                                    </optgroup>

                                    {/* Option 4: Open Models (Text Focused) */}
                                    <optgroup label="Open Models">
                                        <option value="gemma-3-27b-it">Gemma 3 (27B)</option>
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

                        <div className="hr" style={{ margin: '20px 0 10px 0' }} />

                        <div className="stack" style={{ gap: '10px' }}>
                            <label style={{ color: 'var(--accent-secondary)' }}>🎹 Professional Expansion (Beta)</label>
                            <p style={{ fontSize: '0.85rem' }}>Extract deep stems and polyphonic MIDI from the full track.</p>

                            <div className="row" style={{ gridTemplateColumns: "1fr 1fr", gap: '12px', alignItems: 'center' }}>
                                <div>
                                    <label style={{ fontSize: '0.7rem' }}>Model</label>
                                    <select
                                        value={profModel}
                                        onChange={(e) => setProfModel(e.target.value)}
                                        disabled={jobLoading || pollingActive}
                                        style={{ width: '100%' }}
                                    >
                                        <option value="demucs">Demucs v4 (Balanced)</option>
                                        <option value="umx">Open-Unmix (Clean Vocals)</option>
                                    </select>
                                </div>
                                <button
                                    className="btn secondary"
                                    style={{ borderColor: 'var(--accent-secondary)', color: 'var(--accent-secondary)', marginTop: '20px' }}
                                    disabled={!file || jobLoading || pollingActive}
                                    onClick={runProfessionalPipeline}
                                >
                                    {jobLoading ? "..." : pollingActive ? "Processing..." : "Start Deep Extraction"}
                                </button>
                            </div>


                            {jobStatus && (
                                <div className="card" style={{ padding: '12px', background: 'rgba(45, 212, 191, 0.05)', borderColor: 'var(--accent-secondary)' }}>
                                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                                        <span style={{ fontSize: '0.8rem', fontWeight: 600 }}>Status: {jobStatus.state.toUpperCase()}</span>
                                        <span style={{ fontSize: '0.8rem' }}>{jobStatus.progress}%</span>
                                    </div>
                                    <div style={{ height: '4px', background: 'rgba(255,255,255,0.1)', borderRadius: '2px', overflow: 'hidden' }}>
                                        <div style={{ height: '100%', width: `${jobStatus.progress}%`, background: 'var(--accent-secondary)', transition: 'width 0.5s ease' }} />
                                    </div>
                                    <div className="muted" style={{ marginTop: '8px', fontSize: '0.75rem' }}>{jobStatus.message}</div>

                                    {jobStatus.state === "success" && (
                                        <div className="stack" style={{ marginTop: '20px', gap: '24px' }}>
                                            <StemPlayer
                                                stems={jobStatus.artifacts.stems.map((s: string) => ({
                                                    name: s.replace(".wav", ""),
                                                    url: `http://localhost:8000/static/jobs/${jobId}/stems/${s}`
                                                }))}
                                            />

                                            <MidiPreview
                                                jobId={jobId!}
                                                midiFiles={jobStatus.artifacts.midi}
                                                validationReport={jobStatus.validation_report}
                                            />

                                            <div className="card" style={{ background: 'rgba(45, 212, 191, 0.1)', borderColor: 'var(--accent-secondary)' }}>
                                                <div className="row" style={{ justifyContent: 'space-between', alignItems: 'center' }}>
                                                    <div className="stack" style={{ gap: '4px' }}>
                                                        <label style={{ color: 'var(--accent-secondary)' }}>🏁 DAW Ready: REAPER Project</label>
                                                        <p style={{ fontSize: '0.75rem' }}>Full session with stems and MIDI tracks mapped and ready.</p>
                                                    </div>
                                                    <a
                                                        href={`http://localhost:8000/static/jobs/${jobId}/${jobStatus.artifacts.project[0]}`}
                                                        download
                                                        className="btn"
                                                        style={{ background: 'var(--accent-secondary)', color: '#000' }}
                                                    >
                                                        EXPORT TO REAPER (.RPP)
                                                    </a>
                                                </div>
                                            </div>

                                            <div className="stack" style={{ gap: '8px' }}>
                                                <label style={{ fontSize: '0.7rem' }}>Individual Raw Artifacts</label>
                                                <div className="row" style={{ gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
                                                    <div className="stack" style={{ gap: '4px' }}>
                                                        <span style={{ fontSize: '0.65rem' }}>Stems</span>
                                                        {jobStatus.artifacts.stems.map((s: string) => (
                                                            <a key={s} href={`http://localhost:8000/static/jobs/${jobId}/stems/${s}`} download className="pill" style={{ textAlign: 'center', textDecoration: 'none', fontSize: '10px' }}>{s}</a>
                                                        ))}
                                                    </div>
                                                    <div className="stack" style={{ gap: '4px' }}>
                                                        <span style={{ fontSize: '0.65rem' }}>MIDI</span>
                                                        {jobStatus.artifacts.midi.map((m: string) => (
                                                            <a key={m} href={`http://localhost:8000/static/jobs/${jobId}/midi/${m}`} download className="pill" style={{ textAlign: 'center', textDecoration: 'none', background: 'rgba(129, 140, 248, 0.1)', fontSize: '10px' }}>{m}</a>
                                                        ))}
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    )}

                                </div>
                            )}
                        </div>

                        {error && (
                            <div className="card" style={{ background: "rgba(239, 68, 68, 0.1)", borderColor: "rgba(239, 68, 68, 0.2)" }}>
                                <label style={{ color: "#ef4444" }}>Error Occurred</label>
                                <div className="muted" style={{ color: "#fca5a5" }}>{error}</div>
                            </div>
                        )}
                    </section>
                    <section className="card chat-container">
                        <label>{mode === "engineer" ? "Engineer Consultation" : "Producer Session"}</label>
                        <div className="chat-messages">
                            {chatMessages.length === 0 && (
                                <div className="muted" style={{ textAlign: "center", marginTop: "40px" }}>
                                    Consultation inactive. Start analysis to begin chat.
                                </div>
                            )}
                            {chatMessages.map((msg, idx) => (
                                <div key={idx} className={`message ${msg.role}`}>
                                    <div className="message-label">
                                        {msg.role === "user" ? "You" : (mode === "engineer" ? "Engineer" : "Producer")}
                                    </div>
                                    <div style={{ whiteSpace: 'pre-wrap' }}>{msg.text}</div>
                                    {msg.midiDownloadUrl && (
                                        <div className="midi-attachment">
                                            <div className="midi-header">
                                                <span className="midi-icon">🎹</span>
                                                <span className="midi-title">MIDI File Generated</span>
                                            </div>
                                            <a
                                                href={`http://localhost:8000${msg.midiDownloadUrl}`}
                                                download
                                                className="btn midi-download-btn"
                                            >
                                                Download .MID File
                                            </a>
                                        </div>
                                    )}
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