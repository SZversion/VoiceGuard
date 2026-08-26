from app.analysis.domain_corrector import DomainCorrectionRule, DomainTermCorrector
from tools.domain_correction_evaluation import evaluate_pairs


def test_evaluate_pairs_reports_raw_and_corrected_metrics_by_rule():
    corrector = DomainTermCorrector(
        [DomainCorrectionRule("typo-1", "보이스피시", "보이스피싱", "오탈자")]
    )

    result = evaluate_pairs(
        [
            {
                "sample_id": "sample-1",
                "reference": "보이스피싱 조심하세요",
                "hypothesis": "보이스피시 조심하세요",
            }
        ],
        corrector,
    )

    assert result["sample_count"] == 1
    assert result["changed_sample_count"] == 1
    assert result["average_raw_cer"] > result["average_corrected_cer"]
    assert result["rules"]["typo-1"]["application_count"] == 1
    assert result["rules"]["typo-1"]["improved_sample_count"] == 1


def test_evaluate_pairs_does_not_store_transcript_text():
    result = evaluate_pairs(
        [
            {
                "sample_id": "sample-1",
                "reference": "정상 상담입니다",
                "hypothesis": "정상 상담입니다",
            }
        ],
        DomainTermCorrector([]),
    )

    serialized = str(result)
    assert "정상 상담입니다" not in serialized
    assert "reference" not in result
    assert "hypothesis" not in result
