import pytest

from app.analysis.model_loader import ModelLoadError, load_text_classifier


class FakeTokenizer:
    @classmethod
    def from_pretrained(cls, model_id):
        assert model_id == "test/model"
        return cls()


class FakeModel:
    evaluated = False

    @classmethod
    def from_pretrained(cls, model_id):
        assert model_id == "test/model"
        return cls()

    def eval(self):
        self.evaluated = True


def test_load_text_classifier_loads_model_once():
    classifier = load_text_classifier(
        model_id="test/model",
        max_length=128,
        loader=lambda: (FakeTokenizer, FakeModel),
    )

    assert classifier.max_length == 128
    assert isinstance(classifier.tokenizer, FakeTokenizer)
    assert isinstance(classifier.model, FakeModel)
    assert classifier.model.evaluated is True


def test_load_text_classifier_wraps_load_failure():
    class BrokenModel:
        @classmethod
        def from_pretrained(cls, model_id):
            raise OSError("download failed")

    with pytest.raises(ModelLoadError, match="분류모델을 로드하지 못했습니다"):
        load_text_classifier(
            model_id="test/model",
            loader=lambda: (FakeTokenizer, BrokenModel),
        )
