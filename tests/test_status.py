"""v4.0.0-alpha.6: durum paneli (disk, ElevenLabs kalan karakter, FFmpeg) ve günlük/aylık maliyet defteri."""

import threading
from datetime import date, datetime
from types import SimpleNamespace

import pytest

from elevenlabs.core.api_error import ApiError

from apps.axion_local import ledger, status


@pytest.fixture(autouse=True)
def data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("AXION_DATA_DIR", str(tmp_path))
    return tmp_path


def test_ledger_sums_today_and_this_month(data_dir):
    ledger.add("haber", 0.0046, when=datetime(2026, 9, 26, 10, 0))
    ledger.add("goruntu", 0.0066, when=datetime(2026, 9, 26, 10, 5))
    ledger.add("sahne", None, when=datetime(2026, 9, 26, 10, 6))  # maliyeti bilinmeyen çağrı da sayılır
    ledger.add("ses", 0.0, characters=812, when=datetime(2026, 9, 26, 10, 1))
    ledger.add("haber", 0.01, when=datetime(2026, 9, 2, 9, 0))
    ledger.add("haber", 0.5, when=datetime(2026, 8, 31, 9, 0))  # geçen ay
    (data_dir / ledger.FILENAME).open("a", encoding="utf-8").write("bozuk satır\n")
    spent = ledger.totals(date(2026, 9, 26))
    assert spent["gun"]["usd"] == pytest.approx(0.0112) and spent["gun"]["cagri"] == 3
    assert spent["gun"]["karakter"] == 812 and spent["ay"]["usd"] == pytest.approx(0.0212)
    assert ledger.describe(spent["gun"]) == "$0.011 · 3 çağrı (görüntü analizi $0.007, haber metni $0.005, sahne seçimi $0.000)"


def test_ledger_write_error_does_not_break_work(data_dir, monkeypatch):
    (data_dir / "dosya").write_text("klasör değil", encoding="utf-8")
    monkeypatch.setattr(ledger, "data_dir", lambda: data_dir / "dosya")
    ledger.add("haber", 0.01)  # hata vermez
    assert ledger.totals()["ay"]["cagri"] == 0


class FakeElevenLabs:
    def __init__(self, used=90_000, limit=100_000, fail=False):
        self.calls = 0
        self.used, self.limit, self.fail = used, limit, fail
        self.user = SimpleNamespace(subscription=SimpleNamespace(get=self.get))

    def get(self):
        self.calls += 1
        if self.fail:  # SDK hatasının metni başlıklarla başlar; panel nedeni yazar (v4.1.0-alpha.1)
            raise ApiError(headers={"date": "Sat, 26 Sep 2026"}, status_code=401, body={"detail": {
                "status": "missing_permissions", "message": "The API key is missing the permission user_read"}})
        return SimpleNamespace(character_count=self.used, character_limit=self.limit,
                               next_character_count_reset_unix=datetime(2026, 10, 3, 12).timestamp())


def test_elevenlabs_remaining_is_cached_and_never_blocks():
    client = FakeElevenLabs()
    first = status.elevenlabs("anahtar", client, now=1000.0, wait=True)
    assert first == {"kullanilan": 90_000, "sinir": 100_000, "kalan": 10_000, "yenilenme": "03.10.2026"}
    assert status.elevenlabs("anahtar", client, now=1300.0) == first and client.calls == 1  # 10 dk içinde sorulmaz
    # Eski sonuç: arka planda yenilenir, sayfa beklemez (eski sonucu hemen alır).
    slow = threading.Event()
    client.get = lambda: slow.wait(5) and None
    client.user.subscription.get = client.get
    assert status.elevenlabs("anahtar", client, now=2000.0) == first
    slow.set()
    assert status.elevenlabs(None) == {"hata": "ELEVENLABS_API_KEY yok"}


def test_panel_lines_warn_about_low_characters(monkeypatch):
    status._ELEVENLABS.clear()
    status.elevenlabs("k", FakeElevenLabs(used=95_000), wait=True)
    monkeypatch.setattr(status, "ffmpeg", lambda: {"surum": "7.1", "ffprobe": True, "amd": True})
    ledger.add("haber", 0.004)
    ledger.add("ses", 0.0, characters=1234)
    rows = status.lines("k")
    assert rows[0].startswith("**Disk:**") and "GB boş" in rows[0]
    assert rows[1] == ("⚠️ **ElevenLabs:** 5.000 karakter kaldı / 100.000 · yenilenme 03.10.2026 · "
                       "Axion bugün 1.234, bu ay 1.234 karakter harcadı")
    assert rows[2] == "**FFmpeg:** 7.1 · kodlayıcı AMD donanım (h264_amf)"
    assert rows[3].startswith("**Bugün:** $0.004 · 1 çağrı") and rows[4].startswith("**Bu ay:**")
    status._ELEVENLABS.clear()
    status.elevenlabs("k2", FakeElevenLabs(fail=True), wait=True)
    # Editör (v4.1): "kullanılan kredi yazmıyordu": neden açıkça yazılır, Axion'un harcadığı yine görünür.
    assert status.lines("k2")[1] == ('**ElevenLabs:** kalan karakter okunamadı: API anahtarında "User → Read" izni yok '
                                     "(ElevenLabs sitesi → Developers → API Keys → anahtarı düzenle → izni aç) · "
                                     "Axion bugün 1.234, bu ay 1.234 karakter harcadı")
