"""Daily Instagram post agent for the Noor brand."""

import io
import os
import subprocess
import tempfile
import time
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import cloudinary
import cloudinary.uploader
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


# ── Instagram / Telegram constants ───────────────────────────────────────────

IG_API_BASE = "https://graph.facebook.com/v22.0"
TELEGRAM_API_BASE = "https://api.telegram.org"

# ── Image Generation (POST_FORMAT=image) ─────────────────────────────────────

def generate_image(image_prompt: str, client: google_genai.Client) -> bytes:
    """Generate a single image using Imagen 4 and return raw JPEG bytes."""
    response = client.models.generate_images(
        model="imagen-4.0-generate-001",
        prompt=image_prompt,
        config=google_types.GenerateImagesConfig(number_of_images=1),
    )
    return response.generated_images[0].image.image_bytes


LOGO_MARGIN = 30
LOGO_MAX_WIDTH = 180


def overlay_logo(image_bytes: bytes, logo_path: Path) -> bytes:
    """Composite the Noor logo into the bottom-right corner. Returns JPEG bytes."""
    base = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
    logo = Image.open(logo_path).convert("RGBA")

    ratio = LOGO_MAX_WIDTH / logo.width
    new_size = (LOGO_MAX_WIDTH, max(1, int(logo.height * ratio)))
    logo = logo.resize(new_size, Image.LANCZOS)

    x = base.width - new_size[0] - LOGO_MARGIN
    y = base.height - new_size[1] - LOGO_MARGIN

    composite = base.copy()
    composite.paste(logo, (x, y), logo)

    out = io.BytesIO()
    composite.convert("RGB").save(out, format="JPEG", quality=95)
    return out.getvalue()


def upload_image_to_cloudinary(image_bytes: bytes, cloud_name: str, api_key: str, api_secret: str) -> str:
    """Upload image bytes to Cloudinary and return the public HTTPS URL."""
    cloudinary.config(cloud_name=cloud_name, api_key=api_key, api_secret=api_secret)
    result = cloudinary.uploader.upload(image_bytes, resource_type="image", format="jpg")
    return result["secure_url"]


def create_ig_image_container(
    ig_user_id: str, image_url: str, caption: str, access_token: str
) -> str:
    """Create an IG media container for a feed image post. Returns container_id."""
    response = http_requests.post(
        f"{IG_API_BASE}/{ig_user_id}/media",
        params={"image_url": image_url, "caption": caption, "access_token": access_token},
        timeout=30,
    )
    if not response.ok:
        raise RuntimeError(f"IG image container creation failed ({response.status_code}): {response.text}")
    data = response.json()
    if "id" not in data:
        raise RuntimeError(f"IG image container creation failed: {data}")
    return data["id"]


def send_photo_to_telegram(image_bytes: bytes, caption: str, bot_token: str, chat_id: str) -> None:
    """Send JPEG photo + caption to a Telegram chat via Bot API."""
    response = http_requests.post(
        f"{TELEGRAM_API_BASE}/bot{bot_token}/sendPhoto",
        data={"chat_id": chat_id, "caption": caption[:1024]},
        files={"photo": ("noor.jpg", image_bytes, "image/jpeg")},
        timeout=30,
    )
    response.raise_for_status()
    if not response.json().get("ok"):
        raise RuntimeError(f"Telegram sendPhoto failed: {response.json()}")

    if len(caption) > 1024:
        http_requests.post(
            f"{TELEGRAM_API_BASE}/bot{bot_token}/sendMessage",
            data={"chat_id": chat_id, "text": caption[1024:]},
            timeout=30,
        ).raise_for_status()


# ── Video Generation (POST_FORMAT=video) ─────────────────────────────────────

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


def upload_to_cloudinary(video_bytes: bytes, cloud_name: str, api_key: str, api_secret: str) -> str:
    """Upload video bytes to Cloudinary and return the public HTTPS URL."""
    cloudinary.config(cloud_name=cloud_name, api_key=api_key, api_secret=api_secret)
    result = cloudinary.uploader.upload(video_bytes, resource_type="video", format="mp4")
    return result["secure_url"]


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
    """Run the Noor content pipeline in image or video mode.

    Set POST_FORMAT=video to enable the Veo 2 Reels pipeline.
    Defaults to POST_FORMAT=image (Imagen 4 feed post).

    Environment variables required:
      GEMINI_API_KEY,
      CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET,
      IG_USER_ID, IG_ACCESS_TOKEN,
      TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
    """
    today_wib = datetime.now(ZoneInfo("Asia/Jakarta")).date()
    post_format = os.environ.get("POST_FORMAT", "image").lower()

    google_client = google_genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    cloudinary_cloud_name = os.environ["CLOUDINARY_CLOUD_NAME"]
    cloudinary_api_key = os.environ["CLOUDINARY_API_KEY"]
    cloudinary_api_secret = os.environ["CLOUDINARY_API_SECRET"]
    ig_user_id = os.environ["IG_USER_ID"]
    ig_access_token = os.environ["IG_ACCESS_TOKEN"]
    telegram_token = os.environ["TELEGRAM_BOT_TOKEN"]
    telegram_chat_id = os.environ["TELEGRAM_CHAT_ID"]

    print(f"[1] Generating content for {today_wib} (format={post_format})...")
    content = generate_content(today_wib, google_client)
    print(f"    Topic: {content['topic']}")
    print(f"    Caption preview: {content['caption'][:60]}...")

    if post_format == "video":
        _run_video_pipeline(content, google_client, cloudinary_cloud_name, cloudinary_api_key,
                            cloudinary_api_secret, ig_user_id, ig_access_token,
                            telegram_token, telegram_chat_id)
    else:
        _run_image_pipeline(content, google_client, cloudinary_cloud_name, cloudinary_api_key,
                            cloudinary_api_secret, ig_user_id, ig_access_token,
                            telegram_token, telegram_chat_id)


def _run_image_pipeline(content, google_client, cloudinary_cloud_name, cloudinary_api_key,
                        cloudinary_api_secret, ig_user_id, ig_access_token,
                        telegram_token, telegram_chat_id) -> None:
    logo_path = Path(__file__).parent / "public" / "noor_logo_white.png"

    print("[2/4] Generating image with Imagen 4...")
    image_bytes = generate_image(content["image_prompt"], google_client)
    print(f"      Image: {len(image_bytes):,} bytes")

    print("[3/4] Overlaying Noor logo...")
    if logo_path.exists():
        image_bytes = overlay_logo(image_bytes, logo_path)
        print("      Logo composited.")
    else:
        print(f"      Warning: no logo at {logo_path} — skipping overlay")

    print("[4/4] Uploading and posting to Instagram + Telegram...")
    image_url = upload_image_to_cloudinary(image_bytes, cloudinary_cloud_name, cloudinary_api_key, cloudinary_api_secret)
    print(f"      Uploaded: {image_url}")
    container_id = create_ig_image_container(ig_user_id, image_url, content["caption"], ig_access_token)
    media_id = publish_ig_media_container(ig_user_id, container_id, ig_access_token)
    print(f"      Published! media_id={media_id}")
    send_photo_to_telegram(image_bytes, content["caption"], telegram_token, telegram_chat_id)
    print("      Done!")


def _run_video_pipeline(content, google_client, cloudinary_cloud_name, cloudinary_api_key,
                        cloudinary_api_secret, ig_user_id, ig_access_token,
                        telegram_token, telegram_chat_id) -> None:
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
