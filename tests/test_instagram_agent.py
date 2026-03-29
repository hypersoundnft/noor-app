"""Tests for instagram_agent.py — content generation."""
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


# ── Video Generation ──────────────────────────────────────────────────────────
from instagram_agent import generate_video_clips, concatenate_clips


def test_generate_video_clips_returns_three_bytes_objects():
    """generate_video_clips calls Veo 2 three times and returns 3 bytes objects."""
    mock_client = MagicMock()
    fake_video_bytes = b"FAKEVIDEO"
    mock_operation = MagicMock()
    mock_operation.done = True
    mock_operation.response.generated_videos = [MagicMock(video=MagicMock(video_bytes=fake_video_bytes))]
    mock_client.models.generate_videos.return_value = mock_operation

    clips = generate_video_clips("cinematic mosque dawn", mock_client)

    assert len(clips) == 3
    assert all(c == fake_video_bytes for c in clips)
    assert mock_client.models.generate_videos.call_count == 3


def test_concatenate_clips_produces_file(tmp_path):
    """concatenate_clips writes an MP4 file and returns its path (mocked ffmpeg)."""
    # Write 3 fake "clip" files
    clip_paths = []
    for i in range(3):
        p = tmp_path / f"clip{i}.mp4"
        p.write_bytes(b"FAKE")
        clip_paths.append(p)

    with patch("instagram_agent.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        out_path = concatenate_clips(clip_paths, tmp_path)

    assert out_path == tmp_path / "combined.mp4"
    # Verify ffmpeg was called with concat
    args = mock_run.call_args[0][0]
    assert "ffmpeg" in args
    assert "-f" in args and "concat" in args


# ── Instagram Posting ─────────────────────────────────────────────────────────
from instagram_agent import (
    upload_to_imgbb,
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


from instagram_agent import create_ig_reel_container, wait_for_ig_container


def test_create_ig_reel_container_uses_reels_media_type():
    """create_ig_reel_container sends media_type=REELS and video_url."""
    mock_response = MagicMock()
    mock_response.ok = True
    mock_response.json.return_value = {"id": "container123"}
    with patch("instagram_agent.http_requests.post", return_value=mock_response) as mock_post:
        cid = create_ig_reel_container(
            ig_user_id="12345",
            video_url="https://res.cloudinary.com/noor/video/upload/noor.mp4",
            caption="Bismillah. #Noor",
            access_token="PAGE_TOKEN",
        )
    assert cid == "container123"
    params = mock_post.call_args[1]["params"]
    assert params["media_type"] == "REELS"
    assert "video_url" in params
    assert "image_url" not in params


def test_wait_for_ig_container_returns_when_finished():
    """wait_for_ig_container polls until status_code is FINISHED."""
    mock_response_pending = MagicMock()
    mock_response_pending.json.return_value = {"status_code": "IN_PROGRESS"}
    mock_response_done = MagicMock()
    mock_response_done.json.return_value = {"status_code": "FINISHED"}

    with patch("instagram_agent.http_requests.get", side_effect=[mock_response_pending, mock_response_done]), \
         patch("instagram_agent.time.sleep"):
        wait_for_ig_container("container123", "PAGE_TOKEN")  # should not raise


def test_wait_for_ig_container_raises_on_timeout():
    """wait_for_ig_container raises RuntimeError after too many pending responses."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"status_code": "IN_PROGRESS"}

    with patch("instagram_agent.http_requests.get", return_value=mock_response), \
         patch("instagram_agent.time.sleep"):
        with pytest.raises(RuntimeError, match="timed out"):
            wait_for_ig_container("container123", "PAGE_TOKEN", max_attempts=2)


# ── Voiceover Generation ──────────────────────────────────────────────────────
from instagram_agent import generate_voiceover


def test_generate_voiceover_returns_bytes():
    """generate_voiceover calls Gemini TTS and returns audio bytes."""
    mock_client = MagicMock()
    fake_audio = b"RIFF....WAVEfmt "
    mock_client.models.generate_content.return_value = MagicMock(
        candidates=[MagicMock(content=MagicMock(parts=[
            MagicMock(inline_data=MagicMock(data=fake_audio))
        ]))]
    )
    result = generate_voiceover("Every morning is a gift.", mock_client)
    assert result == fake_audio


def test_generate_voiceover_uses_kore_voice():
    """generate_voiceover uses the Kore voice preset."""
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = MagicMock(
        candidates=[MagicMock(content=MagicMock(parts=[
            MagicMock(inline_data=MagicMock(data=b"audio"))
        ]))]
    )
    generate_voiceover("narration text", mock_client)
    call_kwargs = mock_client.models.generate_content.call_args[1]
    config = call_kwargs["config"]
    voice_name = config.speech_config.voice_config.prebuilt_voice_config.voice_name
    assert voice_name == "Kore"


# ── Cloudinary Upload ─────────────────────────────────────────────────────────
from instagram_agent import upload_to_cloudinary


def test_upload_to_cloudinary_uses_video_resource_type():
    """upload_to_cloudinary uploads with resource_type='video'."""
    with patch("cloudinary.uploader.upload") as mock_upload, \
         patch("cloudinary.config"):
        mock_upload.return_value = {"secure_url": "https://res.cloudinary.com/noor/video/upload/noor.mp4"}
        url = upload_to_cloudinary(b"FAKEVIDEO", "my_cloud", "api_key", "api_secret")

    assert url == "https://res.cloudinary.com/noor/video/upload/noor.mp4"
    call_kwargs = mock_upload.call_args[1]
    assert call_kwargs["resource_type"] == "video"


# ── Video + Audio Merge ───────────────────────────────────────────────────────
from instagram_agent import merge_video_audio


def test_merge_video_audio_calls_ffmpeg(tmp_path):
    """merge_video_audio runs ffmpeg with -shortest and returns output path."""
    video_path = tmp_path / "combined.mp4"
    audio_path = tmp_path / "narration.wav"
    video_path.write_bytes(b"FAKEVIDEO")
    audio_path.write_bytes(b"FAKEAUDIO")

    with patch("instagram_agent.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        out_path = merge_video_audio(video_path, audio_path, tmp_path)

    assert out_path == tmp_path / "final.mp4"
    args = mock_run.call_args[0][0]
    assert "ffmpeg" in args
    assert "-shortest" in args
    assert str(video_path) in args
    assert str(audio_path) in args
