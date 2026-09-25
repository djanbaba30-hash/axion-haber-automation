"""Aynı haber iki cihazda açık mı (editör: bilgisayar ve tablet). Uyarı içindir; kilit değildir.

Her oturum en son hangi haberi açtığını bildirir. Diğer oturumun hâlâ bağlı olup olmadığına Streamlit'in oturum
yöneticisinden bakılır (iç API; streamlit sürümü sabit). Bakılamazsa uyarı çıkmaz.
"""

from __future__ import annotations

import threading

_OPEN: dict[str, str] = {}  # oturum → açık haber
_LOCK = threading.Lock()


def _session_id() -> str | None:
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx

        ctx = get_script_run_ctx()
        return ctx.session_id if ctx else None
    except Exception:  # noqa: BLE001
        return None


def _is_connected(session_id: str) -> bool:
    try:
        from streamlit import runtime

        return runtime.exists() and runtime.get_instance()._session_mgr.is_active_session(session_id)
    except Exception:  # noqa: BLE001
        return False


def open_elsewhere(project_id: str | None) -> bool:
    """Bu oturumun açtığı haberi kaydeder; aynı haber başka bağlı bir oturumda da açıksa True."""
    me = _session_id()
    if me is None:
        return False
    with _LOCK:
        if project_id:
            _OPEN[me] = project_id
        else:
            _OPEN.pop(me, None)
        others = [sid for sid, pid in _OPEN.items() if sid != me and pid == project_id]
    stale = [sid for sid in others if not _is_connected(sid)]
    with _LOCK:
        for sid in stale:
            _OPEN.pop(sid, None)
    return bool(project_id) and len(others) > len(stale)
