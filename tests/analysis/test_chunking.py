from app.analysis.chunking import chunk_text_by_tokens


class FakeTokenizer:
    def encode(self, text, add_special_tokens=False):
        return list(range(len(text.split())))

    def decode(self, token_ids, skip_special_tokens=True):
        return " ".join(f"token{token_id}" for token_id in token_ids)


def test_short_text_is_returned_unchanged():
    tokenizer = FakeTokenizer()

    assert chunk_text_by_tokens("short text", tokenizer, max_length=5) == ["short text"]


def test_long_text_is_split_by_content_token_limit():
    tokenizer = FakeTokenizer()

    chunks = chunk_text_by_tokens(
        "one two three four five six",
        tokenizer,
        max_length=5,
    )

    assert chunks == [
        "token0 token1 token2",
        "token3 token4 token5",
    ]
