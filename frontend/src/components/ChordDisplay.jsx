import React, { useState } from "react";

/**
 * ChordDisplay - Visualizes detected chord progression as a horizontal timeline
 * with BPM adjustment and editable chord cards
 */
export default function ChordDisplay({ bpm, chords, onBpmChange, onChordsChange }) {
    const [showBpmMenu, setShowBpmMenu] = useState(false);
    const [editingIdx, setEditingIdx] = useState(null);
    const [editChord, setEditChord] = useState("");
    const [editBeats, setEditBeats] = useState("");

    if (!chords || chords.length === 0) {
        return null;
    }

    // Color palette for different chord types
    const getChordColor = (chord) => {
        if (chord === "N" || chord === "NC") return "var(--text-dim)";
        if (chord.includes("m7") || chord.includes("min7")) return "#f472b6"; // pink
        if (chord.includes("m") || chord.includes("min")) return "#a78bfa"; // purple
        if (chord.includes("7") || chord.includes("dom")) return "#fbbf24"; // amber
        if (chord.includes("dim")) return "#ef4444"; // red
        if (chord.includes("aug")) return "#f97316"; // orange
        return "#2dd4bf"; // teal for major
    };

    const handleBpmSelect = (newBpm) => {
        setShowBpmMenu(false);
        if (onBpmChange) {
            onBpmChange(newBpm);
        }
    };

    const startEditing = (idx, chord) => {
        setEditingIdx(idx);
        setEditChord(chord.chord);
        setEditBeats(Math.round(chord.duration_beats).toString());
    };

    const saveEdit = () => {
        if (editingIdx === null || !onChordsChange) return;

        const newBeats = parseInt(editBeats, 10) || chords[editingIdx].duration_beats;
        const beatDiff = newBeats - chords[editingIdx].duration_beats;

        const updatedChords = chords.map((c, idx) => {
            if (idx === editingIdx) {
                return {
                    ...c,
                    chord: editChord.trim() || c.chord,
                    duration_beats: newBeats,
                };
            }
            // Adjust subsequent chord start times
            if (idx > editingIdx) {
                return {
                    ...c,
                    start_beat: c.start_beat + beatDiff,
                };
            }
            return c;
        });

        onChordsChange(updatedChords);
        setEditingIdx(null);
    };

    const deleteChord = (idx) => {
        if (!onChordsChange) return;
        const updatedChords = chords.filter((_, i) => i !== idx);
        onChordsChange(updatedChords);
        setEditingIdx(null);
    };

    // BPM options: half, original, double
    const bpmOptions = bpm ? [
        { label: `${Math.round(bpm / 2)} (½×)`, value: bpm / 2 },
        { label: `${Math.round(bpm)} (1×)`, value: bpm },
        { label: `${Math.round(bpm * 2)} (2×)`, value: bpm * 2 },
    ] : [];

    return (
        <div className="chord-display">
            <div className="chord-header">
                <span className="chord-label">Detected Chords <span className="muted">(click to edit)</span></span>
                {bpm && (
                    <div className="bpm-selector">
                        <button
                            className="bpm-badge bpm-clickable"
                            onClick={() => setShowBpmMenu(!showBpmMenu)}
                        >
                            {Math.round(bpm)} BPM ▾
                        </button>
                        {showBpmMenu && (
                            <div className="bpm-dropdown">
                                {bpmOptions.map((opt, idx) => (
                                    <button
                                        key={idx}
                                        className={`bpm-option ${opt.value === bpm ? 'active' : ''}`}
                                        onClick={() => handleBpmSelect(opt.value)}
                                    >
                                        {opt.label}
                                    </button>
                                ))}
                            </div>
                        )}
                    </div>
                )}
            </div>
            <div className="chord-timeline">
                {chords.map((chord, idx) => {
                    const bgColor = getChordColor(chord.chord);
                    const isEditing = editingIdx === idx;
                    const roundedBeats = Math.round(chord.duration_beats);

                    if (isEditing) {
                        return (
                            <div key={idx} className="chord-block chord-editing" style={{ backgroundColor: bgColor }}>
                                <input
                                    type="text"
                                    className="chord-edit-input"
                                    value={editChord}
                                    onChange={(e) => setEditChord(e.target.value)}
                                    placeholder="Chord"
                                    autoFocus
                                />
                                <div className="chord-edit-beats">
                                    <input
                                        type="number"
                                        className="chord-edit-input chord-edit-beats-input"
                                        value={editBeats}
                                        onChange={(e) => setEditBeats(e.target.value)}
                                        min="1"
                                        max="32"
                                    />
                                    <span>b</span>
                                </div>
                                <div className="chord-edit-actions">
                                    <button className="chord-edit-btn save" onClick={saveEdit}>✓</button>
                                    <button className="chord-edit-btn delete" onClick={() => deleteChord(idx)}>✕</button>
                                </div>
                            </div>
                        );
                    }

                    return (
                        <div
                            key={idx}
                            className="chord-block"
                            style={{ backgroundColor: bgColor }}
                            title={`${chord.chord}: beats ${chord.start_beat.toFixed(1)}-${(chord.start_beat + chord.duration_beats).toFixed(1)} (click to edit)`}
                            onClick={() => startEditing(idx, chord)}
                        >
                            <span className="chord-name">{chord.chord}</span>
                            <span className="chord-beats">{roundedBeats}b</span>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}
