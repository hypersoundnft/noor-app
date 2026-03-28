"""Tests for instagram_agent.py — content generation."""
import json
from datetime import date
from unittest.mock import MagicMock

import pytest
from instagram_agent import TOPIC_ROTATION, get_topic_for_date, generate_content


def test_get_topic_for_date_covers_all_three_topics():
    """Three consecutive day-of-year values cover all three topics."""
    results = {get_topic_for_date(date(2026, 1, d)) for d in range(1, 4)}
    assert results == set(TOPIC_ROTATION)


def test_get_topic_for_date_is_deterministic():
    """Same date always returns the same topic."""
    d = date(2026, 3, 27)
    assert get_topic_for_date(d) == get_topic_for_date(d)


def test_generate_content_returns_required_keys():
    """generate_content parses Claude's JSON and returns the three required keys."""
    mock_client = MagicMock()
    mock_client.messages.create.return_value = MagicMock(
        content=[MagicMock(text=json.dumps({
            "image_prompt": "Minimalist mosque at dawn, soft golden light",
            "caption": "Start your day with intention.\n\n#Noor #IslamicLifestyle #Fitrah",
            "topic": "fitrah",
        }))]
    )
    result = generate_content(date(2026, 3, 27), mock_client)
    assert set(result.keys()) >= {"image_prompt", "caption", "topic"}


def test_generate_content_raises_on_invalid_json():
    """generate_content raises json.JSONDecodeError if Claude returns non-JSON."""
    mock_client = MagicMock()
    mock_client.messages.create.return_value = MagicMock(
        content=[MagicMock(text="Sorry, I cannot help with that.")]
    )
    with pytest.raises(json.JSONDecodeError):
        generate_content(date(2026, 3, 27), mock_client)


# ── Image Generation ──────────────────────────────────────────────────────────
from unittest.mock import patch
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
