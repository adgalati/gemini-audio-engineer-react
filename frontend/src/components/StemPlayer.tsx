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

    useEffect(() => {
        // Initialize WaveSurfer for each stem
        stems.forEach((stem, index) => {
            if (!containersRef.current[index]) return;

            const ws = WaveSurfer.create({
                container: containersRef.current[index]!,
                height: 60,
                progressColor: "#818cf8",
                waveColor: "#475569",
                barWidth: 2,
                cursorColor: "#2dd4bf",
                normalize: true,
            });

            ws.load(stem.url);
            wsInstances.current[index] = ws;

            ws.on("ready", () => {
                setIsReady(prev => {
                    const next = [...prev];
                    next[index] = true;
                    return next;
                });
            });

            // Sync playback across all instances
            ws.on("interaction", () => {
                const time = ws.getCurrentTime();
                wsInstances.current.forEach(inst => inst?.seekTo(time / inst.getDuration()));
            });
        });

        return () => {
            wsInstances.current.forEach(inst => inst?.destroy());
            wsInstances.current = [];
        };
    }, [stems]);

    const togglePlay = () => {
        const nextPlaying = !isPlaying;
        setIsPlaying(nextPlaying);
        wsInstances.current.forEach(inst => nextPlaying ? inst?.play() : inst?.pause());
    };

    const toggleMute = (index: number) => {
        const nextMutes = [...mutes];
        nextMutes[index] = !nextMutes[index];
        setMutes(nextMutes);
        wsInstances.current[index]?.setMuted(nextMutes[index]);
    };

    const toggleSolo = (index: number) => {
        const nextSolos = [...solos];
        nextSolos[index] = !nextSolos[index];
        setSolos(nextSolos);

        // If any solo is active, only soloed tracks play.
        // If no solos active, all non-muted tracks play.
        const isAnySolo = nextSolos.some(s => s);
        wsInstances.current.forEach((inst, i) => {
            if (isAnySolo) {
                inst?.setVolume(nextSolos[i] ? volumes[i] : 0);
            } else {
                inst?.setVolume(mutes[i] ? 0 : volumes[i]);
            }
        });
    };

    const onVolumeChange = (index: number, val: number) => {
        const nextVolumes = [...volumes];
        nextVolumes[index] = val;
        setVolumes(nextVolumes);
        if (!mutes[index] && (!solos.some(s => s) || solos[index])) {
            wsInstances.current[index]?.setVolume(val);
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
                        <div ref={el => containersRef.current[i] = el} />
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
