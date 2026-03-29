# Video Reels Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the static image Instagram pipeline with AI-generated video Reels: Gemini generates content, Veo 2 generates video clips, Gemini TTS narrates, ffmpeg merges, posted as an Instagram Reel.

**Architecture:** `instagram_agent.py` is rewritten function-by-function. Claude/Anthropic is removed entirely; all AI runs through `google-genai` with one `GEMINI_API_KEY`. Temp files are managed with `tempfile.TemporaryDirectory` so GitHub Actions runners stay clean.

**Tech Stack:** `google-genai>=1.0.0`, `cloudinary>=1.36.0`, `requests`, `ffmpeg` (pre-installed on ubuntu-latest), `Pillow` (kept for logo — not used in this feature but already in requirements)

---

## File Map

| File | Change |
|------|--------|
| `instagram_agent.py` | Full rewrite of all functions |
| `tests/test_instagram_agent.py` | Update all tests to match new signatures |
| `requirements.txt` | Remove `anthropic` |
| `.github/workflows/instagram-post.yml` | Remove `ANTHROPIC_API_KEY`, bump timeout to 20 min |

---

## Task 1: Content Generation — Claude → Gemini Function Calling

**Files:**
- Modify: `instagram_agent.py` (replace `generate_content`, `_POST_TOOL`, `SYSTEM_PROMPT`, imports)
- Modify: `tests/test_instagram_agent.py` (update content generation tests)

- [ ] **Step 1: Write failing tests for new `generate_content` signature**

In `tests/test_instagram_agent.py`, replace the existing `test_generate_content_*` tests:

```python
from unittest.mock import MagicMock, patch
from datetime import date
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
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd /Users/yp/noor-website && python -m pytest tests/test_instagram_agent.py::test_generate_content_returns_required_keys -v
```

Expected: `ImportError` or `AssertionError` (function signature mismatch)

- [ ] **Step 3: Rewrite content generation in `instagram_agent.py`**

Replace the top of `instagram_agent.py` (imports through `generate_content`):

```python
"""Daily Instagram post agent for the Noor brand."""

import io
import os
import subprocess
import tempfile
import time
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from google import genai as google_genai
from google.genai import types as google_types
import requests as http_requests
from PIL import Image

# ── Content Generation ────────────────────────────────────────────────────────

TOPIC_ROTATION = ["fitrah", "halal_lens", "lifestyle"]

SYSTEM_PROMPT = """You are the lead content strategist for 'Noor', a modern Islamic lifestyle brand and Halal food scanner. Your tone is encouraging, modern, minimalistic, and trustworthy.

Generate a concept for an Instagram Reel post on the given topic.

Topic definitions:
- fitrah: A daily Dua, Quranic reflection, or spiritual reminder
- halal_lens: A hidden Haram ingredient to watch out for in everyday food or cosmetic products
- lifestyle: A modern Muslim lifestyle tip (productivity, wellness, mindful habits)"""

_POST_TOOL = google_types.Tool(
    function_declarations=[
        google_types.FunctionDeclaration(
            name="create_post",
            description="Create a Noor Instagram Reel post",
            parameters=google_types.Schema(
                type="OBJECT",
                properties={
                    "image_prompt": google_types.Schema(
                        type="STRING",
                        description="Highly detailed cinematic video generation prompt. Style: golden hour or soft natural light, 9:16 portrait, photorealistic, ultra-detailed. Subject evokes the topic. Modern Islamic aesthetic. No Arabic text or calligraphy.",
                    ),
                    "caption": google_types.Schema(
                        type="STRING",
                        description="Instagram caption in English. Max 300 words. End with 3-5 relevant hashtags.",
                    ),
                    "topic": google_types.Schema(
                        type="STRING",
                        description="The exact topic string received.",
                    ),
                    "narration": google_types.Schema(
                        type="STRING",
                        description="60-80 word spoken voiceover script. Warm, calm tone. No hashtags. No markdown. Written to be heard, not read.",
                    ),
                },
                required=["image_prompt", "caption", "topic", "narration"],
            ),
        )
    ]
)


def get_topic_for_date(today: date) -> str:
    """Return topic key based on day-of-year mod 3."""
    return TOPIC_ROTATION[today.timetuple().tm_yday % 3]


def generate_content(today: date, client: google_genai.Client) -> dict:
    """Call Gemini to generate image_prompt, caption, topic, narration via function calling.

    Returns dict with keys: image_prompt, caption, topic, narration.
    """
    topic = get_topic_for_date(today)
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=f"Generate a Noor Instagram Reel post for topic: {topic}",
        config=google_types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            tools=[_POST_TOOL],
            tool_config=google_types.ToolConfig(
                function_calling_config=google_types.FunctionCallingConfig(
                    mode="ANY",
                    allowed_function_names=["create_post"],
                )
            ),
        ),
    )
    return dict(response.candidates[0].content.parts[0].function_call.args)
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
cd /Users/yp/noor-website && python -m pytest tests/test_instagram_agent.py::test_generate_content_returns_required_keys tests/test_instagram_agent.py::test_generate_content_narration_is_string tests/test_instagram_agent.py::test_get_topic_for_date_covers_all_three_topics tests/test_instagram_agent.py::test_get_topic_for_date_is_deterministic -v
```

