import pytest

from tools.model_evaluation import EvaluationCase, compute_metrics


def test_compute_metrics_counts_binary_predictions_without_filename_labels():
    cases = [
        EvaluationCase("normal", "normal", 0.1),
        EvaluationCase("normal", "voice_phishing", 0.8),
        EvaluationCase("voice_phishing", "voice_phishing", 0.9),
        EvaluationCase("voice_phishing", "normal", 0.2),
    ]

    metrics = compute_metrics(cases)

    assert metrics == {
        "total": 4,
        "true_positive": 1,
        "true_negative": 1,
        "false_positive": 1,
        "false_negative": 1,
        "accuracy": 0.5,
        "precision": 0.5,
        "recall": 0.5,
        "f1": 0.5,
        "false_positive_rate": 0.5,
    }


def test_compute_metrics_rejects_unknown_labels():
    with pytest.raises(ValueError, match="label"):
        compute_metrics([EvaluationCase("unknown", "normal", 0.1)])