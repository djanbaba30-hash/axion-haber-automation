"""Tarayıcı sayfasının kayıtlı girişleri (site → kullanıcı adı + şifre): `data/tarayici_girisler.json`.

Editör bir kez giriş yapınca kaydedilir, sonraki girişlerde kutular kendiliğinden dolar. Şifre Windows'ta DPAPI ile
(yalnızca aynı Windows kullanıcısının çözebileceği biçimde) şifrelenir; başka sistemlerde (testler) base64'tür.
Şifre hiçbir zaman tablete gönderilmez: yalnızca bilgisayardaki tarayıcıya yazılır.
"""

from __future__ import annotations

import base64
import json
import sys
import threading
from pathlib import Path
from urllib.parse import urlparse

FILENAME = "tarayici_girisler.json"
_LOCK = threading.Lock()


def site_of(url: str) -> str:
    """Girişin anahtarı: alan adı (www. olmadan)."""
    host = (urlparse(url).hostname or "").lower()
    return host[4:] if host.startswith("www.") else host


# ---------------------------------------------------------------------------------- Windows DPAPI (ctypes)
def _dpapi(data: bytes, protect: bool) -> bytes:
    import ctypes
    from ctypes import wintypes

    class Blob(ctypes.Structure):
        _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]

    buffer = ctypes.create_string_buffer(data, len(data))
    source, target = Blob(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_char))), Blob()
    crypt32, kernel32 = ctypes.windll.crypt32, ctypes.windll.kernel32
    function = crypt32.CryptProtectData if protect else crypt32.CryptUnprotectData
    if not function(ctypes.byref(source), None, None, None, None, 0, ctypes.byref(target)):
        raise OSError("Windows şifrelemesi başarısız")
    try:
        return ctypes.string_at(target.pbData, target.cbData)
    finally:
        kernel32.LocalFree(target.pbData)


def _seal(password: str) -> str:
    raw = password.encode("utf-8")
    if sys.platform == "win32":
        return "dpapi:" + base64.b64encode(_dpapi(raw, True)).decode("ascii")
    return "b64:" + base64.b64encode(raw).decode("ascii")


def _open(sealed: str) -> str | None:
    try:
        kind, _, body = sealed.partition(":")
        raw = base64.b64decode(body)
        if kind == "dpapi":
            return _dpapi(raw, False).decode("utf-8") if sys.platform == "win32" else None
        return raw.decode("utf-8") if kind == "b64" else None
    except (ValueError, OSError, UnicodeDecodeError):
        return None


class Logins:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._cache: tuple[int, dict[str, dict[str, str]]] | None = None  # (dosya zamanı, içerik)

    def _read(self) -> dict[str, dict[str, str]]:
        # Tarayıcı ekranı saniyede birkaç kez sorar: dosya değişmedikçe yeniden okunmaz.
        try:
            stamp = self.path.stat().st_mtime_ns
            if self._cache is None or self._cache[0] != stamp:
                data = json.loads(self.path.read_text(encoding="utf-8"))
                entries = {k: v for k, v in data.items() if isinstance(v, dict)} if isinstance(data, dict) else {}
                self._cache = (stamp, entries)
        except (OSError, ValueError):
            return {}
        return dict(self._cache[1])

    def get(self, site: str) -> tuple[str, str] | None:
        entry = self._read().get(site)
        if not entry:
            return None
        password = _open(str(entry.get("password", "")))
        return (str(entry.get("username", "")), password) if password else None

    def save(self, site: str, username: str, password: str) -> None:
        with _LOCK:
            data = self._read()
            data[site] = {"username": username, "password": _seal(password)}
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def delete(self, site: str) -> None:
        with _LOCK:
            data = self._read()
            if data.pop(site, None) is not None:
                self.path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def sites(self) -> list[tuple[str, str]]:
        """(site, kullanıcı adı) listesi: kenar çubuğunda gösterilir (şifre değil)."""
        return sorted((site, str(entry.get("username", ""))) for site, entry in self._read().items())
