# Gemini Audio Engineer – Phase 1 Expansion Plan (Repo-Accurate)

## Objective
Extend the existing Gemini Audio Engineer backend to support deep stem separation, MIDI generation, and long‑running audio jobs without restructuring the repository. Evolve **gemini-audio-engineer-react** from a mix advice assistant into a **professional audio processing system** that can:

- Perform **deep stem separation**
- Generate **structured MIDI outputs**
- Support **long‑running audio jobs**
- Remain compatible with:
    - existing FastAPI backend
    - existing Gemini / OpenAI logic
    - existing Next.js frontend

This phase focuses on **audio processing + MIDI, not REAPER yet**.

## Current Backend Structure (As‑Is)
backend/
├── .env
├── .env.example
├── app.py
├── audio_processor.py
├── check_models.py
├── gemini_client.py
├── midi_engine.py
├── openai_client.py
├── prompts.py
└── requirements.txt

# Key observations:
- app.py
    → FastAPI entrypoint and routing
- audio_processor.py
    → Handles trimming, spectrograms, FFmpeg interaction
    → This is where DSP logic already lives
- midi_engine.py
    → MIDI utilities already exist
    → Currently lightweight / limited
- gemini_client.py & openai_client.py
    → AI reasoning layer (keep untouched)

There is no job system, no stem system, no MIDI pipeline yet.

## Current Frontend Structure (As‑Is)
frontend/
├── src/
│   ├── app/
│   ├── assets/
│   ├── components/
│   ├── api.ts
│   └── next-env-custom.d.ts
├── next-env.d.ts
├── next.config.mjs
├── package.json
└── tsconfig.json

# Key observations:
- Audio upload + region selection already works
- Frontend talks to FastAPI via api.ts
- No concept of:
    - job status
    - downloadable stems
    - MIDI outputs

## New Concepts Introduced
- File‑system based audio jobs
- Deep stem separation
- Structured MIDI outputs
- Long‑running background processing

## Audio Job Layout
backend/audio_jobs/
└── <job_id>/
    ├── input.wav
    ├── status.json
    ├── stems/
    └── midi/

## Audio Stems (Phase 1)
- vocals_lead.wav
- vocals_backing.wav
- bass.wav
- guitars.wav
- keys_synth.wav
- harmony.wav
- kick.wav
- snare.wav
- hats.wav

# How they are derived
- Demucs → core stems (vocals, drums, bass, other)
- DSP refinement:
    - vocals → lead / backing
    - drums → kick / snare / hats
    - other → guitars / keys / harmony
All DSP logic lives inside or alongside audio_processor.py

## MIDI Outputs (Phase 1)
- melody_lead.mid
- bass.mid
- drums.mid
- harmony.mid
- guitars.mid
- keys_synth.mid

## Source mapping
-----------------------------------------
|MIDI File	      |  Source Audio        |
|-----------------|----------------------|
|melody_lead.mid  |  vocals_lead.wav     |
|bass.mid	      |  bass.wav            |
|drums.mid	      |  kick / snare / hats |
|harmony.mid	  |  keys + guitars      |
|guitars.mid	  |  guitars.wav         |
|keys_synth.mid	  |  keys_synth.wav      |
-----------------------------------------

MIDI logic extends midi_engine.py, not replaced.

## Processing Flow
1. Upload audio
2. Create job directory
3. Run Demucs
4. Split vocals
5. Split drums
6. Classify instruments
7. Generate MIDI
8. Update job status

## Role of Gemini / OpenAI
- Musical validation
- Arrangement and mix feedback
- No raw DSP processing

## API Surface Changes (Backend)
# New endpoint (example)
POST /process

# Responsibilities:
    - Accept uploaded audio
    - Create job directory
    - Start processing pipeline
    - Return job_id

# Existing endpoints remain untouched
# Your current:
- health
- analysis
- preview
continue to work.

## Frontend Changes (Later Phase)
# Frontend will later gain:

- job progress polling
- stem download buttons
- MIDI download buttons

Not implemented yet.

## Where pipeline.py Fits
# We do not introduce a new service layer.
# Instead:
- audio_processor.py becomes:
    - low-level DSP utilities
- NEW audio_pipeline.py:
    - orchestrates the entire process
    - updates job status
    - calls stem + MIDI functions
This keeps responsibilities clean.

## Phase 1 Deliverables
# By the end of Phase 1, the system will:

- Accept full-length audio
- Generate deep stems
- Generate structured MIDI
- Support long-running jobs
- Feed real musical artifacts into Gemini

## Phase 1 Result
A production‑ready audio analysis and transformation backend that feeds high‑quality stems and MIDI into AI reasoning.