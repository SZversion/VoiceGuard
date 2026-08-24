# Spec - Analysis progress stages

## Goal

Expose a monotonic `progress` value in the existing job status response and report six logical analysis stages:

1. `preprocessing` - audio preprocessing
2. `transcribing` - Whisper STT
3. `normalizing` - text normalization/chunking boundary
4. `classifying` - risk classification
5. `risk_search` - risk segment search boundary
6. `finalizing` - guidance and result finalization

Keep existing `status`, `stage`, result, error, cancellation, and legacy Analyzer contracts compatible.

## Progress contract

```text
queued        0
preprocessing 10
transcribing  30
normalizing   45
classifying   65
risk_search   80
finalizing    90
completed    100
```

The new logical stages are emitted at pipeline boundaries. They do not change model or classification behavior. WebSocket, SSE, frontend implementation, and persistent job storage are out of scope.

## Acceptance criteria

- A newly created job has progress 0.
- A progress-aware analyzer emits the six stages in order and progress never decreases.
- A completed job has stage `completed` and progress 100.
- An analyzer implementing only `analyze(audio)` still completes.
- Failed and cancelled jobs never advance to completed.
- Existing API fields and error contracts remain valid.
