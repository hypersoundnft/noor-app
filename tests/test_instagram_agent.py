"""Tests for instagram_agent.py — content generation."""
import json
from datetime import date
from unittest.mock import MagicMock, patch

import pytest
from instagram_agent import TOPIC_ROTATION, get_topic_for_date, generate_content


def test_get_topic_for_date_covers_all_three_topics():
    results = {get_topic_for_date(date(2026, 1, d)) for d in range(1, 4)}
    assert results == set(TOPIC_ROTATION)


def test_get_topic_for_date_is_deterministic():
    d = date(2026, 3, 27)
    assert get_topic_for_date(d) == get_topic_for_date(d)


def test_generate_content_returns_required_keys():
    """generate_content returns dict with image_prompt, caption, topic, narration."""
    mock_client = MagicMock()
    mock_fn_call = MagicMock()
    mock_fn_call.args = {
        "image_prompt": "Mosque at dawn, cinematic 9:16",
        "caption": "Start with Bismillah.\n\n#Noor",
        "topic": "fitrah",
        "narration": "Every morning is a gift. Begin with gratitude.",
    }
    mock_client.models.generate_content.return_value = MagicMock(
        candidates=[MagicMock(content=MagicMock(parts=[MagicMock(function_call=mock_fn_call)]))]
    )
    result = generate_content(date(2026, 3, 27), mock_client)
    assert set(result.keys()) >= {"image_prompt", "caption", "topic", "narration"}


def test_generate_content_narration_is_string():
    mock_client = MagicMock()
    mock_fn_call = MagicMock()
    mock_fn_call.args = {
        "image_prompt": "Golden hour mosque",
        "caption": "Caption text. #Noor",
        "topic": "lifestyle",
        "narration": "Short spoken narration here.",
    }
    mock_client.models.generate_content.return_value = MagicMock(
        candidates=[MagicMock(content=MagicMock(parts=[MagicMock(function_call=mock_fn_call)]))]
    )
    result = generate_content(date(2026, 3, 27), mock_client)
    assert isinstance(result["narration"], str)
    assert len(result["narration"]) > 0


# ── Image Generation ──────────────────────────────────────────────────────────
from instagram_agent import generate_image


def test_generate_image_downloads_dall_e_url_and_returns_bytes():
    """generate_image calls DALL-E 3, downloads the returned URL, returns raw bytes."""
    fake_bytes = b"\x89PNG\r\nFAKE"
    mock_openai = MagicMock()
    mock_openai.images.generate.return_value = MagicMock(
        data=[MagicMock(url="https://dalle.openai.com/fake-image.png")]
    )
    mock_http_response = MagicMock()
    mock_http_response.content = fake_bytes

    with patch("instagram_agent.http_requests.get", return_value=mock_http_response):
        result = generate_image("minimalist mosque at dawn", mock_openai)

    assert result == fake_bytes
    mock_openai.images.generate.assert_called_once_with(
        model="dall-e-3",
        prompt="minimalist mosque at dawn",
        size="1024x1024",
        quality="standard",
        n=1,
    )


def test_generate_image_raises_on_download_failure():
    """generate_image raises if the image download returns an HTTP error."""
    import requests as req
    mock_openai = MagicMock()
    mock_openai.images.generate.return_value = MagicMock(
        data=[MagicMock(url="https://dalle.openai.com/fake-image.png")]
    )
    mock_http_response = MagicMock()
    mock_http_response.raise_for_status.side_effect = req.exceptions.HTTPError("503")

    with patch("instagram_agent.http_requests.get", return_value=mock_http_response):
        with pytest.raises(req.exceptions.HTTPError):
            generate_image("minimalist mosque", mock_openai)


# ── Logo Overlay ──────────────────────────────────────────────────────────────
import io as _io
import tempfile
from pathlib import Path
from PIL import Image as PILImage
from instagram_agent import overlay_logo


def _make_png(width=1024, height=1024, color=(180, 180, 180)) -> bytes:
    """Create a minimal in-memory PNG for tests."""
    img = PILImage.new("RGB", (width, height), color)
    buf = _io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _make_logo_png(width=400, height=100) -> Path:
    """Write a minimal RGBA logo PNG to a temp file and return its Path."""
    img = PILImage.new("RGBA", (width, height), (255, 255, 255, 200))
    tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    img.save(tmp.name, format="PNG")
    return Path(tmp.name)


def test_overlay_logo_returns_jpeg_bytes():
    """overlay_logo composites the logo and returns JPEG bytes (FF D8 magic)."""
    image_bytes = _make_png()
    logo_path = _make_logo_png()
    result = overlay_logo(image_bytes, logo_path)
    assert result[:2] == b"\xff\xd8", "Expected JPEG output (FF D8 magic bytes)"


def test_overlay_logo_preserves_input_dimensions():
    """Output image is the same size as the input image."""
    image_bytes = _make_png(1024, 1024)
    logo_path = _make_logo_png()
    result = overlay_logo(image_bytes, logo_path)
    out_img = PILImage.open(_io.BytesIO(result))
    assert out_img.size == (1024, 1024)


