from __future__ import annotations

import mimetypes
from pathlib import Path


class LocalMediaFile:
    """Diskteki dosyayı Streamlit UploadedFile arayüzüyle sunar; video kopyalanmadan yerinde okunur."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.name = self.path.name
        self.size = self.path.stat().st_size
        self.type = mimetypes.guess_type(self.name)[0] or "application/octet-stream"

    def getvalue(self) -> bytes:
        return self.path.read_bytes()

    def getbuffer(self) -> memoryview:
        return memoryview(self.getvalue())
