# Noor Instagram Agent — Video Reels Design

**Date:** 2026-03-29
**Status:** Approved

## Overview

Upgrade the Noor Instagram agent from static image posts to AI-generated video Reels with voiceover narration. All generation runs on a single `GEMINI_API_KEY` — no Anthropic dependency.

## Pipeline (7 steps)

```
[1] Generate content   — Gemini 2.5 Flash (function calling) → image_prompt, caption, topic, narration
[2] Generate clips     — Veo 2, 3× 8s clips at 9:16 portrait
[3] Concatenate clips  — ffmpeg concat → ~24s MP4
[4] Generate voiceover — Gemini TTS (Kore voice) → WAV
[5] Merge video+audio  — ffmpeg -shortest → final.mp4
[6] Upload             — Cloudinary (resource_type="video")
[7] Post as Reel       — Instagram Graph API (media_type=REELS) + Telegram sendVideo
```

## Content Generation

**Model:** `gemini-2.5-flash`
**Method:** Gemini function calling for structured output (mirrors Claude tool use pattern)
**Output schema:**
- `image_prompt` — cinematic video generation prompt, 9:16 portrait, no Arabic text
- `caption` — Instagram caption, max 300 words, ends with 3–5 hashtags
- `topic` — the topic key (fitrah / halal_lens / lifestyle)
- `narration` — 60–80 word spoken script, warm/calm tone, no hashtags, no markdown, written to be heard

The `image_prompt` doubles as the Veo 2 video prompt.

**Removes:** `anthropic` package, `ANTHROPIC_API_KEY` secret.

## Video Generation

**Model:** `veo-2.0-generate-001`
**Config:** `aspect_ratio="9:16"`, `duration_seconds=8`
**Clips:** 3 sequential calls with the same prompt → 3 MP4 temp files
**Concat:** `ffmpeg -f concat -safe 0 -i clips.txt -c copy combined.mp4`

Generating 3 clips provides ~24s of footage with natural visual variety.

## Voiceover Generation

**Model:** `gemini-2.5-flash-preview-tts`
**Voice:** `Kore` (warm, calm)
**Input:** `narration` field from content generation
**Output:** WAV bytes → temp file

## Video + Audio Merge

```bash
ffmpeg -i combined.mp4 -i narration.wav -c:v copy -c:a aac -shortest final.mp4
```

`-shortest` trims to whichever track ends first. ffmpeg is pre-installed on `ubuntu-latest`.

## Instagram Reels Posting

**Container creation changes:**
- `media_type="REELS"`
- `video_url=<cloudinary_url>` (replaces `image_url`)

**Processing poll:** After container creation, poll `/{container_id}?fields=status_code` every 5 seconds until `status_code == "FINISHED"` before publishing. Timeout after 120 seconds.

**Video requirements (must pass or API rejects):**
- Format: MP4, H.264 video, AAC audio
- Aspect ratio: 9:16 (Veo 2 native output)
- Minimum resolution: 720p
- Duration: 3–90 seconds

## Telegram

Replace `sendPhoto` with `sendVideo`, passing the final MP4 bytes.

## Secrets

| Secret | Change |
|--------|--------|
| `ANTHROPIC_API_KEY` | **Removed** |
| `GEMINI_API_KEY` | Existing — now covers content + video + TTS |
| `CLOUDINARY_*` | Existing — unchanged |
| `IG_USER_ID` | Existing — unchanged |
| `IG_ACCESS_TOKEN` | Existing — unchanged |
| `TELEGRAM_BOT_TOKEN` | Existing — unchanged |
| `TELEGRAM_CHAT_ID` | Existing — unchanged |

## GitHub Actions

Workflow timeout bumped from 10 → **20 minutes** to accommodate video generation (3 Veo 2 calls + processing wait).
