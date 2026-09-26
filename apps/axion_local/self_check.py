"""Açılış kontrolü (bekçi, uygulamadan güncellemeden sonra çalıştırır): yeni sürüm açılıyor mu?

`python -m apps.axion_local.self_check` → 0 = sağlam, 1 = bozuk (bekçi önceki sürüme döner). Bütün Python dosyaları
derlenir, sayfa olmayan modüller içe aktarılır, Haber/Video/Tasarım sayfaları AppTest ile boş bir veri klasöründe bir
kez çizilir (API çağrısı yok, projelere dokunulmaz). Tarayıcı sayfası çizilmez (Brave açılırdı); modülleri içe aktarılır.
"""

from __future__ import annotations

import importlib
import os
import py_compile
import sys
import tempfile
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PACKAGES = ("apps", "shared")
PAGES = ("apps/video_studio/page.py", "apps/design_studio/page.py")  # ilk çizim Haber Stüdyosu (varsayılan sayfa)
DUMMY_SECRETS = {"OPENAI_API_KEY": "sk-kontrol", "ANTHROPIC_API_KEY": "sk-ant-kontrol", "ELEVENLABS_API_KEY": "kontrol"}
TIMEOUT_SECONDS = 180


def _python_files() -> list[Path]:
    files = [ROOT / "axion_app.py", ROOT / "axion_local.py"]
    for package in PACKAGES:
        files += sorted(p for p in (ROOT / package).rglob("*.py") if "__pycache__" not in p.parts)
    return files


def compile_all() -> list[str]:
    errors = []
    for path in _python_files():
        try:
            py_compile.compile(str(path), doraise=True)
        except py_compile.PyCompileError as error:
            errors.append(f"{path.relative_to(ROOT)}: {error.msg.strip()}")
    return errors


def import_modules() -> list[str]:
    errors = []
    for path in _python_files():
        relative = path.relative_to(ROOT)
        if relative.parts[0] not in PACKAGES or path.name == "page.py":
            continue  # sayfalar Streamlit betiğidir (içe aktarılınca çalışır); AppTest ile çizilir
        name = ".".join(relative.with_suffix("").parts).removesuffix(".__init__")
        try:
            importlib.import_module(name)
        except Exception as error:  # noqa: BLE001 — her hata "açılmaz" demek
            errors.append(f"{name}: {error.__class__.__name__}: {error}")
    return errors


def render_pages(script: Path = ROOT / "axion_local.py", pages: tuple[str, ...] = PAGES) -> list[str]:
    """Uygulamayı AppTest ile çizer; sayfalardaki hata (exception) listesi."""
    from streamlit.testing.v1 import AppTest

    from apps.axion_local import update_check

    update_check.status = lambda now=None: None  # kontrol sırasında repoya sorulmaz
    at = AppTest.from_file(str(script), default_timeout=TIMEOUT_SECONDS)
    for key, value in DUMMY_SECRETS.items():
        at.secrets[key] = value
    errors = []
    for page in (None, *pages):
        try:
            if page:
                at.switch_page(page)
            at.run()
        except Exception as error:  # noqa: BLE001 — zaman aşımı, betik yüklenemedi
            errors.append(f"{page or 'Haber Stüdyosu'}: {error.__class__.__name__}: {error}")
            break
        for exception in at.exception:
            errors.append(f"{page or 'Haber Stüdyosu'}: {exception.value}")
    return errors


def run() -> list[str]:
    errors = compile_all()
    if errors:
        return errors  # sözdizimi hatası varsa gerisini denemeye gerek yok
    with tempfile.TemporaryDirectory(prefix="axion_kontrol_", ignore_cleanup_errors=True) as folder:  # Windows kilidi
        os.environ["AXION_DATA_DIR"] = str(Path(folder) / "data")  # gerçek projelere/ayarlara dokunulmaz
        inbox = Path(folder) / "Downloads"
        inbox.mkdir()
        os.environ["AXION_INBOX_DIR"] = str(inbox)
        errors = import_modules()
        if not errors:
            errors = render_pages()
    return errors


def main() -> int:
    for stream in (sys.stdout, sys.stderr):  # Windows'ta çıktı bekçiye borudan gider (cp1252): Türkçe harf çökertmesin
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(errors="replace")
    os.chdir(ROOT)
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    try:
        errors = run()
    except Exception:  # noqa: BLE001
        errors = [traceback.format_exc()]
    if errors:
        print("Axion acilis kontrolu BASARISIZ:")
        for error in errors:
            print(" -", error[:2000])
        return 1
    print("Axion acilis kontrolu tamam.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
