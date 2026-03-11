"""
Configuration for the AI Misinformation Generator Demo.
Contains target figures, narrative topics, and model settings.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# --- Google AI SDK ---
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")

# --- Model Configuration ---
PROMPT_MODEL = "gemini-3.1-flash-lite-preview"           # For prompt orchestration (text)
IMAGE_MODEL = "gemini-3.1-flash-image-preview"  # For image generation
VIDEO_MODEL = "veo-3.1-fast-generate-preview"   # For video generation (fast)

# --- Target Figures (Singapore Context) ---
TARGETS = [
    {
        "id": "lawrence_wong",
        "name": "Lawrence Wong",
        "role": "Prime Minister of Singapore",
        "category": "politician",
        "description": "Current PM of Singapore, leader of the PAP.",
    },
    {
        "id": "lee_hsien_loong",
        "name": "Lee Hsien Loong",
        "role": "Senior Minister",
        "category": "politician",
        "description": "Former PM and Senior Minister of Singapore.",
    },
    {
        "id": "tharman_shanmugaratnam",
        "name": "Tharman Shanmugaratnam",
        "role": "President of Singapore",
        "category": "politician",
        "description": "Current President of Singapore.",
    },
    {
        "id": "k_shanmugam",
        "name": "K. Shanmugam",
        "role": "Minister for Home Affairs and Law",
        "category": "politician",
        "description": "Minister for Home Affairs and Minister for Law.",
    },
    {
        "id": "heng_swee_keat",
        "name": "Heng Swee Keat",
        "role": "Deputy Prime Minister",
        "category": "politician",
        "description": "Deputy Prime Minister and Coordinating Minister.",
    },
    {
        "id": "jj_lin",
        "name": "JJ Lin",
        "role": "Singer-Songwriter",
        "category": "celebrity",
        "description": "Internationally renowned Singaporean singer.",
    },
    {
        "id": "stefanie_sun",
        "name": "Stefanie Sun",
        "role": "Singer",
        "category": "celebrity",
        "description": "Iconic Singaporean Mandopop singer.",
    },
    {
        "id": "fandi_ahmad",
        "name": "Fandi Ahmad",
        "role": "Football Legend",
        "category": "celebrity",
        "description": "Singapore's most celebrated footballer.",
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
        "description": "Fabricated inflammatory statements targeting specific racial or religious groups in Singapore.",
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
        "description": "Fabricated content designed to stoke racial discord and undermine social harmony.",
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
