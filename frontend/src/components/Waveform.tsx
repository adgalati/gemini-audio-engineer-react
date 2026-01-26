"use client";

import React, { useEffect, useMemo, useRef, useState } from "react";
import WaveSurfer from "wavesurfer.js";
import RegionsPlugin from "wavesurfer.js/dist/plugins/regions.esm.js";

/**
 * Waveform player + region selection (no backend calls).
 * - Loads a local File via object URL
 * - Creates a draggable + resizable region
 * - Emits selection changes up to parent
 */
interface WaveformProps {
  file: File;
  onSelectionChange?: (selection: { startSec: number; endSec: number; durationSec: number }) => void;
}

export default function Waveform({ file, onSelectionChange }: WaveformProps) {

  const containerRef = useRef<HTMLDivElement>(null);
  const wsRef = useRef<WaveSurfer | null>(null);
  const regionRef = useRef<any>(null); // RegionsPlugin doesn't always export a 'SingleRegion' type easily
  const [isReady, setIsReady] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const [duration, setDuration] = useState(0);

  useEffect(() => {
    if (!containerRef.current || !file) return;

    // 1. Create Object URL locally within the effect
    const audioUrl = URL.createObjectURL(file);

    // Cleanup any previous instance
    if (wsRef.current) {
      wsRef.current.destroy();
      wsRef.current = null;
      regionRef.current = null;
    }

    // Create the Regions plugin instance first
    const wsRegions = RegionsPlugin.create();

    // Create WaveSurfer
    const ws = WaveSurfer.create({
      container: containerRef.current,
      height: 120,
      normalize: true,
      waveColor: "#475569",
      progressColor: "#818cf8",
      cursorColor: "#2dd4bf",
      barWidth: 2,
      barGap: 3,
      barRadius: 3,
      plugins: [wsRegions],
    });

    wsRef.current = ws;

    ws.on("ready", () => {
      // Guard: if destroyed in the meantime
      if (!wsRef.current) return;

      setIsReady(true);
      const dur = ws.getDuration();
      setDuration(dur);

      // Default region: full duration (capped at 10 minutes for safety)
      const start = 0;
      const end = Math.min(dur, 600);

      // Add region via the plugin instance
      const r = wsRegions.addRegion({
        start,
        end,
        drag: true,
        resize: true,
        color: "rgba(129, 140, 248, 0.15)",
      });

      regionRef.current = r;
      onSelectionChange?.({ startSec: start, endSec: end, durationSec: dur });
    });

    ws.on("play", () => setIsPlaying(true));
    ws.on("pause", () => setIsPlaying(false));
    ws.on("finish", () => setIsPlaying(false));

    // Listen to region events on the plugin instance
    wsRegions.on("region-updated", (region: any) => {
      onSelectionChange?.({
        startSec: region.start,
        endSec: region.end,
        durationSec: ws.getDuration(),
      });
    });

    // Ensure we capture the final state after drag ends
    wsRegions.on("region-out", (region: any) => {
      onSelectionChange?.({
        startSec: region.start,
        endSec: region.end,
        durationSec: ws.getDuration(),
      });
    });

    ws.load(audioUrl);

    return () => {
      // Cleanup: Destroy WS first, then revoke the URL
      if (ws) ws.destroy();
      URL.revokeObjectURL(audioUrl);
    };
  }, [file, onSelectionChange]);

  const toggle = () => {
    if (!wsRef.current) return;
    wsRef.current.playPause();
  };

  const playRegion = () => {
    const ws = wsRef.current;
    const region = regionRef.current;
    if (!ws || !region) return;
    ws.play(region.start, region.end);
  };

  const selectFull = () => {
    const ws = wsRef.current;
    const region = regionRef.current;
    if (!ws || !region) return;
    const dur = ws.getDuration();
    region.setOptions({ start: 0, end: dur });
    onSelectionChange?.({ startSec: 0, endSec: dur, durationSec: dur });
  };

  return (
    <div className="stack">
      <div ref={containerRef} className="card" />
      <div className="kpi">
        <button className="btn secondary" disabled={!isReady} onClick={toggle}>
          {isPlaying ? "Pause" : "Play/Pause"}
        </button>
        <button className="btn secondary" disabled={!isReady} onClick={playRegion}>
          Play Selection
        </button>
        <button className="btn secondary" disabled={!isReady} onClick={selectFull}>
          Select Full
        </button>
        <span className="pill">Duration: {duration.toFixed(2)}s</span>
        <span className="pill">Drag/resize region to select</span>
      </div>
      <div className="muted">
        Tip: Default selection is the full song (up to 10 min).
      </div>
    </div>
  );
}
