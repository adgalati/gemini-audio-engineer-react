import React, { useEffect, useMemo, useRef, useState } from "react";
import WaveSurfer from "wavesurfer.js";
import RegionsPlugin from "wavesurfer.js/dist/plugins/regions.esm.js";

/**
 * Waveform player + region selection (no backend calls).
 * - Loads a local File via object URL
 * - Creates a draggable + resizable region
 * - Emits selection changes up to parent
 */
export default function Waveform({ file, onSelectionChange }) {
  const containerRef = useRef(null);
  const wsRef = useRef(null);
  const regionRef = useRef(null);

  const [isReady, setIsReady] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const [duration, setDuration] = useState(0);

  const url = useMemo(() => (file ? URL.createObjectURL(file) : null), [file]);

  useEffect(() => {
    return () => {
      if (url) URL.revokeObjectURL(url);
    };
  }, [url]);

  useEffect(() => {
    if (!containerRef.current || !url) return;

    // Cleanup any previous instance
    if (wsRef.current) {
      wsRef.current.destroy();
      wsRef.current = null;
      regionRef.current = null;
    }

    const ws = WaveSurfer.create({
      container: containerRef.current,
      height: 120,
      normalize: true,
      backend: "WebAudio",
      plugins: [
        RegionsPlugin.create(),
      ],
    });

    wsRef.current = ws;

    ws.on("ready", () => {
      setIsReady(true);
      const dur = ws.getDuration();
      setDuration(dur);

      // Default region: first 30s (or full duration if shorter)
      const start = 0;
      const end = Math.min(dur, 30);

      const r = ws.addRegion({
        start,
        end,
        drag: true,
        resize: true,
      });

      regionRef.current = r;
      onSelectionChange?.({ startSec: start, endSec: end, durationSec: dur });
    });

    ws.on("play", () => setIsPlaying(true));
    ws.on("pause", () => setIsPlaying(false));
    ws.on("finish", () => setIsPlaying(false));

    ws.on("region-updated", (region) => {
      onSelectionChange?.({
        startSec: region.start,
        endSec: region.end,
        durationSec: ws.getDuration(),
      });
    });

    ws.load(url);

    return () => {
      ws.destroy();
    };
  }, [url, onSelectionChange]);

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
        <span className="pill">Duration: {duration.toFixed(2)}s</span>
        <span className="pill">Drag/resize the region to set selection</span>
      </div>
      <div className="muted">
        Tip: if you don’t see a selection box, wait for the waveform to finish loading.
      </div>
    </div>
  );
}
