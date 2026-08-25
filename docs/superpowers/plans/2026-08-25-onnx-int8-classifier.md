# ONNX INT8 Classifier Runtime Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an ONNX INT8 KoELECTRA classifier that preserves the existing classifier contract and uses ONNX INT8 as the only FastAPI classifier runtime.

**Architecture:** Add a focused ONNX classifier implementation and loader. Keep analyzer and API contracts unchanged while FastAPI startup loads only the ONNX INT8 classifier. The analyzer and API schemas remain unchanged.

**Tech Stack:** Python 3.11, ONNX Runtime, Transformers tokenizer, pytest, FastAPI lifespan.

**Spec:** `docs/specs/onnx-int8-classifier.md`

## Global Constraints

- Preserve `ClassifierOutput`, `classify()`, and `classify_chunks()` behavior.
- Preserve label mapping `0=normal`, `1=voice_phishing`.
- Use `max_length=128` and `CPUExecutionProvider`.
- Do not select the PyTorch loader from FastAPI runtime.
- Do not change STT, threshold, API response schemas, or batch inference in this branch.
- Do not commit tokens, audio, model files, or local caches.

---

### Task 1: Add ONNX Runtime dependency

**Files:**
- Modify: `requirements.txt`
- Test: `tests/analysis/test_onnx_classifier.py`

- [ ] **Step 1: Write the failing ONNX classifier contract tests**
- [ ] **Step 2: Run the focused tests and confirm the missing-module failure**
- [ ] **Step 3: Add the minimal `onnxruntime` dependency declaration**
- [ ] **Step 4: Run the focused tests again**

### Task 2: Implement the ONNX classifier

**Files:**
- Create: `app/analysis/onnx_classifier.py`
- Modify: `tests/analysis/test_onnx_classifier.py`

**Interfaces:**
- Consumes: tokenizer, ONNX session, `max_length=128`
- Produces: `OnnxTextClassifier.classify(text) -> ClassifierOutput`; `classify_chunks(text) -> list[tuple[str, ClassifierOutput]]`

- [ ] **Step 1: Test valid logits and label mapping**
- [ ] **Step 2: Test empty text rejection and non-binary logits rejection**
- [ ] **Step 3: Implement tokenizer input mapping and softmax output**
- [ ] **Step 4: Run focused tests and refactor only after green**

### Task 3: Connect the ONNX loader as the FastAPI classifier runtime

**Files:**
- Create: `app/analysis/onnx_loader.py`
- Modify: `app/api/main.py`
- Test: `tests/analysis/test_onnx_loader.py`, `tests/api/test_analyzer_runtime.py`

**Interfaces:**
- Consumes: ONNX model repository constants and optional injected factories
- Produces: `load_onnx_classifier() -> OnnxTextClassifier`; FastAPI startup uses this loader

- [ ] **Step 1: Test ONNX loader configuration and error wrapping**
- [ ] **Step 2: Test FastAPI startup uses the ONNX loader by default**
- [ ] **Step 4: Implement minimal selector and loader**
- [ ] **Step 5: Run focused runtime tests**

### Task 4: Verify model parity and runtime behavior

**Files:**
- Modify: `docs/specs/onnx-int8-classifier.md` only if measured behavior changes the contract
- Test: existing classifier, analyzer, and API runtime tests

- [ ] **Step 1: Install dependencies in the local environment**
- [ ] **Step 2: Run the ONNX INT8 smoke test against the Hugging Face model**
- [ ] **Step 3: Compare labels, suspicion scores, and warm latency with the reference evaluation outputs**
- [ ] **Step 4: Run focused tests and `git diff --check`**
- [ ] **Step 5: Run the full suite and record unrelated baseline failures without hiding them**
- [ ] **Step 6: Review changed files, secrets, caches, and audio artifacts before commit**