Expected: 4 PASSED

- [ ] **Step 5: Commit**

```bash
cd /Users/yp/noor-website && git add instagram_agent.py tests/test_instagram_agent.py && git commit -m "feat: replace Claude content generation with Gemini function calling + narration field"
```

---

## Task 2: Video Generation — Imagen 4 → Veo 2

**Files:**
- Modify: `instagram_agent.py` (remove `generate_image`, remove `overlay_logo`, add `generate_video_clips`, add `concatenate_clips`)
- Modify: `tests/test_instagram_agent.py` (replace image/logo tests with video tests)

- [ ] **Step 1: Write failing tests for `generate_video_clips` and `concatenate_clips`**

Add to `tests/test_instagram_agent.py`:

```python
import tempfile
from pathlib import Path
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
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd /Users/yp/noor-website && python -m pytest tests/test_instagram_agent.py::test_generate_video_clips_returns_three_bytes_objects tests/test_instagram_agent.py::test_concatenate_clips_produces_file -v
```

Expected: `ImportError` — functions don't exist yet

- [ ] **Step 3: Replace `generate_image` and `overlay_logo` with `generate_video_clips` and `concatenate_clips` in `instagram_agent.py`**

Remove the `# ── Image Generation` and `# ── Logo Overlay` sections entirely. Add:

```python
# ── Video Generation ──────────────────────────────────────────────────────────

def generate_video_clips(video_prompt: str, client: google_genai.Client, num_clips: int = 3) -> list[bytes]:
    """Generate num_clips short video clips using Veo 2 and return list of MP4 bytes.

    Each clip is 8 seconds at 9:16 aspect ratio. Polls until operation is done.
    """
    clips = []
    for _ in range(num_clips):
        operation = client.models.generate_videos(
            model="veo-2.0-generate-001",
            prompt=video_prompt,
            config=google_types.GenerateVideoConfig(
                aspect_ratio="9:16",
                duration_seconds=8,
            ),
        )
        while not operation.done:
            time.sleep(10)
            operation = client.operations.get(operation)
        clips.append(operation.response.generated_videos[0].video.video_bytes)
    return clips


def concatenate_clips(clip_paths: list[Path], work_dir: Path) -> Path:
    """Concatenate MP4 clips using ffmpeg concat demuxer.

    Writes a clips.txt manifest and runs ffmpeg. Returns path to combined.mp4.
    Raises subprocess.CalledProcessError if ffmpeg fails.
    """
    manifest = work_dir / "clips.txt"
    manifest.write_text("\n".join(f"file '{p}'" for p in clip_paths))
    out_path = work_dir / "combined.mp4"
    subprocess.run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(manifest), "-c", "copy", str(out_path)],
        check=True,
        capture_output=True,
    )
    return out_path
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
cd /Users/yp/noor-website && python -m pytest tests/test_instagram_agent.py::test_generate_video_clips_returns_three_bytes_objects tests/test_instagram_agent.py::test_concatenate_clips_produces_file -v
```

