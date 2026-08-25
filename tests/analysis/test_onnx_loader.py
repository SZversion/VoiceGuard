import pytest

from app.analysis.model_loader import ModelLoadError
from app.analysis.onnx_loader import load_onnx_classifier


class FakeTokenizer:
    calls = []

    @classmethod
    def from_pretrained(cls, model_id, **kwargs):
        cls.calls.append((model_id, kwargs))
        return cls()


class FakeSession:
    def __init__(self, path, providers):
        self.path = path
        self.providers = providers


class FakeRuntime:
    InferenceSession = FakeSession


def test_loader_downloads_onnx_file_and_creates_cpu_session():
    downloads = []

    def fake_download(**kwargs):
        downloads.append(kwargs)
        return "C:/cache/model_quantized.onnx"

    classifier = load_onnx_classifier(
        model_id="example/model",
        tokenizer_class=FakeTokenizer,
        runtime_module=FakeRuntime,
        hub_download=fake_download,
    )

    assert classifier.max_length == 128
    assert downloads[0]["filename"] == "koelectra_v1_onnx_int8/model_quantized.onnx"
    assert classifier.session.path.endswith("model_quantized.onnx")
    assert classifier.session.providers == ["CPUExecutionProvider"]
    assert FakeTokenizer.calls[0][0] == "example/model"
    assert FakeTokenizer.calls[0][1]["subfolder"] == "koelectra_v1_onnx_int8"


def test_loader_wraps_download_or_session_errors():
    def failing_download(**kwargs):
        raise RuntimeError("private repository")

    with pytest.raises(ModelLoadError, match="분류모델"):
        load_onnx_classifier(
            tokenizer_class=FakeTokenizer,
            runtime_module=FakeRuntime,
            hub_download=failing_download,
        )