from app.analysis.classifier import ClassifierOutput, TextClassifier


class FakeTokenizer:
    def encode(self, text, add_special_tokens=False):
        return list(range(len(text.split())))

    def decode(self, token_ids, skip_special_tokens=True):
        return " ".join(f"token{token_id}" for token_id in token_ids)

    def __call__(self, transcript, **kwargs):
        return {"input": transcript}


class FakeModel:
    def __call__(self, **encoded):
        class Output:
            logits = [[0.0, 1.0]]

        return Output()


def test_classifier_classifies_each_chunk():
    classifier = TextClassifier(FakeTokenizer(), FakeModel(), max_length=5)

    outputs = classifier.classify_chunks("one two three four five six")

    assert [text for text, _ in outputs] == [
        "token0 token1 token2",
        "token3 token4 token5",
    ]
    assert all(isinstance(result, ClassifierOutput) for _, result in outputs)
