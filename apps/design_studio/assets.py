"""Şablon varlıkları: arka planlar ve yazı tipleri; editörün uygulamadan eklediği dosyalar ve GitHub'a yükleme.

- Repodakiler: `assets/sablon/arka_plan_N.png`, `assets/sablon/fontlar/*.ttf|otf`.
- Uygulamadan eklenenler önce yerelde `data/varliklar/` altına yazılır (git dışında: güncelleme çakışmaz), anında
  kullanılır. `GITHUB_TOKEN` tanımlıysa aynı dosya repoya da yüklenir; sonraki güncellemede repodan gelir
  (aynı adlı dosyada repodaki geçerli).
"""

from __future__ import annotations

import base64
import json
import os
import re
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path

from shared.fonts import user_font_dir

ROOT = Path(__file__).resolve().parents[2]
TEMPLATE_DIR = ROOT / "assets" / "sablon"
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
FONT_EXTENSIONS = {".ttf", ".otf"}
# Arka plan sırası bu iş gününde 1'den başlar; sonra her gün bir sonraki (sonuncudan sonra yine 1).
BACKGROUND_FIRST_DAY = date(2026, 9, 24)
DEFAULT_REPO = "djanbaba30-hash/axion-haber-automation"


def user_background_dir() -> Path:
    return Path(os.environ.get("AXION_DATA_DIR") or ROOT / "data") / "varliklar" / "arka_planlar"


def _number(path: Path) -> tuple[int, str]:
    match = re.search(r"(\d+)", path.stem)
    return (int(match.group(1)) if match else 10**6, path.name)


def backgrounds() -> list[Path]:
    """Sıralı arka planlar: repodakiler (arka_plan_1, 2, ...) sonra uygulamadan eklenenler; aynı ad bir kez."""
    found: dict[str, Path] = {}
    for folder, pattern in ((TEMPLATE_DIR, "arka_plan_*"), (user_background_dir(), "*")):
        if folder.is_dir():
            for path in sorted(folder.glob(pattern), key=_number):
                if path.suffix.lower() in IMAGE_EXTENSIONS:
                    found.setdefault(path.name, path)
    return list(found.values())


def background_for_day(day: date) -> Path:
    items = backgrounds()
    if not items:
        raise FileNotFoundError("Arka plan bulunamadı: assets/sablon/arka_plan_1.png ...")
    return items[(day - BACKGROUND_FIRST_DAY).days % len(items)]


def background_by_name(name: str | None, day: date) -> Path:
    """Editörün seçtiği arka plan (dosya adı); yoksa günün arka planı."""
    if name:
        for path in backgrounds():
            if path.name == name:
                return path
    return background_for_day(day)


def _safe_name(name: str) -> str:
    table = str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosuCGIOSU")
    stem, suffix = Path(name).stem.translate(table), Path(name).suffix.lower()
    stem = re.sub(r"[^A-Za-z0-9_-]+", "_", stem).strip("_") or "dosya"
    return stem[:60] + suffix


def next_background_name(suffix: str) -> str:
    numbers = [_number(p)[0] for p in backgrounds() if _number(p)[0] < 10**6]
    return f"arka_plan_{max(numbers, default=0) + 1}{suffix.lower()}"


def save_asset(kind: str, filename: str, content: bytes) -> tuple[Path, str]:
    """Dosyayı yerel varlık klasörüne yazar. Döndürür: (yerel yol, repodaki yol)."""
    suffix = Path(filename).suffix.lower()
    if kind == "font":
        if suffix not in FONT_EXTENSIONS:
            raise ValueError("Yazı tipi .ttf veya .otf olmalı.")
        name = _safe_name(filename)
        folder, repo_path = user_font_dir(), f"assets/sablon/fontlar/{name}"
    elif kind == "arka_plan":
        if suffix not in IMAGE_EXTENSIONS:
            raise ValueError("Arka plan .png, .jpg veya .webp olmalı.")
        name = next_background_name(suffix)
        folder, repo_path = user_background_dir(), f"assets/sablon/{name}"
    else:
        raise ValueError(f"Bilinmeyen varlık türü: {kind}")
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / name
    path.write_bytes(content)
    return path, repo_path


def github_repo() -> str:
    """Yerel kopyanın GitHub adresinden 'sahip/repo' (bulunamazsa varsayılan)."""
    config = ROOT / ".git" / "config"
    try:
        match = re.search(r"github\.com[:/]([^/\s]+/[^/\s]+?)(?:\.git)?\s", config.read_text(encoding="utf-8") + "\n")
    except OSError:
        match = None
    return match.group(1) if match else DEFAULT_REPO


def upload_to_github(repo_path: str, content: bytes, token: str, repo: str | None = None, branch: str = "main") -> str:
    """Dosyayı GitHub'a (contents API) yükler; varsa günceller. Commit adresini döndürür."""
    repo = repo or github_repo()
    url = f"https://api.github.com/repos/{repo}/contents/{repo_path}"
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json", "User-Agent": "axion-local"}
    sha = None
    try:
        with urllib.request.urlopen(urllib.request.Request(f"{url}?ref={branch}", headers=headers), timeout=30) as response:
            sha = json.loads(response.read()).get("sha")
    except urllib.error.HTTPError as error:
        if error.code != 404:
            raise RuntimeError(f"GitHub'a erişilemedi ({error.code}). Anahtarın bu repoya yazma izni var mı?") from error
    body = {"message": f"Tasarım Stüdyosu'ndan varlık: {repo_path}", "content": base64.b64encode(content).decode(), "branch": branch}
    if sha:
        body["sha"] = sha
    request = urllib.request.Request(url, data=json.dumps(body).encode(), headers=headers, method="PUT")
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            return json.loads(response.read()).get("commit", {}).get("html_url", "")
    except urllib.error.HTTPError as error:
        raise RuntimeError(f"GitHub yüklemesi başarısız ({error.code}).") from error

