# Backend API Scaffold Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a testable FastAPI MVP scaffold for asynchronous Korean voice-analysis jobs with model readiness, validation, cancellation, and cleanup contracts.

**Architecture:** Keep HTTP routes, job lifecycle, analysis adapters, and infrastructure concerns separate. Use an in-memory registry and background runner for the single-instance MVP; inject a fake analyzer in tests and reserve Faster-Whisper/ONNX adapters for production wiring.

**Tech Stack:** Python 3.11, FastAPI, Pydantic, pytest, httpx, python-multipart, ffprobe/FFmpeg adapter boundary.

**Spec:** `docs/specs/backend-api.md`

## Global Constraints

- API paths use `/api/v1`.
- Audio processing target is mono / 16kHz / 16-bit signed PCM.
- Audio chunks are 30 seconds with 10% overlap.
- No audio, transcript, intermediate result, or credential is committed or logged.
- In-memory state is an MVP constraint; no database or external queue.
- Model-unready analysis returns `503 MODEL.NOT_READY` while health remains available.

---

### Task 1: Project configuration and API contracts

**Files:**
- Create: `app/__init__.py`, `app/api/__init__.py`, `app/api/routes/__init__.py`, `app/analysis/__init__.py`, `app/jobs/__init__.py`, `app/core/__init__.py`
- Create: `app/core/config.py`, `app/api/schemas.py`, `app/api/errors.py`
- Modify: `requirements.txt`, `.env.example`
- Test: `tests/api/test_schemas.py`, `tests/core/test_config.py`

**Interfaces:**
- `Settings.from_env() -> Settings`
- `JobStatus`, `JobStage`, `ModelStatus` enums
- `ErrorResponse` and response models for health, model status, job creation, job status, and analysis result

- [ ] **Step 1: Write failing tests** for enum values, default configuration, and model-unready error serialization.
- [ ] **Step 2: Run `pytest tests/api/test_schemas.py tests/core/test_config.py -q` and confirm failure because modules do not exist.**
- [ ] **Step 3: Implement minimal settings and Pydantic contracts.**
- [ ] **Step 4: Re-run the focused tests and confirm they pass.**
- [ ] **Step 5: Commit `feat: define backend api contracts`.**

### Task 2: Model status and health routes

**Files:**
- Create: `app/api/main.py`, `app/api/routes/health.py`
- Create: `app/analysis/stt.py`, `app/analysis/classifier.py`
- Test: `tests/api/test_health.py`

**Interfaces:**
- `ModelManager.status() -> ModelStatusResponse`
- `GET /api/v1/health -> HealthResponse`
- `GET /api/v1/model-status -> ModelStatusResponse`

- [ ] **Step 1: Write failing tests** proving health is `200` without model files, model status reports `loading`/`error`, and ready requires both adapters.
- [ ] **Step 2: Run `pytest tests/api/test_health.py -q` and confirm the expected missing-route failure.**
- [ ] **Step 3: Implement lazy model manager and routes without loading real weights at import time.**
- [ ] **Step 4: Re-run the focused tests and confirm they pass.**
- [ ] **Step 5: Commit `feat: add health and model status endpoints`.**

### Task 3: Input validation, security limits, and job registry

**Files:**
- Create: `app/analysis/audio.py`, `app/core/security.py`, `app/core/rate_limit.py`
- Create: `app/jobs/registry.py`
- Test: `tests/analysis/test_audio.py`, `tests/core/test_security.py`, `tests/core/test_rate_limit.py`, `tests/jobs/test_registry.py`

**Interfaces:**
- `validate_upload(filename: str, content: bytes) -> AudioMetadata`
- `hash_ip(ip: str, secret: str) -> str`
- `RateLimiter.allow(key: str) -> bool`
- `JobRegistry.create/get/update/cancel/release_lock(...)`

- [ ] **Step 1: Write failing tests** for supported extensions, signature mismatch, empty/corrupt payloads, deterministic IP hashing, rate limit expiry, duplicate locks, and job transitions.
- [ ] **Step 2: Run the focused test command and confirm failures are caused by missing implementations.**
- [ ] **Step 3: Implement bounded-memory validators, hashed keys, TTL-based limits, and thread-safe in-memory job records.**
- [ ] **Step 4: Re-run the focused tests and confirm they pass.**
- [ ] **Step 5: Commit `feat: add upload validation and job registry`.**

### Task 4: Pipeline adapters, cleanup, and runner

**Files:**
- Create: `app/analysis/pipeline.py`, `app/analysis/aggregation.py`, `app/analysis/cleanup.py`, `app/jobs/runner.py`
- Test: `tests/analysis/test_pipeline.py`, `tests/jobs/test_runner.py`

**Interfaces:**
- `Analyzer` protocol with `preprocess`, `transcribe`, `classify`, `finalize`
- `FakeAnalyzer` for deterministic tests
- `JobRunner.submit(job_id, analyzer) -> None`
- `cleanup_job(job) -> None`

- [ ] **Step 1: Write failing tests** for ordered stage transitions, non-Korean failure, fake completed result, cancellation checkpoints, and cleanup on success/failure/cancel.
- [ ] **Step 2: Run focused tests and confirm missing pipeline/runner failures.**
- [ ] **Step 3: Implement the minimal pipeline, fake adapter, cancellation-aware runner, top-three aggregation, and idempotent cleanup.**
- [ ] **Step 4: Re-run focused tests and confirm they pass.**
- [ ] **Step 5: Commit `feat: add asynchronous analysis runner`.**

### Task 5: Analyze routes and full API integration

**Files:**
- Create: `app/api/routes/analyze.py`
- Modify: `app/api/main.py`
- Test: `tests/api/test_analyze.py`

**Interfaces:**
- `POST /api/v1/analyze -> 202 JobCreatedResponse`
- `GET /api/v1/analyze/{job_id}/status -> JobStatusResponse`
- `GET /api/v1/analyze/{job_id}/result -> AnalysisResultResponse`
- `DELETE /api/v1/analyze/{job_id} -> JobStatusResponse`

- [ ] **Step 1: Write failing API tests** for model-unready 503, valid upload, invalid upload, duplicate/rate-limited requests, status polling, result retrieval, not-found, and cancellation.
- [ ] **Step 2: Run `pytest tests/api/test_analyze.py -q` and confirm failures before route implementation.**
- [ ] **Step 3: Implement route dependencies, request ID/error handling, temporary file ownership, runner submission, and cleanup hooks.**
- [ ] **Step 4: Re-run the API tests and confirm they pass.**
- [ ] **Step 5: Commit `feat: expose asynchronous analysis api`.**

### Task 6: Documentation, container scaffold, and verification

**Files:**
- Modify: `README.md`, `docs/architecture.md`, `docs/개발가이드_FastAPI_Nuxt_MVP.md`, `.env.example`, `requirements.txt`
- Create: `Dockerfile`, `tests/conftest.py`

- [ ] **Step 1: Write the integration test** that runs the fake analyzer through upload, polling, result, and cleanup.
- [ ] **Step 2: Run the test and confirm it fails if any integration contract is missing.**
- [ ] **Step 3: Update docs to remove the stale 8kHz claim, document `/api/v1` routes, environment variables, fake analyzer test mode, and single-instance limitation; add a minimal Python 3.11 Dockerfile.**
- [ ] **Step 4: Run `pytest -q`, `python -m compileall app tests`, and a route smoke check; record exact results.**
- [ ] **Step 5: Review `git diff`, verify no audio/transcript/secret files are included, and commit `docs: document backend api scaffold`.**
