# Spec - Finance transcript normalization

## Why

Whisper output can contain speaker labels, correction markers, noise markup, masking sounds,
spaced digits, and dual number notation. The classifier should receive a stable transcript
without changing the existing API result contract.

## Goal

Apply normalize_finance_text between STT transcription and text classification.
Keep normalization deterministic, local, and testable. Preserve ordinary words unless they
match an explicit markup pattern.

## What

The normalizer handles:

- consecutive dual number notation such as 1/one 2/two
- individual dual number notation
- digit sequences separated by spaces
- correction marker +
- parenthesized noise markup
- AI Hub filler markup ending in /
- masking marker \uc0a5 or \uc0a5-
- speaker labels \ud53c\ud574\uc790: and \uc0ac\uae30\ubc94:
- repeated whitespace

## How

The normalizer lives in app/analysis/text_normalizer.py and returns a string.
VoicePhishingAnalyzer passes this returned string to TextClassifier.classify.
The analysis progress stage remains normalizing.

## Acceptance criteria

- Each cleanup rule has a deterministic unit test.
- The analyzer passes normalized text, not the raw transcript, to the classifier.
- Existing clean transcripts and result fields remain unchanged.
- Empty transcripts continue to fail through the classifier contract.
- No audio, transcript, token, or personal data is persisted by the normalizer.