Expected: 2 PASSED

- [ ] **Step 5: Commit**

```bash
cd /Users/yp/noor-website && git add instagram_agent.py tests/test_instagram_agent.py && git commit -m "feat: add Veo 2 video clip generation and ffmpeg concat"
```

---

## Task 3: Voiceover Generation — Gemini TTS

**Files:**
- Modify: `instagram_agent.py` (add `generate_voiceover`)
- Modify: `tests/test_instagram_agent.py` (add voiceover tests)

- [ ] **Step 1: Write failing test for `generate_voiceover`**

Add to `tests/test_instagram_agent.py`:

```python
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
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd /Users/yp/noor-website && python -m pytest tests/test_instagram_agent.py::test_generate_voiceover_returns_bytes tests/test_instagram_agent.py::test_generate_voiceover_uses_kore_voice -v
```

Expected: `ImportError`

- [ ] **Step 3: Add `generate_voiceover` to `instagram_agent.py`**

After the `concatenate_clips` function, add:

```python
# ── Voiceover Generation ──────────────────────────────────────────────────────


def generate_voiceover(narration: str, client: google_genai.Client) -> bytes:
    """Generate a spoken voiceover from narration text using Gemini TTS.

    Uses the Kore voice (warm, calm). Returns raw audio bytes (WAV/PCM).
    """
    response = client.models.generate_content(
        model="gemini-2.5-flash-preview-tts",
        contents=narration,
        config=google_types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=google_types.SpeechConfig(
                voice_config=google_types.VoiceConfig(
                    prebuilt_voice_config=google_types.PrebuiltVoiceConfig(
                        voice_name="Kore",
                    )
                )
            ),
        ),
    )
    return response.candidates[0].content.parts[0].inline_data.data
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
cd /Users/yp/noor-website && python -m pytest tests/test_instagram_agent.py::test_generate_voiceover_returns_bytes tests/test_instagram_agent.py::test_generate_voiceover_uses_kore_voice -v
```

Expected: 2 PASSED

- [ ] **Step 5: Commit**

```bash
cd /Users/yp/noor-website && git add instagram_agent.py tests/test_instagram_agent.py && git commit -m "feat: add Gemini TTS voiceover generation with Kore voice"
```

---

## Task 4: Video + Audio Merge (ffmpeg)

**Files:**
- Modify: `instagram_agent.py` (add `merge_video_audio`)
- Modify: `tests/test_instagram_agent.py` (add merge test)

- [ ] **Step 1: Write failing test for `merge_video_audio`**

Add to `tests/test_instagram_agent.py`:

```python
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
```

- [ ] **Step 2: Run test to confirm it fails**

```bash
cd /Users/yp/noor-website && python -m pytest tests/test_instagram_agent.py::test_merge_video_audio_calls_ffmpeg -v
```

Expected: `ImportError`

- [ ] **Step 3: Add `merge_video_audio` to `instagram_agent.py`**

After `generate_voiceover`, add:

```python
# ── Video + Audio Merge ───────────────────────────────────────────────────────


def merge_video_audio(video_path: Path, audio_path: Path, work_dir: Path) -> Path:
    """Merge video and audio with ffmpeg, trimming to the shorter track.

    Returns path to final.mp4. Raises subprocess.CalledProcessError if ffmpeg fails.
    """
    out_path = work_dir / "final.mp4"
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-i", str(video_path),
            "-i", str(audio_path),
            "-c:v", "copy",
            "-c:a", "aac",
            "-shortest",
            str(out_path),
        ],
        check=True,
        capture_output=True,
    )
    return out_path
```

- [ ] **Step 4: Run test to confirm it passes**

