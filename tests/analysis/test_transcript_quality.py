import pytest

from app.analysis.transcript_quality import TranscriptQualityFilter


def test_rejects_empty_transcript_with_explicit_reason():
    result = TranscriptQualityFilter().check("   ")

    assert result.usable is False
    assert result.reason == "empty_transcript"


def test_rejects_severely_repeated_tokens():
    result = TranscriptQualityFilter().check("아아 아아 아아 아아 아아")

    assert result.usable is False
    assert result.reason == "repeated_tokens"


def test_rejects_transcript_with_too_many_invalid_characters():
    result = TranscriptQualityFilter().check("@@@ ### $$$ %%")

    assert result.usable is False
    assert result.reason == "low_valid_ratio"


def test_accepts_short_meaningful_financial_transcript():
    result = TranscriptQualityFilter().check("계좌 확인")

    assert result.usable is True
    assert result.reason is None
    assert 0.0 <= result.score <= 1.0


@pytest.mark.parametrize("transcript", ["대출", "송금 요청", "무통장 입금"])
def test_accepts_short_domain_phrases(transcript):
    assert TranscriptQualityFilter().check(transcript).usable is True
