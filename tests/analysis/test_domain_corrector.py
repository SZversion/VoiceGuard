import pytest

from app.analysis.domain_corrector import (
    AppliedCorrection,
    DomainCorrectionRule,
    DomainTermCorrector,
    load_default_domain_rules,
)


def test_applies_allowlisted_phrase_and_records_rule():
    corrector = DomainTermCorrector(
        [DomainCorrectionRule("r1", "대출 상환", "대출상환", "금융 용어", "spacing")],
        enabled_kinds=("typo", "spacing"),
    )

    result = corrector.correct("대출 상환을 요구했습니다.")

    assert result.raw_transcript == "대출 상환을 요구했습니다."
    assert result.corrected_transcript == "대출상환을 요구했습니다."
    assert result.corrections == (
        AppliedCorrection("r1", "대출 상환", "대출상환", "금융 용어"),
    )


def test_unknown_phrase_is_unchanged():
    corrector = DomainTermCorrector([])
    result = corrector.correct("일반 상담 내용입니다.")

    assert result.corrected_transcript == result.raw_transcript
    assert result.corrections == ()


def test_rules_are_applied_in_declared_order():
    corrector = DomainTermCorrector(
        [
            DomainCorrectionRule("r1", "검찰 청", "검찰청", "기관명", "spacing"),
            DomainCorrectionRule("r2", "대출 상환", "대출상환", "금융 용어", "spacing"),
        ],
        enabled_kinds=("typo", "spacing"),
    )

    result = corrector.correct("검찰 청이 대출 상환을 요구했습니다.")

    assert result.corrected_transcript == "검찰청이 대출상환을 요구했습니다."
    assert [item.rule_id for item in result.corrections] == ["r1", "r2"]


@pytest.mark.parametrize(
    "rules",
    [
        [DomainCorrectionRule("r1", "", "target", "reason")],
        [DomainCorrectionRule("r1", "same", "same", "reason")],
        [
            DomainCorrectionRule("r1", "same", "target", "reason"),
            DomainCorrectionRule("r1", "other", "target", "reason"),
        ],
    ],
)
def test_invalid_rules_are_rejected(rules):
    with pytest.raises(ValueError):
        DomainTermCorrector(rules)


def test_empty_transcript_is_rejected():
    corrector = DomainTermCorrector([])

    with pytest.raises(ValueError, match="transcript"):
        corrector.correct("  ")


def test_corrects_voice_phishing_typo():
    corrector = DomainTermCorrector(
        [DomainCorrectionRule("r1", "보이스피시", "보이스피싱", "오탈자")]
    )

    result = corrector.correct("보이스피시 의심 표현입니다.")

    assert result.corrected_transcript == "보이스피싱 의심 표현입니다."
    assert result.corrections[0].rule_id == "r1"


def test_contextual_rule_applies_when_context_is_nearby():
    corrector = DomainTermCorrector(
        [
            DomainCorrectionRule(
                "r1",
                "보이스피시",
                "보이스피싱",
                "오탈자",
                "typo",
                ("사칭",),
                12,
            )
        ]
    )

    result = corrector.correct("검찰 사칭 보이스피시가 의심됩니다.")

    assert result.corrected_transcript == "검찰 사칭 보이스피싱이 의심됩니다."


def test_contextual_rule_does_not_apply_when_context_is_far_away():
    corrector = DomainTermCorrector(
        [
            DomainCorrectionRule(
                "r1",
                "보이스피시",
                "보이스피싱",
                "오탈자",
                "typo",
                ("사칭",),
                5,
            )
        ]
    )

    result = corrector.correct("검찰 사칭에 관한 긴 설명입니다. 보이스피시 표현입니다.")

    assert result.corrected_transcript == result.raw_transcript


def test_default_corrector_does_not_apply_spacing_rules():
    corrector = DomainTermCorrector(
        [DomainCorrectionRule("spacing", "개인 정보", "개인정보", "띄어쓰기", "spacing")]
    )

    result = corrector.correct("개인 정보가 유출되었습니다.")

    assert result.corrected_transcript == result.raw_transcript
    assert result.corrections == ()


def test_default_rules_only_enable_non_spacing_typo_corrections():
    corrector = DomainTermCorrector(load_default_domain_rules())

    result = corrector.correct("보이스피시와 개인 정보가 언급되었습니다.")

    assert result.corrected_transcript == "보이스피싱와 개인 정보가 언급되었습니다."
    assert [item.rule_id for item in result.corrections] == ["domain-phishing-002"]


def test_default_rules_correct_reviewed_domain_typos_in_context():
    corrector = DomainTermCorrector(load_default_domain_rules())

    result = corrector.correct(
        "계좌를 확인하겠습니다. 무통장 입금과 검찰청 안내를 이용하세요."
    )

    assert result.corrected_transcript == (
        "계좌를 확인하겠습니다. 무통장 입금과 검찰청 안내를 이용하세요."
    )


@pytest.mark.parametrize(
    ("transcript", "expected"),
    [
        ("금융기관 계절 확인", "금융기관 계좌 확인"),
        ("무통장 모통장 입금", "무통장 무통장 입금"),
        ("수사기관 검찰촌 안내", "수사기관 검찰청 안내"),
    ],
)
def test_default_rules_correct_candidate_stt_typos(transcript, expected):
    corrector = DomainTermCorrector(load_default_domain_rules())

    result = corrector.correct(transcript)

    assert result.corrected_transcript == expected


@pytest.mark.parametrize("source", ["계절", "모통장", "검찰촌"])
def test_candidate_typos_are_not_corrected_without_domain_context(source):
    corrector = DomainTermCorrector(load_default_domain_rules())

    result = corrector.correct(f"오늘은 {source} 이야기를 들었습니다.")

    assert result.corrected_transcript == result.raw_transcript


@pytest.mark.parametrize(
    ("source", "target"),
    [
        ("대포 통장", "대포통장"),
        ("개인 정보", "개인정보"),
        ("신용 카드", "신용카드"),
        ("명의 도용", "명의도용"),
        ("금융 사기", "금융사기"),
    ],
)
def test_corrects_allowlisted_domain_spacing(source, target):
    corrector = DomainTermCorrector(
        [DomainCorrectionRule("spacing", source, target, "띄어쓰기", "spacing")],
        enabled_kinds=("typo", "spacing"),
    )

    result = corrector.correct(source)

    assert result.corrected_transcript == target


@pytest.mark.parametrize(
    ("source", "target"),
    [
        ("금융 감독원", "금융감독원"),
        ("인증 번호", "인증번호"),
        ("비밀 번호", "비밀번호"),
        ("안전 계좌", "안전계좌"),
        ("공인 인증서", "공인인증서"),
    ],
)
def test_default_spacing_draft_rules_apply_only_when_enabled(source, target):
    corrector = DomainTermCorrector(
        load_default_domain_rules(),
        enabled_kinds=("typo", "spacing"),
    )

    result = corrector.correct(source)

    assert result.corrected_transcript == target
