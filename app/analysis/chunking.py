from collections.abc import Sequence
from typing import Any


def chunk_text_by_tokens(
    text: str,
    tokenizer: Any,
    max_length: int = 128,
) -> list[str]:
    """Split text into ordered, non-empty tokenizer-based model inputs."""
    content_length = max_length - 2
    if content_length <= 0:
        raise ValueError("max_length must be greater than 2")

    token_ids: Sequence[int] = tokenizer.encode(
        text,
        add_special_tokens=False,
    )
    if len(token_ids) <= content_length:
        return [text]

    chunks: list[str] = []
    for start in range(0, len(token_ids), content_length):
        chunk_ids = token_ids[start : start + content_length]
        chunk_text = tokenizer.decode(
            chunk_ids,
            skip_special_tokens=True,
        )
        if chunk_text.strip():
            chunks.append(chunk_text)
    return chunks
