import os
import tempfile
from pathlib import Path


class TempDataStore:
    def __init__(self, directory: str | None = None):
        self.directory = directory

    def create(self, data: bytes) -> str:
        fd, path = tempfile.mkstemp(prefix="analysis_", suffix=".audio", dir=self.directory)
        with os.fdopen(fd, "wb") as file:
            file.write(data)
        return path

    def delete(self, path: str) -> None:
        try:
            Path(path).unlink()
        except FileNotFoundError:
            pass
