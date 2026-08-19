from collections.abc import Mapping
from typing import Protocol


class Analyzer(Protocol):
    async def analyze(self, audio: bytes) -> Mapping[str, object]:
        ...