```bash
cd /Users/yp/noor-website && python -m pytest tests/test_instagram_agent.py::test_merge_video_audio_calls_ffmpeg -v
```

Expected: PASSED

- [ ] **Step 5: Commit**

```bash
cd /Users/yp/noor-website && git add instagram_agent.py tests/test_instagram_agent.py && git commit -m "feat: add ffmpeg video+audio merge"
```

---

## Task 5: Cloudinary Upload — Image → Video

**Files:**
- Modify: `instagram_agent.py` (update `upload_to_cloudinary` to use `resource_type="video"`)
- Modify: `tests/test_instagram_agent.py` (update cloudinary test)

- [ ] **Step 1: Write failing test for updated `upload_to_cloudinary`**

Add to `tests/test_instagram_agent.py`:

```python
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
```

- [ ] **Step 2: Run test to confirm it fails**

```bash
cd /Users/yp/noor-website && python -m pytest tests/test_instagram_agent.py::test_upload_to_cloudinary_uses_video_resource_type -v
```

Expected: FAILED (currently uses `resource_type="image"`)

- [ ] **Step 3: Update `upload_to_cloudinary` in `instagram_agent.py`**

```python
def upload_to_cloudinary(video_bytes: bytes, cloud_name: str, api_key: str, api_secret: str) -> str:
    """Upload video bytes to Cloudinary and return the public HTTPS URL."""
    import cloudinary
    import cloudinary.uploader

    cloudinary.config(cloud_name=cloud_name, api_key=api_key, api_secret=api_secret)
    result = cloudinary.uploader.upload(video_bytes, resource_type="video", format="mp4")
    return result["secure_url"]
```

- [ ] **Step 4: Run test to confirm it passes**

```bash
cd /Users/yp/noor-website && python -m pytest tests/test_instagram_agent.py::test_upload_to_cloudinary_uses_video_resource_type -v
```

Expected: PASSED

- [ ] **Step 5: Commit**

```bash
cd /Users/yp/noor-website && git add instagram_agent.py tests/test_instagram_agent.py && git commit -m "feat: upload video to Cloudinary instead of image"
```

---

## Task 6: Instagram Reels Posting

**Files:**
- Modify: `instagram_agent.py` (update `create_ig_media_container`, add `wait_for_ig_container`)
- Modify: `tests/test_instagram_agent.py` (update IG tests)

- [ ] **Step 1: Write failing tests**

Add to `tests/test_instagram_agent.py`:

```python
from instagram_agent import create_ig_reel_container, wait_for_ig_container, publish_ig_media_container


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
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd /Users/yp/noor-website && python -m pytest tests/test_instagram_agent.py::test_create_ig_reel_container_uses_reels_media_type tests/test_instagram_agent.py::test_wait_for_ig_container_returns_when_finished tests/test_instagram_agent.py::test_wait_for_ig_container_raises_on_timeout -v
```

Expected: `ImportError`

- [ ] **Step 3: Update Instagram functions in `instagram_agent.py`**

Replace `create_ig_media_container` with `create_ig_reel_container` and add `wait_for_ig_container`:

