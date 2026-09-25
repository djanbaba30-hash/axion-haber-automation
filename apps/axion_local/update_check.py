"""Güncelleme var mı (editör: "PC'de güncellemeyi unutursam görünsün"): bilgisayardaki sürüm (git HEAD) repodaki
`main` ile karşılaştırılır. `git ls-remote` yalnız son commit numarasını sorar (indirme yok); arka planda, en çok
30 dakikada bir. Git yoksa, internet yoksa ya da repo değilse hiçbir şey gösterilmez (sayfa hiç beklemez).
"""

from __future__ import annotations

import os
import subprocess
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BRANCH = "main"
INTERVAL_SECONDS = 30 * 60
TIMEOUT_SECONDS = 15
PULL_TIMEOUT_SECONDS = 180
RESTART_CODE = 3  # bekçiye: "güncellendi, paketleri kontrol et ve hemen yeniden başlat" (çökme sayılmaz)
SUPERVISOR_ENV = "AXION_BEKCI"  # bekçi (windows/axion_calistir.ps1) Axion'u başlatırken koyar

_lock = threading.Lock()
_state: dict[str, object] = {"checked": 0.0, "status": None, "running": False}


def _git(*args: str, timeout: float = TIMEOUT_SECONDS) -> str:
    result = subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, text=True, timeout=timeout,
        env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},  # şifre sorup beklemesin
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),  # Windows'ta konsol penceresi açılmasın
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip())
    return result.stdout.strip()


def check() -> str | None:
    """"guncel", "var" ya da None (kontrol edilemedi)."""
    try:
        local = _git("rev-parse", "HEAD")
        remote = _git("ls-remote", "origin", f"refs/heads/{BRANCH}").split()
    except (OSError, RuntimeError, subprocess.SubprocessError):
        return None
    if not remote:
        return None
    return "guncel" if remote[0] == local else "var"


def supervised() -> bool:
    """Axion bekçiyle mi çalışıyor (masaüstü simgesi): ancak o zaman kendini yeniden başlatabilir."""
    return os.environ.get(SUPERVISOR_ENV) == "1"


def apply_update() -> str | None:
    """Yeni sürümü indirir (`git pull --ff-only`, guncelle.bat'ın yaptığı gibi). Hata yoksa None, varsa hata metni.
    Paketleri (pip) bekçi yeniden başlatmadan önce kurar: çalışan Python'un dosyaları Windows'ta kilitlidir."""
    try:
        _git("pull", "--ff-only", timeout=PULL_TIMEOUT_SECONDS)
    except (OSError, RuntimeError, subprocess.SubprocessError) as error:
        return str(error).strip()[-500:] or error.__class__.__name__
    with _lock:
        _state.update(status="guncel", checked=time.monotonic())
    return None


def _run(started: float) -> None:
    status = check()
    with _lock:
        _state.update(status=status, checked=started, running=False)


def status(now: float | None = None) -> str | None:
    """Son bilinen durum; süresi dolduysa arka planda yeniden kontrol başlatır (beklemez)."""
    return _status(now)


def _status(now: float | None = None) -> str | None:
    now = time.monotonic() if now is None else now
    with _lock:
        due = not _state["checked"] or now - float(_state["checked"]) >= INTERVAL_SECONDS
        if due and not _state["running"]:
            _state["running"] = True
            threading.Thread(target=_run, args=(now,), daemon=True, name="axion-guncelleme").start()
        return _state["status"]  # type: ignore[return-value]


def label(value: str | None) -> str | None:
    if value == "guncel":
        return "🟢 Axion güncel"
    if value == "var":
        return "🔴 Güncelleme var"
    return None


# Yeniden başlatmadan sonra sayfa kendiliğinden yenilensin: Streamlit sunucuya yeniden bağlanır ama sayfayı yeniden
# çizmez (tablet dokunuş beklerdi). Sunucu kapanıp yeniden açılınca (sağlık adresi) sayfa yenilenir; 2 dk'da olmazsa da.
RELOAD_JS = """
export default function () {
  if (window.__axionYenidenYukle) return;
  window.__axionYenidenYukle = true;
  const began = Date.now();
  let wentDown = false;
  const check = async () => {
    let up = false;
    try { up = (await fetch('/_stcore/health', { cache: 'no-store' })).ok; } catch (e) { up = false; }
    if (!up) wentDown = true;
    if ((wentDown && up) || Date.now() - began > 120000) { window.location.reload(); return; }
    setTimeout(check, 1000);
  };
  setTimeout(check, 2000);
}
"""
_reload_component = None


def reload_when_back() -> None:
    import streamlit as st
    from streamlit.components.v2 import get_bidi_component_manager

    global _reload_component
    name = "axion_yeniden_yukle"
    if _reload_component is None or get_bidi_component_manager().get(name) is None:
        _reload_component = st.components.v2.component(name, html="<span></span>", js=RELOAD_JS)
    _reload_component(key="axion_yeniden_yukle")
