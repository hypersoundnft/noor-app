"""Daily Instagram post agent for the Noor brand."""

import io
import os
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from google import genai as google_genai
from google.genai import types as google_types
import anthropic
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


# ── Image Generation ──────────────────────────────────────────────────────────


def generate_image(image_prompt: str, client: google_genai.Client) -> bytes:
    """Call Imagen 4 via Google AI Studio and return raw image bytes."""
    response = client.models.generate_images(
        model="imagen-4.0-generate-001",
        prompt=image_prompt,
        config=google_types.GenerateImagesConfig(number_of_images=1),
    )
    return response.generated_images[0].image.image_bytes


# ── Logo Overlay ──────────────────────────────────────────────────────────────

LOGO_MARGIN = 30   # pixels from edge
LOGO_MAX_WIDTH = 180  # max logo width in pixels


def overlay_logo(image_bytes: bytes, logo_path: Path) -> bytes:
    """Composite the Noor logo into the bottom-right corner.

    Scales the logo to at most LOGO_MAX_WIDTH wide, maintaining aspect ratio.
    Returns JPEG bytes at 95% quality.
    """
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


# ── Instagram Posting ─────────────────────────────────────────────────────────

IG_API_BASE = "https://graph.facebook.com/v22.0"


def upload_to_cloudinary(image_bytes: bytes, cloud_name: str, api_key: str, api_secret: str) -> str:
    """Upload image bytes to Cloudinary and return the public HTTPS URL."""
    import cloudinary
    import cloudinary.uploader

    cloudinary.config(cloud_name=cloud_name, api_key=api_key, api_secret=api_secret)
    result = cloudinary.uploader.upload(image_bytes, resource_type="image", format="jpg")
    return result["secure_url"]


def upload_to_imgbb(image_bytes: bytes, api_key: str) -> str:
    """Upload image bytes to imgbb and return the public URL. (Legacy stub.)"""
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


def create_ig_media_container(
    ig_user_id: str, image_url: str, caption: str, access_token: str
) -> str:
    """Step 1 of 2: Create an IG media container for a feed image post.

    image_url must be a publicly accessible HTTPS URL.
    Returns container_id (pass to publish_ig_media_container).
    Raises RuntimeError if the API response lacks an 'id'.
    """
    response = http_requests.post(
        f"{IG_API_BASE}/{ig_user_id}/media",
        params={
            "image_url": image_url,
            "caption": caption,
            "access_token": access_token,
        },
        timeout=30,
    )
    if not response.ok:
        raise RuntimeError(f"IG container creation failed ({response.status_code}): {response.text}")
    data = response.json()
    if "id" not in data:
        raise RuntimeError(f"IG container creation failed: {data}")
    return data["id"]


def publish_ig_media_container(ig_user_id: str, container_id: str, access_token: str) -> str:
    """Step 2 of 2: Publish an IG media container to the feed.

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


def send_to_telegram(image_bytes: bytes, caption: str, bot_token: str, chat_id: str) -> None:
    """Send image + caption to a Telegram chat via Bot API.

    Sends the photo with caption (truncated to 1024 chars if needed).
    If caption exceeds 1024 chars, sends remainder as a follow-up message.
    """
    photo_url = f"{TELEGRAM_API_BASE}/bot{bot_token}/sendPhoto"
    response = http_requests.post(
        photo_url,
        data={"chat_id": chat_id, "caption": caption[:1024]},
        files={"photo": ("noor.jpg", image_bytes, "image/jpeg")},
        timeout=30,
    )
    response.raise_for_status()
    if not response.json().get("ok"):
        raise RuntimeError(f"Telegram sendPhoto failed: {response.json()}")

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
    cloudinary_cloud_name = os.environ["CLOUDINARY_CLOUD_NAME"]
    cloudinary_api_key = os.environ["CLOUDINARY_API_KEY"]
    cloudinary_api_secret = os.environ["CLOUDINARY_API_SECRET"]
    ig_user_id = os.environ["IG_USER_ID"]
    ig_access_token = os.environ["IG_ACCESS_TOKEN"]
    telegram_token = os.environ["TELEGRAM_BOT_TOKEN"]
    telegram_chat_id = os.environ["TELEGRAM_CHAT_ID"]
    logo_path = Path(__file__).parent / "public" / "noor_logo_white.png"

    print(f"[1/5] Generating content for {today_wib}...")
    content = generate_content(today_wib, claude_client)
    print(f"      Topic: {content['topic']}")
    print(f"      Caption preview: {content['caption'][:60]}...")

    print("[2/5] Generating image with Imagen 4...")
    image_bytes = generate_image(content["image_prompt"], google_client)
    print(f"      Image: {len(image_bytes):,} bytes")

    print("[3/5] Overlaying Noor logo...")
    if logo_path.exists():
        image_bytes = overlay_logo(image_bytes, logo_path)
        print("      Logo composited.")
    else:
        print(f"      Warning: no logo at {logo_path} — skipping overlay")

    print("[4/5] Posting to Instagram...")
    image_url = upload_to_cloudinary(image_bytes, cloudinary_cloud_name, cloudinary_api_key, cloudinary_api_secret)
    print(f"      Uploaded to imgbb: {image_url}")
    container_id = create_ig_media_container(ig_user_id, image_url, content["caption"], ig_access_token)
    media_id = publish_ig_media_container(ig_user_id, container_id, ig_access_token)
    print(f"      Published! media_id={media_id}")

    print("[5/5] Sending to Telegram...")
    send_to_telegram(image_bytes, content["caption"], telegram_token, telegram_chat_id)
    print("      Done!")


if __name__ == "__main__":
    main()