```python
# ── Instagram Posting ─────────────────────────────────────────────────────────

IG_API_BASE = "https://graph.facebook.com/v22.0"


def create_ig_reel_container(
    ig_user_id: str, video_url: str, caption: str, access_token: str
) -> str:
    """Step 1 of 3: Create an IG media container for a Reel.

    video_url must be a publicly accessible HTTPS URL (MP4, H.264, 9:16).
    Returns container_id.
    Raises RuntimeError on API failure.
    """
    response = http_requests.post(
        f"{IG_API_BASE}/{ig_user_id}/media",
        params={
            "media_type": "REELS",
            "video_url": video_url,
            "caption": caption,
            "access_token": access_token,
        },
        timeout=30,
    )
    if not response.ok:
        raise RuntimeError(f"IG Reel container creation failed ({response.status_code}): {response.text}")
    data = response.json()
    if "id" not in data:
        raise RuntimeError(f"IG Reel container creation failed: {data}")
    return data["id"]


def wait_for_ig_container(
    container_id: str, access_token: str, max_attempts: int = 24, poll_interval: int = 5
) -> None:
    """Step 2 of 3: Poll until the IG container status is FINISHED.

    Polls every poll_interval seconds up to max_attempts times (~120s default).
    Raises RuntimeError on timeout or error status.
    """
    for _ in range(max_attempts):
        response = http_requests.get(
            f"{IG_API_BASE}/{container_id}",
            params={"fields": "status_code", "access_token": access_token},
            timeout=30,
        )
        response.raise_for_status()
        status = response.json().get("status_code")
        if status == "FINISHED":
            return
        if status == "ERROR":
            raise RuntimeError(f"IG container processing failed: {response.json()}")
        time.sleep(poll_interval)
    raise RuntimeError(f"IG container {container_id} timed out after {max_attempts} attempts")


def publish_ig_media_container(ig_user_id: str, container_id: str, access_token: str) -> str:
    """Step 3 of 3: Publish an IG media container to the feed.

    Returns the media_id of the published post.
    Raises RuntimeError if the API response lacks an 'id'.
    """
    response = http_requests.post(
        f"{IG_API_BASE}/{ig_user_id}/media_publish",
        params={
            "creation_id": container_id,
            "access_token": access_token,
        },
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()
    if "id" not in data:
        raise RuntimeError(f"IG publish failed: {data}")
    return data["id"]
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
cd /Users/yp/noor-website && python -m pytest tests/test_instagram_agent.py::test_create_ig_reel_container_uses_reels_media_type tests/test_instagram_agent.py::test_wait_for_ig_container_returns_when_finished tests/test_instagram_agent.py::test_wait_for_ig_container_raises_on_timeout -v
```

Expected: 3 PASSED

- [ ] **Step 5: Commit**

```bash
cd /Users/yp/noor-website && git add instagram_agent.py tests/test_instagram_agent.py && git commit -m "feat: post as Instagram Reel with container polling"
```

---

## Task 7: Telegram — sendPhoto → sendVideo

**Files:**
- Modify: `instagram_agent.py` (rename/update `send_to_telegram`)
- Modify: `tests/test_instagram_agent.py` (update Telegram test)

- [ ] **Step 1: Write failing test**

Add to `tests/test_instagram_agent.py`:

```python
from instagram_agent import send_to_telegram


def test_send_to_telegram_uses_send_video():
    """send_to_telegram calls sendVideo (not sendPhoto) with MP4 bytes."""
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {"ok": True}

    with patch("instagram_agent.http_requests.post", return_value=mock_response) as mock_post:
        send_to_telegram(b"FAKEMP4", "Caption text. #Noor", "bot-token", "-1001234567890")

    call_url = mock_post.call_args[0][0]
    assert "sendVideo" in call_url
    assert "sendPhoto" not in call_url


def test_send_to_telegram_truncates_caption_at_1024():
    """send_to_telegram truncates caption to 1024 chars for the video message."""
    long_caption = "A" * 2000
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {"ok": True}

    with patch("instagram_agent.http_requests.post", return_value=mock_response) as mock_post:
        send_to_telegram(b"FAKEMP4", long_caption, "bot-token", "-1001234567890")

    first_call_data = mock_post.call_args_list[0][1]["data"]
    assert len(first_call_data["caption"]) == 1024
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd /Users/yp/noor-website && python -m pytest tests/test_instagram_agent.py::test_send_to_telegram_uses_send_video tests/test_instagram_agent.py::test_send_to_telegram_truncates_caption_at_1024 -v
```

Expected: FAILED (currently uses sendPhoto)

- [ ] **Step 3: Update `send_to_telegram` in `instagram_agent.py`**

Replace `send_to_telegram`:

