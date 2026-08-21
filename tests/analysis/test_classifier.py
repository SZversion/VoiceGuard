import pytest

from app.analysis.classifier import ClassifierOutput, TextClassifier


class FakeTokenizer:
    def __call__(self, text, **kwargs):
        assert text == "의심스러운 송금 요청입니다."
        assert kwargs["max_length"] == 128
        assert kwargs["truncation"] is True
        return {"input_ids": [[1, 2, 3]]}


class FakeModel:
    def __call__(self, **inputs):
        assert inputs == {"input_ids": [[1, 2, 3]]}
        return type("Output", (), {"logits": [[0.1, 2.1]]})()


def test_classify_maps_model_id_to_voice_phishing():
    classifier = TextClassifier(FakeTokenizer(), FakeModel())

    result = classifier.classify("의심스러운 송금 요청입니다.")

    assert isinstance(result, ClassifierOutput)
    assert result.label == "voice_phishing"
    assert result.label_id == 1
    assert 0.0 <= result.suspicion_score <= 1.0


def test_classify_rejects_empty_text():
    classifier = TextClassifier(FakeTokenizer(), FakeModel())

    with pytest.raises(ValueError, match="transcript"):
        classifier.classify("   ")


def test_classify_rejects_unknown_class_count():
    class InvalidModel(FakeModel):
        def __call__(self, **inputs):
            return type("Output", (), {"logits": [[1.0, 2.0, 3.0]]})()

    classifier = TextClassifier(FakeTokenizer(), InvalidModel())

    with pytest.raises(ValueError, match="class id"):
        classifier.classify("의심스러운 송금 요청입니다.")