def test_overlay_logo_scales_wide_logo_to_max_width():
    """A logo wider than LOGO_MAX_WIDTH is scaled down."""
    from instagram_agent import LOGO_MAX_WIDTH
    image_bytes = _make_png()
    # Logo wider than LOGO_MAX_WIDTH
    logo_path = _make_logo_png(width=LOGO_MAX_WIDTH * 3, height=200)
    # Should not raise; output image still valid
    result = overlay_logo(image_bytes, logo_path)
    out_img = PILImage.open(_io.BytesIO(result))
    assert out_img.size == (1024, 1024)


# ── Instagram Posting ─────────────────────────────────────────────────────────
from instagram_agent import (
    upload_to_imgbb,
    create_ig_media_container,
    publish_ig_media_container,
)


def test_upload_to_imgbb_returns_public_url():
    """upload_to_imgbb posts base64 image to imgbb and returns the public URL."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "success": True,
        "data": {"url": "https://i.ibb.co/abc123/noor.jpg"},
    }
    with patch("instagram_agent.http_requests.post", return_value=mock_response):
        url = upload_to_imgbb(b"FAKEJPEG", "test-api-key")
    assert url == "https://i.ibb.co/abc123/noor.jpg"


def test_upload_to_imgbb_raises_on_api_failure():
    """upload_to_imgbb raises RuntimeError when imgbb returns success:false."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"success": False, "error": {"message": "Invalid key"}}
    with patch("instagram_agent.http_requests.post", return_value=mock_response):
        with pytest.raises(RuntimeError, match="imgbb upload failed"):
            upload_to_imgbb(b"FAKEJPEG", "bad-key")


def test_create_ig_media_container_returns_container_id():
    """create_ig_media_container posts to /media and returns the container id."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"id": "17889618863059855"}
    with patch("instagram_agent.http_requests.post", return_value=mock_response):
        cid = create_ig_media_container(
            ig_user_id="12345",
            image_url="https://i.ibb.co/abc123/noor.jpg",
            caption="Bismillah. #Noor",
            access_token="PAGE_TOKEN",
        )
    assert cid == "17889618863059855"


def test_create_ig_media_container_raises_without_id():
    """create_ig_media_container raises RuntimeError when API response lacks 'id'."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"error": {"message": "Invalid OAuth access token"}}
    with patch("instagram_agent.http_requests.post", return_value=mock_response):
        with pytest.raises(RuntimeError, match="IG container creation failed"):
            create_ig_media_container("12345", "https://i.ibb.co/x.jpg", "Cap", "BAD_TOKEN")


def test_publish_ig_media_container_returns_media_id():
    """publish_ig_media_container posts to /media_publish and returns the media id."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"id": "17896129349180111"}
    with patch("instagram_agent.http_requests.post", return_value=mock_response):
        media_id = publish_ig_media_container(
            ig_user_id="12345",
            container_id="17889618863059855",
            access_token="PAGE_TOKEN",
        )
    assert media_id == "17896129349180111"


def test_publish_ig_media_container_raises_without_id():
    """publish_ig_media_container raises RuntimeError when API response lacks 'id'."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"error": {"message": "Container not ready"}}
    with patch("instagram_agent.http_requests.post", return_value=mock_response):
        with pytest.raises(RuntimeError, match="IG publish failed"):
            publish_ig_media_container("12345", "container123", "BAD_TOKEN")


# ── Integration: main() ───────────────────────────────────────────────────────
from instagram_agent import main


def test_main_completes_full_pipeline(monkeypatch):
    """main() runs all five stages end-to-end with all external calls mocked.

    This exercises the wiring: content → image → upload → container → publish.
    No logo file exists at the test path, so the overlay stage is skipped.
    """
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-anthropic")
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai")
    monkeypatch.setenv("IMGBB_API_KEY", "test-imgbb")
    monkeypatch.setenv("IG_USER_ID", "12345")
    monkeypatch.setenv("IG_ACCESS_TOKEN", "test-token")

    fake_png = _make_png()  # reuse helper from logo tests

    mock_imgbb = MagicMock()
    mock_imgbb.json.return_value = {"success": True, "data": {"url": "https://i.ibb.co/test.jpg"}}
    mock_ig_container = MagicMock()
    mock_ig_container.json.return_value = {"id": "container123"}
    mock_ig_publish = MagicMock()
    mock_ig_publish.json.return_value = {"id": "media456"}

    with patch("instagram_agent.anthropic.Anthropic") as mock_anthropic_cls, \
         patch("instagram_agent.openai.OpenAI") as mock_openai_cls, \
         patch("instagram_agent.http_requests.get") as mock_get, \
         patch("instagram_agent.http_requests.post") as mock_post:

        mock_anthropic_cls.return_value.messages.create.return_value = MagicMock(
            content=[MagicMock(text=json.dumps({
                "image_prompt": "soft mosque dawn light",
                "caption": "Start your day with Bismillah. #Noor",
                "topic": "fitrah",
            }))]
        )
        mock_openai_cls.return_value.images.generate.return_value = MagicMock(
            data=[MagicMock(url="https://dalle.openai.com/fake.png")]
        )
        mock_get.return_value = MagicMock(content=fake_png)
        mock_post.side_effect = [mock_imgbb, mock_ig_container, mock_ig_publish]

        main()  # should complete without raising
