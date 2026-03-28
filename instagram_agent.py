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
        model="claude-opus-4-6",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": f"Generate a Noor Instagram post for topic: {topic}"}],
    )
    return json.loads(message.content[0].text)


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
