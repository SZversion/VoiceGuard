import asyncio

from app.analysis.audio_chunking import AudioChunk
from app.analysis.whisper_transcriber import WhisperLoRATranscriber


class FakeTranscriber(WhisperLoRATranscriber):
    def __init__(self):
        pass

    async def transcribe(self, audio: bytes) -> str:
        return f"transcript-{audio.decode()}"


def test_transcribe_chunks_processes_chunks_in_order():
    transcriber = FakeTranscriber()
    transcriber.audio_splitter = lambda audio: [
        AudioChunk(b"one", 0.0, 30.0),
        AudioChunk(b"two", 30.0, 60.0),
    ]

    result = asyncio.run(transcriber.transcribe_chunks(b"audio"))

    assert [(item.start, item.end, item.transcript) for item in result] == [
        (0.0, 30.0, "transcript-one"),
        (30.0, 60.0, "transcript-two"),
    ]
