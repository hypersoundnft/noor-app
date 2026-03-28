"""Daily Instagram post agent for the Noor brand."""

import base64
import io
import json
import os
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import anthropic
import openai
import requests as http_requests
from PIL import Image

# ── Content Generation ────────────────────────────────────────────────────────

TOPIC_ROTATION = ["fitrah", "halal_lens", "lifestyle"]

SYSTEM_PROMPT = """You are the lead content strategist for 'Noor', a modern Islamic lifestyle brand and Halal food scanner. Your tone is encouraging, modern, minimalistic, and trustworthy.

Generate a concept for an Instagram post on the given topic. Output ONLY valid JSON (no markdown, no extra text) with these exact keys:
- "image_prompt": A highly detailed DALL-E 3 image generation prompt. Style: clean, minimalistic, modern Islamic aesthetic, soft lighting, pastel or earth tones. Do NOT include Arabic text or calligraphy in the image.
- "caption": An engaging Instagram caption in English. Max 300 words. End with 3-5 relevant hashtags starting with #.
- "topic": The exact topic string you received.

Topic definitions:
- fitrah: A daily Dua, Quranic reflection, or spiritual reminder
- halal_lens: A hidden Haram ingredient to watch out for in everyday food or cosmetic products
- lifestyle: A modern Muslim lifestyle tip (productivity, wellness, mindful habits)"""


def get_topic_for_date(today: date) -> str:
    """Return topic key based on day-of-year mod 3."""
    return TOPIC_ROTATION[today.timetuple().tm_yday % 3]


def generate_content(today: date, client: anthropic.Anthropic) -> dict:
    """Call Claude to generate image_prompt and caption.

    Returns dict with keys: image_prompt, caption, topic.
    Raises json.JSONDecodeError if the model response is not valid JSON.
    """
    topic = get_topic_for_date(today)
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": f"Generate a Noor Instagram post for topic: {topic}"}],
    )
    # Find the first text block (skip thinking blocks if present)
    raw = next(block.text for block in message.content if block.type == "text")
    # Strip markdown code fences if model wrapped the JSON
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("```", 2)[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()
    return json.loads(raw)


# ── Image Generation ──────────────────────────────────────────────────────────


def generate_image(image_prompt: str, client: openai.OpenAI) -> bytes:
    """Call DALL-E 3 with the given prompt. Downloads and returns raw image bytes."""
    response = client.images.generate(
        model="dall-e-3",
        prompt=image_prompt,
        size="1024x1024",
        quality="standard",
        n=1,
    )
    image_url = response.data[0].url
    r = http_requests.get(image_url, timeout=30)
    r.raise_for_status()
    return r.content


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


def upload_to_imgbb(image_bytes: bytes, api_key: str) -> str:
    """Upload image bytes to imgbb.com and return the public HTTPS URL.

    imgbb free tier: 32 MB max, permanent storage.
    Raises RuntimeError if the API reports failure.
    """
    b64 = base64.b64encode(image_bytes).decode("utf-8")
    response = http_requests.post(
        "https://api.imgbb.com/1/upload",
        data={"key": api_key, "image": b64},
        timeout=30,
    )
    response.raise_for_status()
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
    response.raise_for_status()
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
    """Run the full Noor content pipeline, delivering to Telegram.

    Reads four environment variables:
      ANTHROPIC_API_KEY, OPENAI_API_KEY,
      TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
    """
    today_wib = datetime.now(ZoneInfo("Asia/Jakarta")).date()

    claude_client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    openai_client = openai.OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    telegram_token = os.environ["TELEGRAM_BOT_TOKEN"]
    telegram_chat_id = os.environ["TELEGRAM_CHAT_ID"]
    logo_path = Path(__file__).parent / "public" / "noor_logo_white.png"

    print(f"[1/4] Generating content for {today_wib}...")
    content = generate_content(today_wib, claude_client)
    print(f"      Topic: {content['topic']}")
    print(f"      Caption preview: {content['caption'][:60]}...")

    print("[2/4] Generating image with DALL-E 3...")
    image_bytes = generate_image(content["image_prompt"], openai_client)
    print(f"      Image: {len(image_bytes):,} bytes")

    print("[3/4] Overlaying Noor logo...")
    if logo_path.exists():
        image_bytes = overlay_logo(image_bytes, logo_path)
        print("      Logo composited.")
    else:
        print(f"      Warning: no logo at {logo_path} — skipping overlay")

    print("[4/4] Sending to Telegram...")
    send_to_telegram(image_bytes, content["caption"], telegram_token, telegram_chat_id)
    print("      Done!")


if __name__ == "__main__":
    main()
