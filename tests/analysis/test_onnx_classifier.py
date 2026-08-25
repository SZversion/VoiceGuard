import numpy as np
import pytest

from app.analysis.classifier import ClassifierOutput
from app.analysis.onnx_classifier import OnnxTextClassifier


class FakeTokenizer:
    def __call__(self, text, **kwargs):
        assert kwargs["return_tensors"] == "np"
        assert kwargs["max_length"] == 128
        assert kwargs["truncation"] is True
        assert kwargs["padding"] == "max_length"
        return {
            "input_ids": np.array([[1, 2, 3]], dtype=np.int64),
            "attention_mask": np.array([[1, 1, 1]], dtype=np.int64),
        }

    def encode(self, text, add_special_tokens=False):
        return list(range(130))

    def decode(self, token_ids, skip_special_tokens=True):
        return "청크 " + str(token_ids[0])


class FakeSession:
    def __init__(self, logits=(0.1, 2.1), input_names=("input_ids", "attention_mask")):
        self.logits = logits
        self.input_names = input_names
        self.received = None

    def get_inputs(self):
        return [type("Input", (), {"name": name})() for name in self.input_names]

    def run(self, output_names, inputs):
        self.received = inputs
        return [np.array([self.logits], dtype=np.float32)]


def test_classify_returns_existing_output_contract_and_maps_label():
    session = FakeSession()
    classifier = OnnxTextClassifier(FakeTokenizer(), session)

    result = classifier.classify("의심스러운 송금 요청입니다.")

    assert isinstance(result, ClassifierOutput)
    assert result.label == "voice_phishing"
    assert result.label_id == 1
    assert 0.0 <= result.suspicion_score <= 1.0
    assert set(session.received) == {"input_ids", "attention_mask"}


def test_classify_rejects_empty_text():
    classifier = OnnxTextClassifier(FakeTokenizer(), FakeSession())

    with pytest.raises(ValueError, match="transcript"):
        classifier.classify("   ")


def test_classify_rejects_non_binary_logits():
    classifier = OnnxTextClassifier(FakeTokenizer(), FakeSession(logits=(1.0, 2.0, 3.0)))

    with pytest.raises(ValueError, match="class id"):
        classifier.classify("텍스트")


def test_classify_chunks_uses_existing_token_chunking_contract():
    classifier = OnnxTextClassifier(FakeTokenizer(), FakeSession())

    results = classifier.classify_chunks("긴 통화 텍스트")

    assert len(results) == 2
    assert all(isinstance(output, ClassifierOutput) for _, output in results)