"""Axion projeleri: editörün bilgisayarındaki kalıcı proje klasörü ve medya gelen kutusu.

Her proje bir klasördür:
    data/projects/<YYYYMMDD-HHMMSS>_<başlık>/
        news_package.json   Haber Stüdyosu çıktısı (NewsPackage, ses hash'i metadata'da)
        tts.mp3             TTS sesi
        media_library.json  Video Studio medya analizi (Luna)
        edit_project.json   Video Studio EditProject
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import logging
import shutil
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from shared.news_package import NewsPackage, parse_news_package

ROOT = Path(__file__).resolve().parents[2]

VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v"}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
MEDIA_EXTENSIONS = VIDEO_EXTENSIONS | IMAGE_EXTENSIONS

PACKAGE_FILENAME = "news_package.json"
AUDIO_FILENAME = "tts.mp3"
MEDIA_LIBRARY_FILENAME = "media_library.json"
EDIT_PROJECT_FILENAME = "edit_project.json"
ROUGH_CUT_FILENAME = "kaba_kurgu.mp4"


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
    def id(self) -> str:
        return self.folder.name

    @property
    def package_path(self) -> Path:
        return self.folder / PACKAGE_FILENAME

    @property
    def audio_path(self) -> Path | None:
        path = self.folder / AUDIO_FILENAME
        return path if path.exists() else None

    @property
    def has_media(self) -> bool:
        return (self.folder / MEDIA_LIBRARY_FILENAME).exists()

    @property
    def label(self) -> str:
        parts = [self.created_at, self.headline, "ses var" if self.audio_path else "ses yok"]
        if self.has_media:
            parts.append("medya hazır")
        return " · ".join(parts)


def save_news_project(
    package: NewsPackage,
    audio_bytes: bytes | None,
    base_dir: Path | None = None,
    now: datetime | None = None,
    folder: Path | None = None,
) -> Path:
    """Haber paketini ve TTS sesini proje klasörüne yazar; ses hash'i pakete eklenir.

    `folder` verilirse o proje güncellenir (medya analizi korunur, eski edit projesi silinir);
    verilmezse yeni proje açılır.
    """
    if folder is None:
        base_dir = base_dir or projects_dir()
        stamp = (now or datetime.now()).strftime("%Y%m%d-%H%M%S")
        folder = base_dir / f"{stamp}_{_slug(package.headline_1)}"
        folder.mkdir(parents=True, exist_ok=False)

    metadata = {k: v for k, v in package.metadata.items() if k not in {"audio_sha256", "audio_filename"}}
    audio_path = folder / AUDIO_FILENAME
    if audio_bytes:
        audio_path.write_bytes(audio_bytes)
        metadata["audio_sha256"] = hashlib.sha256(audio_bytes).hexdigest()
        metadata["audio_filename"] = AUDIO_FILENAME
    else:
        audio_path.unlink(missing_ok=True)
    (folder / EDIT_PROJECT_FILENAME).unlink(missing_ok=True)
    (folder / ROUGH_CUT_FILENAME).unlink(missing_ok=True)
    stored = package.model_copy(update={"metadata": metadata})
    (folder / PACKAGE_FILENAME).write_text(stored.model_dump_json(indent=2), encoding="utf-8")
    return folder


def _project_from_folder(folder: Path) -> NewsProject | None:
    package_path = folder / PACKAGE_FILENAME
    if not package_path.is_file():
        return None
    try:
        data = json.loads(package_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    stamp = folder.name.split("_", 1)[0]
    try:
        created = datetime.strptime(stamp, "%Y%m%d-%H%M%S").strftime("%d.%m.%Y %H:%M")
    except ValueError:
        created = stamp
    return NewsProject(folder, str(data.get("headline_1") or folder.name), created)


logger = logging.getLogger(__name__)

DAY_START_HOUR = 2  # Uygulama her gün 02:00'de (bilgisayarın saatiyle) "yeni gün"e başlar.


def work_day_start(now: datetime | None = None) -> datetime:
    """İçinde bulunulan iş gününün başlangıcı: bugün 02:00, saat 02:00'den önceyse dün 02:00."""
    now = now or datetime.now()
    start = now.replace(hour=DAY_START_HOUR, minute=0, second=0, microsecond=0)
    return start if now >= start else start - timedelta(days=1)


KEEP_DAYS = 3  # Haberler en fazla 3 iş günü saklanır (bugün + önceki 2 gün; editör kararı).


def delete_old_projects(base_dir: Path | None = None, now: datetime | None = None, keep_days: int = KEEP_DAYS) -> list[str]:
    """Saklama süresi dolan proje klasörlerini siler (ses, analiz, kurgu, video, önizlemeler dahil).

    Yalnızca proje adı biçimindeki (YYYYMMDD-HHMMSS_...) klasörlere dokunur; İndirilenler'deki kaynak videolar silinmez.
    """
    base_dir = base_dir or projects_dir()
    if not base_dir.is_dir():
        return []
    cutoff = work_day_start(now) - timedelta(days=keep_days - 1)
    deleted = []
    for folder in base_dir.iterdir():
        created = _folder_time(folder) if folder.is_dir() else None
        if created is None or created >= cutoff:
            continue
        try:
            shutil.rmtree(folder)
        except OSError as error:
            # Ör. Windows'ta açık bir video dosyası: sessizce geçme, günlüğe yaz (data/axion.log); ertesi gün yeniden denenir.
            logger.warning("Eski proje silinemedi: %s (%s)", folder.name, error)
        if not folder.exists():
            deleted.append(folder.name)
            logger.info("Eski proje silindi (3 gün saklama): %s", folder.name)
    return deleted


def _folder_time(folder: Path) -> datetime | None:
    try:
        return datetime.strptime(folder.name.split("_", 1)[0], "%Y%m%d-%H%M%S")
    except ValueError:
        return None


def list_news_projects(base_dir: Path | None = None, limit: int = 30, since: datetime | None = None) -> list[NewsProject]:
    """Projeler, yeniden eskiye. `since` verilirse yalnızca o andan sonra kaydedilenler."""
    base_dir = base_dir or projects_dir()
    if not base_dir.is_dir():
        return []
    projects = []
    for folder in sorted(base_dir.iterdir(), reverse=True):
        if since is not None and (_folder_time(folder) or datetime.min) < since:
            continue
        project = _project_from_folder(folder) if folder.is_dir() else None
        if project:
            projects.append(project)
        if len(projects) >= limit:
            break
    return projects


def get_news_project(project_id: str, base_dir: Path | None = None) -> NewsProject | None:
    folder = (base_dir or projects_dir()) / project_id
    return _project_from_folder(folder) if folder.is_dir() else None


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


def save_project_json(project: NewsProject, filename: str, data: Any) -> Path:
    path = project.folder / filename
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_project_json(project: NewsProject, filename: str) -> Any | None:
    path = project.folder / filename
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