```python
# ── Telegram Delivery ─────────────────────────────────────────────────────────

TELEGRAM_API_BASE = "https://api.telegram.org"


def send_to_telegram(video_bytes: bytes, caption: str, bot_token: str, chat_id: str) -> None:
    """Send MP4 video + caption to a Telegram chat via Bot API.

    Sends the video with caption (truncated to 1024 chars).
    If caption exceeds 1024 chars, sends remainder as a follow-up message.
    """
    video_url = f"{TELEGRAM_API_BASE}/bot{bot_token}/sendVideo"
    response = http_requests.post(
        video_url,
        data={"chat_id": chat_id, "caption": caption[:1024]},
        files={"video": ("noor.mp4", video_bytes, "video/mp4")},
        timeout=60,
    )
    response.raise_for_status()
    if not response.json().get("ok"):
        raise RuntimeError(f"Telegram sendVideo failed: {response.json()}")

    if len(caption) > 1024:
        msg_url = f"{TELEGRAM_API_BASE}/bot{bot_token}/sendMessage"
        response = http_requests.post(
            msg_url,
            data={"chat_id": chat_id, "text": caption[1024:]},
            timeout=30,
        )
        response.raise_for_status()
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
cd /Users/yp/noor-website && python -m pytest tests/test_instagram_agent.py::test_send_to_telegram_uses_send_video tests/test_instagram_agent.py::test_send_to_telegram_truncates_caption_at_1024 -v
```

Expected: 2 PASSED

- [ ] **Step 5: Commit**

```bash
cd /Users/yp/noor-website && git add instagram_agent.py tests/test_instagram_agent.py && git commit -m "feat: send video to Telegram via sendVideo"
```

---

## Task 8: Rewire main() Pipeline

**Files:**
- Modify: `instagram_agent.py` (rewrite `main()`)
- Modify: `tests/test_instagram_agent.py` (update integration test)

- [ ] **Step 1: Write failing integration test**

Replace `test_main_completes_full_pipeline` in `tests/test_instagram_agent.py`:

```python
from instagram_agent import main


def test_main_completes_full_pipeline(monkeypatch, tmp_path):
    """main() runs all 7 stages end-to-end with all external calls mocked."""
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini")
    monkeypatch.setenv("CLOUDINARY_CLOUD_NAME", "test-cloud")
    monkeypatch.setenv("CLOUDINARY_API_KEY", "test-key")
    monkeypatch.setenv("CLOUDINARY_API_SECRET", "test-secret")
    monkeypatch.setenv("IG_USER_ID", "12345")
    monkeypatch.setenv("IG_ACCESS_TOKEN", "test-token")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-bot")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "-1001234567890")

    fake_video = b"FAKEVIDEO"
    fake_audio = b"FAKEAUDIO"

    with patch("instagram_agent.google_genai.Client") as mock_client_cls, \
         patch("instagram_agent.generate_content") as mock_content, \
         patch("instagram_agent.generate_video_clips") as mock_clips, \
         patch("instagram_agent.concatenate_clips") as mock_concat, \
         patch("instagram_agent.generate_voiceover") as mock_tts, \
         patch("instagram_agent.merge_video_audio") as mock_merge, \
         patch("instagram_agent.upload_to_cloudinary") as mock_upload, \
         patch("instagram_agent.create_ig_reel_container") as mock_container, \
         patch("instagram_agent.wait_for_ig_container") as mock_wait, \
         patch("instagram_agent.publish_ig_media_container") as mock_publish, \
         patch("instagram_agent.send_to_telegram") as mock_telegram, \
         patch("instagram_agent.tempfile.TemporaryDirectory") as mock_tmpdir:

        mock_content.return_value = {
            "image_prompt": "mosque dawn cinematic",
            "caption": "Bismillah. #Noor",
            "topic": "fitrah",
            "narration": "Every morning is a gift.",
        }
        mock_clips.return_value = [fake_video, fake_video, fake_video]

        fake_tmp = tmp_path
        mock_tmpdir.return_value.__enter__ = MagicMock(return_value=str(fake_tmp))
        mock_tmpdir.return_value.__exit__ = MagicMock(return_value=False)

        concat_path = fake_tmp / "combined.mp4"
        concat_path.write_bytes(fake_video)
        mock_concat.return_value = concat_path

        mock_tts.return_value = fake_audio

        final_path = fake_tmp / "final.mp4"
        final_path.write_bytes(fake_video)
        mock_merge.return_value = final_path

        mock_upload.return_value = "https://res.cloudinary.com/noor/video/noor.mp4"
        mock_container.return_value = "container123"
        mock_publish.return_value = "media456"

        main()

    mock_content.assert_called_once()
    mock_clips.assert_called_once()
    mock_concat.assert_called_once()
    mock_tts.assert_called_once()
    mock_merge.assert_called_once()
    mock_upload.assert_called_once()
    mock_container.assert_called_once()
    mock_wait.assert_called_once()
    mock_publish.assert_called_once()
    mock_telegram.assert_called_once()
```

