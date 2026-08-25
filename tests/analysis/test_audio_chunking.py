import numpy as np

from app.analysis.audio_chunking import split_waveform


def test_split_waveform_creates_sequential_30_second_chunks():
    waveform = np.zeros(65 * 10, dtype=np.float32)

    chunks = split_waveform(waveform, sample_rate=10, chunk_seconds=30)

    assert [(chunk.start, chunk.end) for chunk in chunks] == [
        (0.0, 30.0),
        (30.0, 60.0),
        (60.0, 65.0),
    ]
    assert [len(chunk.audio) for chunk in chunks] == [300, 300, 50]


def test_short_waveform_stays_as_one_chunk():
    waveform = np.zeros(10, dtype=np.float32)

    chunks = split_waveform(waveform, sample_rate=10, chunk_seconds=30)

    assert len(chunks) == 1
    assert chunks[0].start == 0.0
    assert chunks[0].end == 1.0
