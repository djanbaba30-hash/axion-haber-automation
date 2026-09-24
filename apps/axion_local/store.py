"""Axion Local: editörün bilgisayarındaki kalıcı proje klasörü ve medya gelen kutusu."""

from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from shared.news_package import NewsPackage, parse_news_package

ROOT = Path(__file__).resolve().parents[2]

VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v"}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
MEDIA_EXTENSIONS = VIDEO_EXTENSIONS | IMAGE_EXTENSIONS

PACKAGE_FILENAME = "news_package.json"
AUDIO_FILENAME = "tts.mp3"


def is_local_mode() -> bool:
    return os.environ.get("AXION_LOCAL") == "1"


def data_dir() -> Path:
    return Path(os.environ.get("AXION_DATA_DIR") or ROOT / "data")


def projects_dir() -> Path:
    return data_dir() / "projects"


def inbox_dir() -> Path:
    return Path(os.environ.get("AXION_INBOX_DIR") or Path.home() / "Downloads")


def list_inbox_media(folder: Path | None = None, limit: int = 40) -> list[Path]:
    """Gelen kutusundaki video/görselleri en yeniden eskiye sıralar."""
    folder = folder or inbox_dir()
    if not folder.is_dir():
        return []
    files = [
        path for path in folder.iterdir()
        if path.is_file() and path.suffix.lower() in MEDIA_EXTENSIONS
    ]
    files.sort(key=lambda path: path.stat().st_mtime, reverse=True)
    return files[:limit]


def _slug(text: str, max_length: int = 40) -> str:
    table = str.maketrans("çğıöşüÇĞİÖŞÜâÂîÎûÛ", "cgiosuCGIOSUaAiIuU")
    slug = re.sub(r"[^a-z0-9]+", "-", text.translate(table).lower()).strip("-")
    if len(slug) > max_length:
        cut = slug[:max_length + 1]
        slug = cut.rsplit("-", 1)[0] if "-" in cut else slug[:max_length]
    return slug or "haber"


@dataclass(frozen=True)
class NewsProject:
    folder: Path
    headline: str
    created_at: str

    @property
    def package_path(self) -> Path:
        return self.folder / PACKAGE_FILENAME

    @property
    def audio_path(self) -> Path | None:
        path = self.folder / AUDIO_FILENAME
        return path if path.exists() else None

    @property
    def label(self) -> str:
        audio = "ses var" if self.audio_path else "ses yok"
        return f"{self.created_at} · {self.headline} · {audio}"


def save_news_project(
    package: NewsPackage,
    audio_bytes: bytes | None,
    base_dir: Path | None = None,
    now: datetime | None = None,
) -> Path:
    """Haber paketini ve TTS sesini tek proje klasörüne yazar; ses hash'i pakete eklenir."""
    base_dir = base_dir or projects_dir()
    stamp = (now or datetime.now()).strftime("%Y%m%d-%H%M%S")
    folder = base_dir / f"{stamp}_{_slug(package.headline_1)}"
    folder.mkdir(parents=True, exist_ok=False)

    metadata = dict(package.metadata)
    if audio_bytes:
        (folder / AUDIO_FILENAME).write_bytes(audio_bytes)
        metadata["audio_sha256"] = hashlib.sha256(audio_bytes).hexdigest()
        metadata["audio_filename"] = AUDIO_FILENAME
    stored = package.model_copy(update={"metadata": metadata})
    (folder / PACKAGE_FILENAME).write_text(stored.model_dump_json(indent=2), encoding="utf-8")
    return folder


def list_news_projects(base_dir: Path | None = None, limit: int = 30) -> list[NewsProject]:
    base_dir = base_dir or projects_dir()
    if not base_dir.is_dir():
        return []
    projects = []
    for folder in sorted(base_dir.iterdir(), reverse=True):
        package_path = folder / PACKAGE_FILENAME
        if not package_path.is_file():
            continue
        try:
            data = json.loads(package_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        stamp = folder.name.split("_", 1)[0]
        try:
            created = datetime.strptime(stamp, "%Y%m%d-%H%M%S").strftime("%d.%m.%Y %H:%M")
        except ValueError:
            created = stamp
        projects.append(NewsProject(folder, str(data.get("headline_1") or folder.name), created))
        if len(projects) >= limit:
            break
    return projects


def load_news_project(project: NewsProject) -> tuple[NewsPackage, Path | None]:
    """Paketi doğrular; ses dosyası pakette kayıtlı hash ile eşleşmiyorsa hata verir."""
    package = parse_news_package(json.loads(project.package_path.read_text(encoding="utf-8")))
    audio_path = project.audio_path
    expected = package.metadata.get("audio_sha256")
    if audio_path and expected:
        actual = hashlib.sha256(audio_path.read_bytes()).hexdigest()
        if actual != expected:
            raise ValueError("Projedeki ses dosyası haber paketiyle eşleşmiyor (hash farklı).")
    return package, audio_path
