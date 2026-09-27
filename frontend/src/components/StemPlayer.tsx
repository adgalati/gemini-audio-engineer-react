"use client";

import React, { useEffect, useRef, useState, useCallback } from "react";
import WaveSurfer from "wavesurfer.js";

interface Stem {
    name: string;
    url: string;
}

interface StemPlayerProps {
    stems: Stem[];
}

export default function StemPlayer({ stems }: StemPlayerProps) {
    const containersRef = useRef<(HTMLDivElement | null)[]>([]);
    const wsInstances = useRef<(WaveSurfer | null)[]>([]);
    const [isPlaying, setIsPlaying] = useState(false);
    const [isReady, setIsReady] = useState<boolean[]>(new Array(stems.length).fill(false));
    const [volumes, setVolumes] = useState<number[]>(new Array(stems.length).fill(1));
    const [mutes, setMutes] = useState<boolean[]>(new Array(stems.length).fill(false));
    const [solos, setSolos] = useState<boolean[]>(new Array(stems.length).fill(false));

    const stemsKey = stems.map(s => `${s.name}:${s.url}`).join("|");

    useEffect(() => {
        let isCancelled = false;

        // Reset state arrays when stems count or list changes
        setIsReady(new Array(stems.length).fill(false));
        setVolumes(new Array(stems.length).fill(1));
        setMutes(new Array(stems.length).fill(false));
        setSolos(new Array(stems.length).fill(false));
        setIsPlaying(false);

        // Destroy previous instances
        wsInstances.current.forEach(inst => {
            try {
                inst?.destroy();
            } catch (e) {}
        });
        wsInstances.current = new Array(stems.length).fill(null);

        // Initialize WaveSurfer for each stem
        stems.forEach((stem, index) => {
            const container = containersRef.current[index];
            if (!container) return;

            try {
                container.innerHTML = "";
                const ws = WaveSurfer.create({
                    container,
                    height: 60,
                    progressColor: "#818cf8",
                    waveColor: "#475569",
                    barWidth: 2,
                    cursorColor: "#2dd4bf",
                    normalize: true,
                });

                wsInstances.current[index] = ws;

                ws.on("ready", () => {
                    if (isCancelled) return;
                    setIsReady(prev => {
                        const next = [...prev];
                        next[index] = true;
                        return next;
                    });
                });

                ws.on("error", (err: any) => {
                    if (err?.name === "AbortError" || String(err).includes("aborted")) {
                        return;
                    }
                    console.warn(`WaveSurfer Error for stem ${stem.name}:`, err);
                });

                // Sync playback across all instances
                ws.on("interaction", () => {
                    if (isCancelled) return;
                    const dur = ws.getDuration();
                    if (dur > 0) {
                        const time = ws.getCurrentTime();
                        const progress = time / dur;
                        wsInstances.current.forEach(inst => {
                            if (inst && inst !== ws) {
                                try {
                                    inst.seekTo(progress);
                                } catch (e) {}
                            }
                        });
                    }
                });

                const loadPromise = ws.load(stem.url);
                if (loadPromise && typeof (loadPromise as any).catch === "function") {
                    (loadPromise as any).catch((err: any) => {
                        if (err?.name === "AbortError" || String(err).includes("aborted")) {
                            return;
                        }
                        console.warn(`WaveSurfer load error for stem ${stem.name}:`, err);
                    });
                }
            } catch (e: any) {
                if (e?.name !== "AbortError" && !String(e).includes("aborted")) {
                    console.warn(`WaveSurfer init exception for stem ${stem.name}:`, e);
                }
            }
        });

        return () => {
            isCancelled = true;
            wsInstances.current.forEach(inst => {
                try {
                    inst?.destroy();
                } catch (e) {}
            });
            wsInstances.current = [];
        };
    }, [stemsKey]);

    const togglePlay = () => {
        const nextPlaying = !isPlaying;
        setIsPlaying(nextPlaying);
        wsInstances.current.forEach(inst => {
            if (inst) {
                try {
                    if (nextPlaying) {
                        inst.play();
                    } else {
                        inst.pause();
                    }
                } catch (e) {}
            }
        });
    };

    const toggleMute = (index: number) => {
        const nextMutes = [...mutes];
        nextMutes[index] = !nextMutes[index];
        setMutes(nextMutes);
        try {
            wsInstances.current[index]?.setMuted(nextMutes[index]);
        } catch (e) {}
    };

    const toggleSolo = (index: number) => {
        const nextSolos = [...solos];
        nextSolos[index] = !nextSolos[index];
        setSolos(nextSolos);

        // If any solo is active, only soloed tracks play.
        // If no solos active, all non-muted tracks play.
        const isAnySolo = nextSolos.some(s => s);
        wsInstances.current.forEach((inst, i) => {
            if (!inst) return;
            try {
                if (isAnySolo) {
                    inst.setVolume(nextSolos[i] ? volumes[i] : 0);
                } else {
                    inst.setVolume(mutes[i] ? 0 : volumes[i]);
                }
            } catch (e) {}
        });
    };

    const onVolumeChange = (index: number, val: number) => {
        const nextVolumes = [...volumes];
        nextVolumes[index] = val;
        setVolumes(nextVolumes);
        if (!mutes[index] && (!solos.some(s => s) || solos[index])) {
            try {
                wsInstances.current[index]?.setVolume(val);
            } catch (e) {}
        }
    };

    const allReady = isReady.every(r => r);

    return (
        <div className="card stack" style={{ background: 'rgba(15, 23, 42, 0.5)', padding: '20px' }}>
            <div className="row" style={{ justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                <label style={{ color: 'var(--accent-secondary)' }}>🎚️ Multi-Track Stem Mixer</label>
                <button className="btn" disabled={!allReady} onClick={togglePlay}>
                    {isPlaying ? "⏹️ STOP" : "▶️ PLAY ALL"}
                </button>
            </div>

            <div className="stack" style={{ gap: '12px' }}>
                {stems.map((stem, i) => (
                    <div key={stem.name} className="row" style={{ gridTemplateColumns: '120px 1fr 180px', gap: '15px', alignItems: 'center', padding: '8px', background: 'rgba(255,255,255,0.03)', borderRadius: '8px' }}>
                        <div style={{ fontSize: '0.75rem', fontWeight: 600, textTransform: 'uppercase' }}>{stem.name}</div>
                        <div ref={el => { containersRef.current[i] = el; }} />
                        <div className="row" style={{ gap: '8px' }}>
                            <button
                                className={`pill ${solos[i] ? 'active' : ''}`}
                                onClick={() => toggleSolo(i)}
                                style={{ background: solos[i] ? '#fbbf24' : 'transparent', color: solos[i] ? '#000' : '#fff' }}
                            >S</button>
                            <button
                                className={`pill ${mutes[i] ? 'active' : ''}`}
                                onClick={() => toggleMute(i)}
                                style={{ background: mutes[i] ? '#ef4444' : 'transparent' }}
                            >M</button>
                            <input
                                type="range"
                                min="0" max="1" step="0.01"
                                value={volumes[i]}
                                onChange={(e) => onVolumeChange(i, parseFloat(e.target.value))}
                                style={{ width: '80px' }}
                            />
                        </div>
                    </div>
                ))}
            </div>
            {!allReady && <div className="muted" style={{ textAlign: 'center', marginTop: '10px' }}>Loading Studio Stems...</div>}
        </div>
    );
}
