"""
Configuration for the AI Misinformation Generator Demo.
Contains target figures, narrative topics, and model settings.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# --- Google AI SDK ---
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")

# --- fal.ai API for Grok Image Generation (COMMENTED OUT - using Gemini Nano Banana) ---
# FAL_KEY = os.getenv("FAL_KEY", "")  # FAL: Uncomment to use Grok Imagine via fal.ai
# --- Model Configuration ---
PROMPT_MODEL = "gemini-3.1-flash-lite-preview"          # Gemini for prompt orchestration (Grok commented out)
# PROMPT_MODEL = "grok-4.20-beta-latest-non-reasoning"  # GROK: Uncomment to use Grok instead
IMAGE_MODEL = "gemini-3.1-flash-image-preview"        # GEMINI: Nano Banana with reference image support
# IMAGE_MODEL = "xai/grok-imagine-image/edit"             # FAL: Grok image generation via fal.ai (COMMENTED OUT)
VIDEO_MODEL = "veo-3.1-fast-generate-preview"           # For video generation (fast)

# --- Sample Images Directory (for reference images) ---
SAMPLE_IMAGES_DIR = Path(__file__).parent / "sample_images"
# --- Cloudflare Pages ---
CLOUDFLARE_ACCOUNT_ID = os.getenv("CLOUDFLARE_ACCOUNT_ID", "")
CLOUDFLARE_API_TOKEN = os.getenv("CLOUDFLARE_API_TOKEN", "")
CLOUDFLARE_PROJECT_NAME = os.getenv("CLOUDFLARE_PROJECT_NAME", "")

# --- Google Drive Upload (OAuth 2.0) ---
GOOGLE_DRIVE_FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID", "")
OAUTH_CREDENTIALS_FILE = os.getenv(
    "OAUTH_CREDENTIALS_FILE",
    str(Path(__file__).parent / "credentials.json"),
)
OAUTH_TOKEN_FILE = os.getenv(
    "OAUTH_TOKEN_FILE",
    str(Path(__file__).parent / "token.json"),
)

# --- Target Figures (Singapore Context) ---
TARGETS = [
    {
        "id": "lawrence_wong",
        "name": "Lawrence Wong",
        "role": "Prime Minister of Singapore",
        "category": "politician",
        "description": "Current Prime Minister of Singapore, leader of the PAP.",
        "sample_image": "/portraits/lawrence_wong.png"
    },
    {
        "id": "lee_hsien_loong",
        "name": "Lee Hsien Loong",
        "role": "Senior Minister",
        "category": "politician",
        "description": "Former Prime Minister of Singapore and Senior Minister of Singapore.",
        "sample_image": "/portraits/lee_hsien_loong.png"
    },
    {
        "id": "tharman_shanmugaratnam",
        "name": "Tharman Shanmugaratnam",
        "role": "President of Singapore",
        "category": "politician",
        "description": "Current President of Singapore.",
        "sample_image": "/portraits/tharman_shanmugaratnam.png"
    },
    {
        "id": "k_shanmugam",
        "name": "K. Shanmugam",
        "role": "Minister for Home Affairs and Law",
        "category": "politician",
        "description": "Minister for Home Affairs and Minister for Law.",
        "sample_image": "/portraits/k_shanmugam.png"
    },
    {
        "id": "heng_swee_keat",
        "name": "Heng Swee Keat",
        "role": "Deputy Prime Minister",
        "category": "politician",
        "description": "Deputy Prime Minister and Coordinating Minister.",
        "sample_image": "/portraits/heng_swee_keat.png"
    },
    {
        "id": "jj_lin",
        "name": "JJ Lin",
        "role": "Singaporean Mandopop Singer-Songwriter",
        "category": "celebrity",
        "description": "Internationally renowned Singaporean singer.",
        "sample_image": "/portraits/jj_lin.png"
    },
    {
        "id": "stefanie_sun",
        "name": "Stefanie Sun",
        "role": "Singaporean Mandopop Singer",
        "category": "celebrity",
        "description": "Iconic Singaporean Mandopop singer.",
        "sample_image": "/portraits/stefanie_sun.png"
    },
    {
        "id": "fandi_ahmad",
        "name": "Fandi Ahmad",
        "role": "Singaporean Football Legend",
        "category": "celebrity",
        "description": "Singapore's most celebrated footballer.",
        "sample_image": "/portraits/fandi_ahmad.png"
    },
]

# --- Narrative Topics ---
NARRATIVES = [
    {
        "id": "cdc_voucher_scam",
        "title": "CDC Voucher Scam",
        "description": "Fake announcements about CDC voucher disbursement, claiming extra payouts or fraudulent redemption links.",
        "category": "financial_fraud",
        "icon": "💳",
    },
    {
        "id": "hate_speech",
        "title": "Hate Speech",
        "description": "Fabricated inflammatory statements targeting specific racial or religious groups in Singapore (Chinese, Malay, Indians).",
        "category": "social_harm",
        "icon": "🚫",
    },
    {
        "id": "phishing_scam",
        "title": "Phishing / Scam Endorsement",
        "description": "Fake endorsements of investment schemes, cryptocurrency, or financial products.",
        "category": "financial_fraud",
        "icon": "🎣",
    },
    {
        "id": "racial_tensions",
        "title": "Racial Tensions",
        "description": "Fabricated content designed to stoke racial discord and undermine social harmony between local races (Chinese, Malay, Indians).",
        "category": "social_harm",
        "icon": "⚔️",
    },
    {
        "id": "fake_policy",
        "title": "Fake Policy Announcement",
        "description": "Fabricated government policy changes regarding HDB, CPF, NS, or education.",
        "category": "political",
        "icon": "📜",
    },
    {
        "id": "health_misinfo",
        "title": "Health Misinformation",
        "description": "False health claims, fake vaccine warnings, or fabricated pandemic announcements.",
        "category": "health",
        "icon": "🏥",
    },
    {
        "id": "election_misinfo",
        "title": "Election Misinformation",
        "description": "Fabricated statements about election results, voting procedures, or candidate positions.",
        "category": "political",
        "icon": "🗳️",
    },
    {
        "id": "fake_emergency",
        "title": "Fake Emergency Alert",
        "description": "Fabricated emergency warnings about natural disasters, security threats, or public safety.",
        "category": "public_safety",
        "icon": "🚨",
    },
]
