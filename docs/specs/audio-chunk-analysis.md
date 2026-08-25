# Spec - 30 second audio chunk analysis

## Why

Long audio makes one Whisper inference slow and prevents the backend from exposing useful
segment-level evidence. The analysis should process bounded audio windows and return the
highest-risk transcript segments.

## Goal

Split normalized input audio into sequential 30 second chunks, transcribe each chunk,
classify each chunk, and aggregate the call result.

- use one chunk for audio shorter than 30 seconds
- process chunks sequentially to bound memory
- average the highest-scoring five chunks, or all chunks when fewer than five exist
- classify the call as voice_phishing when the aggregated score is at least 0.5
- return at most three highest-scoring transcript segments

## Result segment

Each returned reference segment contains:

- start: start time in seconds
- end: end time in seconds
- transcript: normalized transcript for the audio chunk
- suspicion_score: chunk-level score

## Out of scope

- overlapping audio windows
- parallel inference
- persisted transcript storage
- threshold calibration or model changes
- frontend progress animation

## Acceptance criteria

- 30 second audio is represented by one chunk.
- 65 second audio is represented by three chunks with correct time bounds.
- chunks are transcribed sequentially.
- top-five mean and top-three evidence selection are deterministic.
- short existing transcriber implementations remain compatible.