- [ ] **Step 2: Run test to confirm it fails**

```bash
cd /Users/yp/noor-website && python -m pytest tests/test_instagram_agent.py::test_main_completes_full_pipeline -v
```

Expected: FAILED

- [ ] **Step 3: Rewrite `main()` in `instagram_agent.py`**

```python
# ── Pipeline ──────────────────────────────────────────────────────────────────


def main() -> None:
    """Run the full Noor video Reel pipeline.

    Environment variables required:
      GEMINI_API_KEY,
      CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET,
      IG_USER_ID, IG_ACCESS_TOKEN,
      TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
    """
    today_wib = datetime.now(ZoneInfo("Asia/Jakarta")).date()

    google_client = google_genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    cloudinary_cloud_name = os.environ["CLOUDINARY_CLOUD_NAME"]
    cloudinary_api_key = os.environ["CLOUDINARY_API_KEY"]
    cloudinary_api_secret = os.environ["CLOUDINARY_API_SECRET"]
    ig_user_id = os.environ["IG_USER_ID"]
    ig_access_token = os.environ["IG_ACCESS_TOKEN"]
    telegram_token = os.environ["TELEGRAM_BOT_TOKEN"]
    telegram_chat_id = os.environ["TELEGRAM_CHAT_ID"]

    print(f"[1/7] Generating content for {today_wib}...")
    content = generate_content(today_wib, google_client)
    print(f"      Topic: {content['topic']}")
    print(f"      Caption preview: {content['caption'][:60]}...")

    with tempfile.TemporaryDirectory() as tmp_str:
        work_dir = Path(tmp_str)

        print("[2/7] Generating 3 video clips with Veo 2...")
        clip_bytes_list = generate_video_clips(content["image_prompt"], google_client)
        clip_paths = []
        for i, clip_bytes in enumerate(clip_bytes_list):
            p = work_dir / f"clip{i}.mp4"
            p.write_bytes(clip_bytes)
            clip_paths.append(p)
        print(f"      {len(clip_paths)} clips generated.")

        print("[3/7] Concatenating clips...")
        combined_path = concatenate_clips(clip_paths, work_dir)
        print(f"      Combined: {combined_path.stat().st_size:,} bytes")

        print("[4/7] Generating voiceover...")
        audio_bytes = generate_voiceover(content["narration"], google_client)
        audio_path = work_dir / "narration.wav"
        audio_path.write_bytes(audio_bytes)
        print(f"      Audio: {len(audio_bytes):,} bytes")

        print("[5/7] Merging video + audio...")
        final_path = merge_video_audio(combined_path, audio_path, work_dir)
        print(f"      Final: {final_path.stat().st_size:,} bytes")

        print("[6/7] Uploading to Cloudinary and posting as Reel...")
        video_bytes = final_path.read_bytes()
        video_url = upload_to_cloudinary(video_bytes, cloudinary_cloud_name, cloudinary_api_key, cloudinary_api_secret)
        print(f"      Uploaded: {video_url}")
        container_id = create_ig_reel_container(ig_user_id, video_url, content["caption"], ig_access_token)
        print(f"      Container: {container_id} — waiting for processing...")
        wait_for_ig_container(container_id, ig_access_token)
        media_id = publish_ig_media_container(ig_user_id, container_id, ig_access_token)
        print(f"      Published! media_id={media_id}")

        print("[7/7] Sending to Telegram...")
        send_to_telegram(video_bytes, content["caption"], telegram_token, telegram_chat_id)
        print("      Done!")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run all tests**

```bash
cd /Users/yp/noor-website && python -m pytest tests/test_instagram_agent.py -v
```

Expected: All relevant tests PASS. Old stale tests (referencing `upload_to_imgbb`, `generate_image`, `overlay_logo`) will fail — remove them in the next step.

- [ ] **Step 5: Remove stale tests**

Delete these test functions from `tests/test_instagram_agent.py` (they test removed functions):
- `test_generate_image_downloads_dall_e_url_and_returns_bytes`
- `test_generate_image_raises_on_download_failure`
- `test_overlay_logo_returns_jpeg_bytes`
- `test_overlay_logo_preserves_input_dimensions`
- `test_overlay_logo_scales_wide_logo_to_max_width`
- `test_upload_to_imgbb_returns_public_url`
- `test_upload_to_imgbb_raises_on_api_failure`
- `test_create_ig_media_container_returns_container_id`
- `test_create_ig_media_container_raises_without_id`
- `test_generate_content_raises_on_invalid_json`
- Any imports of `upload_to_imgbb`, `generate_image`, `overlay_logo`, `create_ig_media_container`

- [ ] **Step 6: Run all tests to confirm clean pass**

```bash
cd /Users/yp/noor-website && python -m pytest tests/test_instagram_agent.py -v
```

Expected: All tests PASS, no failures

- [ ] **Step 7: Commit**

```bash
cd /Users/yp/noor-website && git add instagram_agent.py tests/test_instagram_agent.py && git commit -m "feat: rewire main() for 7-step video Reel pipeline"
```

---

## Task 9: Cleanup — Requirements and Workflow

**Files:**
- Modify: `requirements.txt` (remove `anthropic`)
- Modify: `.github/workflows/instagram-post.yml` (remove `ANTHROPIC_API_KEY`, bump timeout)

- [ ] **Step 1: Remove `anthropic` from `requirements.txt`**

`requirements.txt` should be:

```
requests==2.32.3
google-genai>=1.0.0
Pillow>=11.0.0
cloudinary>=1.36.0
pytest>=8.0.0
```

- [ ] **Step 2: Update workflow**

In `.github/workflows/instagram-post.yml`:
- Change `timeout-minutes: 10` → `timeout-minutes: 20`
- Remove `ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}` line

Final workflow env block:

```yaml
        env:
          GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
          CLOUDINARY_CLOUD_NAME: ${{ secrets.CLOUDINARY_CLOUD_NAME }}
          CLOUDINARY_API_KEY: ${{ secrets.CLOUDINARY_API_KEY }}
          CLOUDINARY_API_SECRET: ${{ secrets.CLOUDINARY_API_SECRET }}
          IG_USER_ID: ${{ secrets.IG_USER_ID }}
          IG_ACCESS_TOKEN: ${{ secrets.IG_ACCESS_TOKEN }}
          TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}
          TELEGRAM_CHAT_ID: ${{ secrets.TELEGRAM_CHAT_ID }}
```

- [ ] **Step 3: Run full test suite one final time**

```bash
cd /Users/yp/noor-website && python -m pytest tests/test_instagram_agent.py -v
```

Expected: All tests PASS

- [ ] **Step 4: Commit and push**

```bash
cd /Users/yp/noor-website && git add requirements.txt .github/workflows/instagram-post.yml && git commit -m "chore: remove anthropic dependency, bump workflow timeout to 20min" && git push
```

- [ ] **Step 5: Trigger manual workflow run on GitHub Actions**

Go to: `github.com/hypersoundnft/noor-app → Actions → Noor Instagram Daily Post → Run workflow`

Verify all 7 steps print successfully in the logs.
