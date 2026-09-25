"""v3.3: Video Stüdyosu görüntü analizinin token'ı (editör: dikey videolarda arttı)."""

from __future__ import annotations

import base64
import io
from types import SimpleNamespace

from PIL import Image, ImageDraw

from apps.video_studio.modules import visual_analysis as va


def frame(path, box=None, shift=0):
    image = Image.new("RGB", (640, 1138), (90, 100, 110))
    draw = ImageDraw.Draw(image)
    draw.rectangle((100 + shift, 300, 500 + shift, 900), fill=(200, 180, 40))  # sabit sahne
    if box:
        draw.rectangle(box, fill=(250, 250, 250))  # küçük bir olay (savrulan yaya)
    image.save(path, "JPEG", quality=92)
    return {"path": str(path)}


def test_vertical_frame_goes_to_luna_at_512_px():
    assert va.image_tokens(640, 1138, max_side=10_000) == 864  # eskisi: 20x36 parça x 1,2
    assert va.image_tokens(640, 1138) == 173  # 288x512
    assert va.image_tokens(640, 360) == 173  # yatay: 512x288


def test_image_is_downscaled_before_sending(tmp_path):
    item = frame(tmp_path / "a.jpg")
    url = va.image_data_url(tmp_path / "a.jpg", va.LUNA_IMAGE_MAX_SIDE)
    image = Image.open(io.BytesIO(base64.b64decode(url.split(",", 1)[1])))
    assert max(image.size) == 512 and url.startswith("data:image/jpeg")
    assert item["path"].endswith("a.jpg")


def test_same_looking_frames_are_not_sent_but_small_events_are(tmp_path):
    shot = {"analysis_windows": [
        {"window_id": "s1_w01", "frames": [frame(tmp_path / "1.jpg"), frame(tmp_path / "2.jpg")]},
        {"window_id": "s1_w02", "frames": [frame(tmp_path / "3.jpg"), frame(tmp_path / "4.jpg", box=(300, 150, 360, 210))]},
        {"window_id": "s1_w03", "frames": [frame(tmp_path / "5.jpg", box=(300, 150, 360, 210))]},
    ]}
    other = {"analysis_windows": [{"window_id": "s2_w01", "frames": [frame(tmp_path / "6.jpg")]}]}
    send, copies = va.frames_to_send([shot, other])
    sent = {window["window_id"]: [f["path"][-5:] for f in frames] for window, frames in send}
    # 2 ve 3 = 1'in aynısı; 4'teki küçük olay gönderilir; 5 = 4'ün aynısı → pencere gönderilmez, sonucu kopyalanır.
    assert sent == {"s1_w01": ["1.jpg"], "s1_w02": ["4.jpg"], "s2_w01": ["6.jpg"]}  # başka sahne hep gönderilir
    assert copies == {"s1_w03": "s1_w02"}


def test_copied_window_gets_the_result_of_its_source(tmp_path, monkeypatch):
    shot = {"analysis_windows": [
        {"window_id": "w1", "start_seconds": 0, "end_seconds": 10, "frames": [frame(tmp_path / "1.jpg")]},
        {"window_id": "w2", "start_seconds": 10, "end_seconds": 20, "frames": [frame(tmp_path / "2.jpg")]},
    ]}
    item = va.WindowVisualAnalysis(
        window_id="w1", description="Durak", visual_type="place", editorial_role="context", visible_people=False,
        location="cadde", text_visible=False, visible_text="", subject_left=0, subject_right=1, subject_top=0,
        subject_bottom=1, side_bars=False, confidence=0.8)
    calls = []

    class Fake:
        def __init__(self, **kwargs):
            self.responses = self

        def parse(self, **kwargs):
            calls.append(kwargs)
            return SimpleNamespace(output_parsed=va.VisualAnalysisResponse(windows=[item], images=[]), usage=None)

    monkeypatch.setattr(va, "OpenAI", Fake)
    windows, _, usage = va.analyze_media_with_luna([shot], [], "anahtar")
    assert windows["w2"] == windows["w1"] and usage["skipped_windows"] == 1 and usage["frame_count"] == 1
    assert sum(part["type"] == "input_image" for part in calls[0]["input"][1]["content"]) == 1
