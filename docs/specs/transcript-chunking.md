# Spec - Token based transcript chunking

## Why

The KoELECTRA classifier uses max_length 128. A long normalized transcript must not be
silently truncated to one model input.

## Goal

Split normalized text by tokenizer token IDs before classification. Reserve two positions
for special tokens, so the content length is max_length - 2. Keep chunks ordered and use no
overlap in this first implementation.

Aggregate chunk classifications with an explicit high-recall OR policy:

- if any chunk is voice_phishing, the call is voice_phishing
- the representative suspicion score is the maximum chunk score
- otherwise the call is normal and the representative score is the maximum score

## Out of scope

- overlap and sentence-aware chunking
- chunk-level reference segment persistence
- threshold calibration and model changes
- changing the public result schema

## Acceptance criteria

- Text within the content limit returns one unchanged chunk.
- Longer text is split by tokenizer IDs into ordered non-empty chunks.
- Each chunk is classified once.
- OR aggregation detects one suspicious chunk.
- Existing short transcript and analyzer contracts remain valid.
