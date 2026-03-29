"""Daily Instagram post agent for the Noor brand."""

import os
import subprocess
import time
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from google import genai as google_genai
from google.genai import types as google_types
import anthropic
import requests as http_requests

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
            config=google_types.GenerateVideosConfig(
                aspect_ratio="9:16",
                duration_seconds=8,
            ),
        )
        while not operation.done:
            time.sleep(10)
            operation = client.operations.get(operation)
        if not operation.response.generated_videos:
            raise RuntimeError(f"Veo 2 returned no videos for clip {len(clips) + 1}")
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


# ── Instagram Posting ─────────────────────────────────────────────────────────

IG_API_BASE = "https://graph.facebook.com/v22.0"


def upload_to_cloudinary(video_bytes: bytes, cloud_name: str, api_key: str, api_secret: str) -> str:
    """Upload video bytes to Cloudinary and return the public HTTPS URL."""
    import cloudinary
    import cloudinary.uploader

    cloudinary.config(cloud_name=cloud_name, api_key=api_key, api_secret=api_secret)
    result = cloudinary.uploader.upload(video_bytes, resource_type="video", format="mp4")
    return result["secure_url"]


def upload_to_imgbb(image_bytes: bytes, api_key: str) -> str:
    """Upload image bytes to imgbb and return the public URL."""
    import base64
    b64 = base64.b64encode(image_bytes).decode()
    response = http_requests.post(
        "https://api.imgbb.com/1/upload",
        data={"key": api_key, "image": b64},
        timeout=30,
    )
    data = response.json()
    if not data.get("success"):
        raise RuntimeError(f"imgbb upload failed: {data}")
    return data["data"]["url"]


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


# ── Pipeline ──────────────────────────────────────────────────────────────────


def main() -> None:
    """Run the full Noor content pipeline, posting to Instagram and Telegram.

    Reads environment variables:
      ANTHROPIC_API_KEY, GEMINI_API_KEY,
      IMGBB_API_KEY, IG_USER_ID, IG_ACCESS_TOKEN,
      TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
    """
    today_wib = datetime.now(ZoneInfo("Asia/Jakarta")).date()

    claude_client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    google_client = google_genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    print(f"[1/5] Generating content for {today_wib}...")
    content = generate_content(today_wib, claude_client)
    print(f"      Topic: {content['topic']}")
    print(f"      Caption preview: {content['caption'][:60]}...")

    print("[2/5] Generating video clips with Veo 2...")
    clips = generate_video_clips(content["image_prompt"], google_client)
    print(f"      Generated {len(clips)} clip(s).")

    print("[3/5] Skipped (video concat + upload — see future tasks)...")

    print("[4/5] Skipped (Instagram posting — see future tasks)...")

    print("[5/5] Skipped (Telegram delivery — see future tasks)...")
    print("      Done!")


if __name__ == "__main__":
    main()
