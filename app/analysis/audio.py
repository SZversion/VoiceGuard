from pathlib import Path


ALLOWED_EXTENSIONS = {".wav", ".mp3", ".m4a"}


class AudioValidationError(ValueError):
    def __init__(self, error_code: str, message: str):
        super().__init__(message)
        self.error_code = error_code
        self.message = message


def validate_audio(filename: str | None, content_type: str | None, data: bytes) -> None:
    extension = Path(filename or "").suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise AudioValidationError("AUDIO.UNSUPPORTED_FORMAT", "지원하지 않는 음성 파일 형식입니다.")
    if not data:
        raise AudioValidationError("AUDIO.EMPTY", "음성 파일이 비어 있습니다.")

    if extension == ".wav":
        valid_signature = len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WAVE"
        allowed_type = content_type in {"audio/wav", "audio/x-wav", "audio/wave"}
    elif extension == ".mp3":
        valid_signature = data.startswith(b"ID3") or data[:2] in {b"\xff\xfb", b"\xff\xf3", b"\xff\xf2"}
        allowed_type = content_type in {"audio/mpeg", "audio/mp3"}
    else:
        valid_signature = b"ftyp" in data[:32]
        allowed_type = content_type in {"audio/mp4", "audio/x-m4a", "video/mp4"}

    if not valid_signature or not allowed_type:
        raise AudioValidationError("AUDIO.INVALID_FORMAT", "음성 파일의 기본 형식을 확인할 수 없습니다.")
