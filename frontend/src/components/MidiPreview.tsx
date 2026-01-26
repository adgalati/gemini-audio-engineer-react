"use client";

import React, { useEffect, useRef } from "react";

interface MidiPreviewProps {
    jobId: string;
    midiFiles: string[];
    validationReport?: string;
}

export default function MidiPreview({ jobId, midiFiles, validationReport }: MidiPreviewProps) {
    const canvasRef = useRef<HTMLCanvasElement>(null);

    // For now, this is a placeholder visual. 
    // In a full implementation, we would parse the MIDI file bytes and draw notes.
    useEffect(() => {
        const ctx = canvasRef.current?.getContext("2d");
        if (!ctx) return;

        const w = ctx.canvas.width;
        const h = ctx.canvas.height;
        ctx.clearRect(0, 0, w, h);

        // Draw some "fake" piano roll nodes to represent data
        ctx.fillStyle = "rgba(45, 212, 191, 0.3)";
        for (let i = 0; i < 50; i++) {
            const x = Math.random() * w;
            const y = Math.random() * h;
            const rw = Math.random() * 50 + 10;
            ctx.fillRect(x, y, rw, 8);
        }
    }, [midiFiles]);

    return (
        <div className="card stack" style={{ background: 'rgba(15, 23, 42, 0.5)', padding: '20px' }}>
            <label style={{ color: 'var(--accent-secondary)' }}>🎹 MIDI Structure Preview</label>

            <div style={{ position: 'relative', height: '200px', background: 'rgba(0,0,0,0.2)', borderRadius: '8px', overflow: 'hidden', border: '1px solid rgba(255,255,255,0.05)' }}>
                <canvas ref={canvasRef} width={800} height={200} style={{ width: '100%', height: '100%' }} />
                <div style={{ position: 'absolute', top: '10px', left: '10px', display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                    {midiFiles.map(m => (
                        <span key={m} className="pill" style={{ background: 'rgba(129, 140, 248, 0.2)', fontSize: '0.65rem' }}>{m}</span>
                    ))}
                </div>
            </div>

            {validationReport && (
                <div className="stack" style={{ marginTop: '16px', gap: '8px' }}>
                    <label style={{ fontSize: '0.7rem', color: '#fbbf24' }}>📋 Gemini Musical Validation Report</label>
                    <div className="muted" style={{
                        fontSize: '0.8rem',
                        padding: '12px',
                        background: 'rgba(251, 191, 36, 0.05)',
                        borderRadius: '6px',
                        borderLeft: '3px solid #fbbf24',
                        whiteSpace: 'pre-wrap',
                        maxHeight: '150px',
                        overflowY: 'auto'
                    }}>
                        {validationReport}
                    </div>
                </div>
            )}
        </div>
    );
}
