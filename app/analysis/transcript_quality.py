from collections import Counter
from dataclasses import dataclass
import re


@dataclass(frozen=True)
class TranscriptQualityResult:
    usable: bool
    score: float
    reason: str | None = None


class TranscriptQualityFilter:
    """Conservatively reject transcripts that are unlikely to be meaningful text."""

    _valid_char = re.compile(r"[가-힣A-Za-z0-9\s.,!?%~()\-]")
    _meaningful_token = re.compile(r"[가-힣A-Za-z0-9]")

    def __init__(
        self,
        invalid_char_ratio: float = 0.4,
        repeated_token_ratio: float = 0.7,
        repeated_token_minimum: int = 4,
    ):
        if not 0 <= invalid_char_ratio <= 1:
            raise ValueError("invalid_char_ratio must be between 0 and 1")
        if not 0 < repeated_token_ratio <= 1:
            raise ValueError("repeated_token_ratio must be between 0 and 1")
        if repeated_token_minimum < 2:
            raise ValueError("repeated_token_minimum must be at least 2")
        self.invalid_char_ratio = invalid_char_ratio
        self.repeated_token_ratio = repeated_token_ratio
        self.repeated_token_minimum = repeated_token_minimum

    def check(self, transcript: str) -> TranscriptQualityResult:
        if not transcript or not transcript.strip():
            return TranscriptQualityResult(False, 0.0, "empty_transcript")

        compact = "".join(transcript.split())
        valid_ratio = sum(bool(self._valid_char.fullmatch(char)) for char in compact) / len(compact)
        score = round(valid_ratio, 4)
        if 1 - valid_ratio > self.invalid_char_ratio:
            return TranscriptQualityResult(False, score, "low_valid_ratio")

        tokens = re.findall(r"[가-힣A-Za-z0-9]+", transcript)
        if tokens:
            most_common_count = Counter(tokens).most_common(1)[0][1]
            if len(tokens) >= self.repeated_token_minimum and most_common_count / len(tokens) >= self.repeated_token_ratio:
                return TranscriptQualityResult(False, score, "repeated_tokens")
            if not any(self._meaningful_token.search(token) for token in tokens):
                return TranscriptQualityResult(False, score, "no_meaningful_tokens")
        else:
            return TranscriptQualityResult(False, score, "no_meaningful_tokens")

        return TranscriptQualityResult(True, score)
