"""
AI Misinformation Generator Demo - FastAPI Backend

Provides endpoints for:
1. Prompt orchestration via Gemini (Grok commented out temporarily)
2. Image generation via Gemini 3.1 Flash Image
3. Video generation via Veo 3.1 Fast
4. Article generation with HTML rendering
"""

import base64
import json
import os
import re
import time
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from google import genai
from google.genai import types
import fal_client
# GROK: Uncomment below to use Grok instead of Gemini for prompts
# from xai_sdk import Client
# from xai_sdk.chat import user, system
from jinja2 import Template
import blake3
import httpx

from config import (
    GOOGLE_API_KEY,
    FAL_KEY,
    # XAI_API_KEY,  # GROK: Uncomment to use Grok
    GOOGLE_DRIVE_FOLDER_ID,
    CLOUDFLARE_ACCOUNT_ID,
    CLOUDFLARE_API_TOKEN,
    CLOUDFLARE_PROJECT_NAME,
    PROMPT_MODEL,
    IMAGE_MODEL,
    VIDEO_MODEL,
    TARGETS,
    NARRATIVES,
    SAMPLE_IMAGES_DIR,
)
from drive_upload import upload_file_to_drive

# --- App Setup ---
app = FastAPI(
    title="AI Misinformation Generator Demo",
    description="Demo tool for generating AI-fabricated media for misinformation detection showcase",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Generated media directory ---
GENERATED_DIR = Path(__file__).parent / "generated"
GENERATED_DIR.mkdir(exist_ok=True)
app.mount("/generated", StaticFiles(directory=str(GENERATED_DIR)), name="generated")

# --- Generated articles directory ---
ARTICLES_DIR = GENERATED_DIR / "articles"
ARTICLES_DIR.mkdir(exist_ok=True)
app.mount("/articles", StaticFiles(directory=str(ARTICLES_DIR), html=True), name="articles")

# --- Google AI Client ---
client = genai.Client(api_key=GOOGLE_API_KEY)

# --- FAL Client for Image-to-Video ---
if FAL_KEY:
    import os as fal_os
    fal_os.environ["FAL_KEY"] = FAL_KEY

# --- xAI Grok Client (COMMENTED OUT - using Gemini for now) ---
# GROK: Uncomment below to use Grok for prompt generation
# grok_client = Client(
#     api_key=XAI_API_KEY,
#     timeout=3600,
# )

# --- In-memory store for video operations ---
video_operations: dict = {}

# --- In-memory store for articles ---
articles_store: dict = {}


def _extract_article_entry(path: Path) -> dict | None:
    """Extract display metadata from a single article HTML file."""
    try:
        html = path.read_text(encoding="utf-8")
    except OSError:
        return None
    headline = (re.search(r"<title>(.*?)</title>", html) or re.search(r'class="headline"[^>]*>(.*?)</h1>', html, re.DOTALL))
    publication = re.search(r'class="publication"[^>]*>(.*?)</div>', html, re.DOTALL)
    author = re.search(r'class="author"[^>]*>By\s*(.*?)</span>', html)
    date = re.search(r'class="date"[^>]*>(.*?)</span>', html)
    return {
        "filename": path.name,
        "headline": headline.group(1).strip() if headline else path.stem,
        "publication": publication.group(1).strip() if publication else "",
        "author": author.group(1).strip() if author else "",
        "date": date.group(1).strip() if date else "",
    }


def update_articles_index(remote_entries: list[dict] | None = None) -> list[dict]:
    """
    Rebuild index.html merging remote_entries (all previously published articles
    from CF's _articles_meta.json) with locally available HTML files.

    Articles present in remote_entries but deleted locally are preserved in the
    index so that CF-hosted articles are never removed from the listing.

    Returns the merged entries list for saving as _articles_meta.json.
    """
    # Start from remote entries keyed by filename so CF-only articles are preserved.
    remote_by_filename: dict[str, dict] = {e["filename"]: e for e in (remote_entries or [])}

    # Scan local HTML files: refresh metadata for existing entries, collect new ones.
    local_files = sorted(
        [f for f in ARTICLES_DIR.glob("*.html") if f.name != "index.html"],
        key=lambda f: f.stat().st_mtime,
        reverse=True,
    )
    new_local: list[dict] = []
    for path in local_files:
        entry = _extract_article_entry(path)
        if entry:
            if path.name in remote_by_filename:
                remote_by_filename[path.name] = entry  # refresh metadata
            else:
                new_local.append(entry)  # brand-new article

    # Order: new local articles (newest first) then remote entries in original order.
    remote_ordered = [remote_by_filename[e["filename"]] for e in (remote_entries or [])
                      if e["filename"] in remote_by_filename]
    entries = new_local + remote_ordered

    rows = ""
    for e in entries:
        rows += f"""
        <tr>
            <td><a href="{e['filename']}">{e['headline']}</a></td>
            <td>{e['publication']}</td>
            <td>{e['author']}</td>
            <td>{e['date']}</td>
        </tr>"""

    index_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI-Generated Articles — Research Index</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #f0f2f5; color: #1a1a1a; }}
        .banner {{ background: #b91c1c; color: white; padding: 18px 32px; }}
        .banner h1 {{ font-size: 1.1em; font-weight: 700; letter-spacing: 0.05em; text-transform: uppercase; }}
        .container {{ max-width: 1000px; margin: 32px auto; padding: 0 24px; }}
        .disclaimer-box {{
            background: #fff8e1;
            border: 2px solid #f59e0b;
            border-left: 6px solid #b91c1c;
            border-radius: 6px;
            padding: 24px 28px;
            margin-bottom: 36px;
        }}
        .disclaimer-box h2 {{ color: #b91c1c; font-size: 1.15em; margin-bottom: 12px; }}
        .disclaimer-box p {{ color: #444; line-height: 1.7; margin-bottom: 10px; font-size: 0.95em; }}
        .disclaimer-box p:last-child {{ margin-bottom: 0; }}
        .disclaimer-box strong {{ color: #b91c1c; }}
        h2.section-title {{ font-size: 1em; text-transform: uppercase; letter-spacing: 0.08em; color: #555; margin-bottom: 16px; }}
        table {{ width: 100%; border-collapse: collapse; background: white; border-radius: 6px; overflow: hidden; box-shadow: 0 1px 4px rgba(0,0,0,0.1); }}
        thead {{ background: #1a1a1a; color: white; }}
        th {{ padding: 12px 16px; text-align: left; font-size: 0.85em; text-transform: uppercase; letter-spacing: 0.06em; }}
        td {{ padding: 12px 16px; border-bottom: 1px solid #e5e7eb; font-size: 0.92em; vertical-align: top; }}
        tr:last-child td {{ border-bottom: none; }}
        tr:hover td {{ background: #f9fafb; }}
        td a {{ color: #1d4ed8; text-decoration: none; font-weight: 500; }}
        td a:hover {{ text-decoration: underline; }}
        .empty {{ padding: 32px; text-align: center; color: #888; font-size: 0.95em; }}
        .count {{ color: #6b7280; font-size: 0.85em; margin-bottom: 10px; }}
    </style>
</head>
<body>
    <div class="banner">
        <h1>SUTD Capstone Research — AI-Generated Article Corpus</h1>
    </div>
    <div class="container">
        <div class="disclaimer-box">
            <h2>&#9888; Research Disclaimer — Read Before Proceeding</h2>
            <p>
                This page is part of a <strong>SUTD Capstone research project</strong> investigating the robustness
                of AI-generated misinformation detection systems. All articles listed below are
                <strong>entirely fabricated by a large language model (LLM)</strong> and were generated
                for the sole purpose of evaluating automated classifiers.
            </p>
            <p>
                <strong>The articles are fake.</strong> Every headline, author name, publication name,
                quote, statistic, and event described within them is fictional and was synthetically
                produced. None of the content reflects real events, real statements by real people,
                or factual information of any kind.
            </p>
            <p>
                The individual article pages intentionally omit AI-generation notices so that the
                classifier under evaluation does not encounter any superficial textual cues that
                would introduce bias into the experiment. The disclaimer you are reading <em>now</em>
                is the authoritative source of context for this corpus.
            </p>
            <p>
                <strong>Do not share, republish, or present any of these articles as real.</strong>
                Misuse of synthetically generated misinformation content, even for unintentional
                distribution, can cause real-world harm.
            </p>
        </div>

        <h2 class="section-title">Generated Articles</h2>
        <p class="count">{len(entries)} article{"s" if len(entries) != 1 else ""} in corpus &mdash; newest first</p>
        <table>
            <thead>
                <tr>
                    <th>Headline</th>
                    <th>Publication</th>
                    <th>Author</th>
                    <th>Date</th>
                </tr>
            </thead>
            <tbody>
                {"<tr><td colspan='4' class='empty'>No articles generated yet.</td></tr>" if not entries else rows}
            </tbody>
        </table>
    </div>
</body>
</html>
"""
    index_path = ARTICLES_DIR / "index.html"
    index_path.write_text(index_html, encoding="utf-8")
    return entries


# =========================================================================
# Request / Response Models
# =========================================================================

class PromptRequest(BaseModel):
    target_id: str
    narrative_id: str
    generation_type: str = "image"  # "image" or "video"


class PromptResponse(BaseModel):
    prompt: str
    target: dict
    narrative: dict
    # For articles: dual coordinated prompts
    image_prompt: str | None = None
    article_prompt: str | None = None
    # For articles: dual prompts
    image_prompt: str | None = None
    article_prompt: str | None = None


class GenerateImageRequest(BaseModel):
    prompt: str
    target_id: str | None = None  # Optional: used to send portrait reference image


class GenerateImageResponse(BaseModel):
    image_url: str
    filename: str


class GenerateVideoRequest(BaseModel):
    image_filename: str  # Filename of the generated image to convert to video
    narration_prompt: str  # Description of what happens/is said in the video


class GenerateVideoResponse(BaseModel):
    operation_id: str
    status: str


class VideoStatusResponse(BaseModel):
    status: str  # "pending", "complete", "failed"
    video_url: str | None = None
    filename: str | None = None
    error: str | None = None

class GenerateArticleRequest(BaseModel):
    target_id: str
    narrative_id: str
    image_prompt: str
    article_prompt: str

class GenerateArticleResponse(BaseModel):
    article_id: str
    article_url: str  # Local preview URL
    headline: str
    image_url: str
    published_url: str | None = None  # Will be set after publishing

# =========================================================================
# Endpoints
# =========================================================================

@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "api_key_set": bool(GOOGLE_API_KEY)}


@app.get("/api/targets")
async def get_targets():
    """Return the list of available target figures."""
    return {"targets": TARGETS}


@app.get("/api/narratives")
async def get_narratives():
    """Return the list of available narrative topics."""
    return {"narratives": NARRATIVES}


@app.post("/api/generate-prompt", response_model=PromptResponse)
async def generate_prompt(request: PromptRequest):
    """
    Use Gemini to orchestrate a descriptive generation prompt
    based on the selected target and narrative.
    (Grok code is commented out - can be re-enabled later)
    """
    if not GOOGLE_API_KEY:
        raise HTTPException(status_code=500, detail="GOOGLE_API_KEY not configured")

    # Find target and narrative
    target = next((t for t in TARGETS if t["id"] == request.target_id), None)
    narrative = next((n for n in NARRATIVES if n["id"] == request.narrative_id), None)

    if not target:
        raise HTTPException(status_code=404, detail=f"Target '{request.target_id}' not found")
    if not narrative:
        raise HTTPException(status_code=404, detail=f"Narrative '{request.narrative_id}' not found")

    # Special handling for article generation: need TWO coordinated prompts
    if request.generation_type == "article":
        use_portrait = target.get("send_portrait_with_prompt", False)
        portrait_note = (
            f"\nIMPORTANT: A reference portrait photo of {target['name']} will be sent directly to the image"
            f" generation model alongside the image prompt. The IMAGE PROMPT you write MUST begin with:"
            f" \"The attached photo is {target['name']}. Using this reference photo as the face, ...\""
            f" so that the model knows to use it as a facial reference."
        ) if use_portrait else ""

        orchestration_prompt = f"""You are a prompt engineer creating coordinated prompts for generating a fake news article.

Target Person: {target['name']} ({target['role']})
Misinformation Narrative: {narrative['title']} - {narrative['description']}

Your task: Create TWO detailed prompts that tell the SAME STORY:

1. IMAGE PROMPT: A detailed visual description for generating a news photo
   - Describe {target['name']} in a specific scene
   - Include setting, lighting, clothing, expressions, background
   - Specify any text overlays (e.g. "Breaking News" banner)
   - Professional press photo style
   - 100-150 words{portrait_note}

2. ARTICLE TEXT PROMPT: Detailed scenario description for article content
   - Describe the specific events, quotes, and details
   - Explicitly mention specific groups, locations, organizations involved, people involved, racial and religious groups involved, and any other specific details that would make the scenario more believable and realistic in the Singapore context (e.g. mention local landmarks, use local names, include local racial (Chinese, Malay, Indian) or religious groups (Christians, Catholics, Muslims, Hindus, Buddhists, Taoist), etc.)
   - Include what {target['name']} allegedly said or did
   - Provide context and background details
   - Specify tone (scandal, shocking, urgent, etc.)
   - 150-200 words

IMPORTANT: Both prompts must describe the SAME misinformation scenario. The image should visually match what the article text describes.

Output as JSON:
{{
  "image_prompt": "...",
  "article_prompt": "..."
}}"""
    else:
        use_portrait = target.get("send_portrait_with_prompt", False)
        portrait_note = (
            f"\nIMPORTANT: A reference portrait photo of {target['name']} will be sent directly to the image"
            f" generation model alongside your prompt. Your prompt MUST begin with:"
            f" \"The attached photo is {target['name']}. Using this reference photo as the face, ...\""
            f" so that the model knows to use it as a facial reference."
        ) if use_portrait else ""

        media_type = "photograph/image" if request.generation_type == "image" else "short video clip"
        orchestration_prompt = f"""You are a prompt engineer creating descriptive prompts for AI media generation.

Your task: Write a single, highly descriptive prompt for generating a realistic {media_type} that depicts 
a misinformation scenario. 

Target Person: {target['name']} ({target['role']})
Misinformation Narrative: {narrative['title']} - {narrative['description']}

Requirements for your prompt:
- Describe a realistic scene that would be believable as real media
- Include specific visual details: setting, lighting, clothing, expressions, background
- Specify any text overlays (e.g. "Breaking News" banner)
- Make it look like a real news clip, social media post, or press event
- Keep the prompt under 200 words
- Output ONLY the generation prompt, nothing else{portrait_note}
"""

    try:
        # Using Gemini for now (Grok code commented out below)
        response = client.models.generate_content(
            model=PROMPT_MODEL,
            contents=[orchestration_prompt],
            config=types.GenerateContentConfig(
                temperature=0.7,
                max_output_tokens=800,
                response_mime_type="application/json" if request.generation_type == "article" else None,
            ),
        )
        
        # Check if response has candidates
        if not response.candidates or len(response.candidates) == 0:
            raise HTTPException(
                status_code=400,
                detail="Prompt generation blocked by safety filters. Try a different target or narrative combination."
            )
        
        generated_prompt = response.text.strip()
        
        # GROK: Uncomment below to use Grok instead of Gemini
        # chat = grok_client.chat.create(model=PROMPT_MODEL)
        # chat.append(system("You are a prompt engineer creating descriptive prompts for AI media generation."))
        # chat.append(user(orchestration_prompt))
        # response = chat.sample()
        # generated_prompt = response.message.strip()
        
        # Parse response for article type (dual prompts)
        if request.generation_type == "article":
            # Clean markdown formatting if present
            prompt_text = generated_prompt
            if prompt_text.startswith("```"):
                prompt_text = prompt_text.split("```")[1]
                if prompt_text.startswith("json"):
                    prompt_text = prompt_text[4:]
            
            try:
                prompts_data = json.loads(prompt_text.strip())
                return PromptResponse(
                    prompt="",  # Not used for articles
                    target=target,
                    narrative=narrative,
                    image_prompt=prompts_data["image_prompt"],
                    article_prompt=prompts_data["article_prompt"],
                )
            except (json.JSONDecodeError, KeyError) as e:
                # Return helpful error with actual response for debugging
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to parse dual prompts. Error: {str(e)}. Gemini response (first 300 chars): {generated_prompt[:300]}"
                )
        
        return PromptResponse(
            prompt=generated_prompt,
            target=target,
            narrative=narrative,
        )
    except HTTPException:
        # Re-raise HTTPExceptions as-is (includes our 400 errors for safety filters)
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prompt generation failed: {str(e)}")


@app.post("/api/generate-image", response_model=GenerateImageResponse)
async def generate_image(request: GenerateImageRequest):
    """
    Generate an image using Gemini 3.1 Flash Image model.
    Returns the URL to the generated image.
    If target_id is provided and that target has send_portrait_with_prompt=True,
    the portrait is sent alongside the prompt as a reference image.
    """
    if not GOOGLE_API_KEY:
        raise HTTPException(status_code=500, detail="GOOGLE_API_KEY not configured")

    try:
        # Build contents: optionally prepend portrait reference image
        contents: list = []
        if request.target_id:
            target = next((t for t in TARGETS if t["id"] == request.target_id), None)
            if target and target.get("send_portrait_with_prompt", False):
                portrait_path = SAMPLE_IMAGES_DIR / f"{request.target_id}.png"
                if portrait_path.exists():
                    portrait_bytes = portrait_path.read_bytes()
                    contents.append(types.Part.from_bytes(data=portrait_bytes, mime_type="image/png"))
                else:
                    print(f"[BACKEND] Warning: portrait not found at {portrait_path}")
        contents.append(request.prompt)

        response = client.models.generate_content(
            model=IMAGE_MODEL,
            contents=contents,
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE", "TEXT"],
            ),
        )

        # Check if response has candidates (safety filters may block content)
        if not response.candidates or len(response.candidates) == 0:
            raise HTTPException(
                status_code=400,
                detail="Content generation blocked by safety filters. Try modifying your prompt."
            )
        
        # Extract image from response parts
        for part in response.candidates[0].content.parts:
            if part.inline_data is not None:
                # Save the image
                filename = f"generated_{uuid.uuid4().hex[:8]}.png"
                filepath = GENERATED_DIR / filename
                
                image_bytes = part.inline_data.data
                if isinstance(image_bytes, str):
                    image_bytes = base64.b64decode(image_bytes)
                
                with open(filepath, "wb") as f:
                    f.write(image_bytes)

                return GenerateImageResponse(
                    image_url=f"/generated/{filename}",
                    filename=filename,
                )

        raise HTTPException(
            status_code=400, 
            detail="No image was generated. The model may have blocked the request due to safety filters. Try modifying the prompt."
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Image generation failed: {str(e)}")


@app.post("/api/generate-narration")
async def generate_narration(request: dict):
    """
    Generate a narration prompt for video based on the image prompt.
    This describes what is being said/narrated in the video.
    """
    if not GOOGLE_API_KEY:
        raise HTTPException(status_code=500, detail="GOOGLE_API_KEY not configured")
    
    image_prompt = request.get("image_prompt", "")
    target_id = request.get("target_id", "")
    narrative_id = request.get("narrative_id", "")
    
    # Find target and narrative
    target = next((t for t in TARGETS if t["id"] == target_id), None)
    narrative = next((n for n in NARRATIVES if n["id"] == narrative_id), None)
    
    if not target or not narrative:
        raise HTTPException(status_code=404, detail="Target or narrative not found")
    
    narration_orchestration = f"""You are creating a narration/voiceover script for a short video clip.

The video will be based on this image:
{image_prompt}

Target Person: {target['name']} ({target['role']})
Misinformation Narrative: {narrative['title']} - {narrative['description']}

Your task: Write a detailed narration prompt that describes:
1. What {target['name']} is saying (direct quotes or paraphrased speech)
2. Any voiceover narration explaining the scene
3. Camera movements or visual actions (e.g., "camera zooms in", "person walks forward")
4. Text overlays that should appear (e.g., "Breaking News banner")
5. Background sounds or music mood

The narration should:
- Match the visual scene from the image prompt above
- Clearly convey the misinformation narrative
- Sound natural and believable as a real news clip or social media video
- Be 100-150 words
- NOT include any disclaimers

Output ONLY the narration prompt, nothing else."""
    
    try:
        response = client.models.generate_content(
            model=PROMPT_MODEL,
            contents=[narration_orchestration],
            config=types.GenerateContentConfig(
                temperature=0.7,
                max_output_tokens=400,
            ),
        )
        
        if not response.candidates or len(response.candidates) == 0:
            raise HTTPException(
                status_code=400,
                detail="Narration generation blocked by safety filters."
            )
        
        narration_prompt = response.text.strip()
        
        return {
            "narration_prompt": narration_prompt,
            "target": target,
            "narrative": narrative,
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Narration generation failed: {str(e)}")


@app.post("/api/generate-video", response_model=GenerateVideoResponse)
async def generate_video(request: GenerateVideoRequest):
    """
    Start video generation using FAL image-to-video (Grok Imagine Video).
    Takes a generated image and narration prompt, returns an operation ID to poll for status.
    """
    if not FAL_KEY:
        raise HTTPException(status_code=500, detail="FAL_KEY not configured")
    
    # Check if image file exists - try both locations (articles/images/ and generated/)
    image_path = ARTICLES_DIR / "images" / request.image_filename
    if not image_path.exists():
        # Fallback to old location for standalone images
        image_path = GENERATED_DIR / request.image_filename
        if not image_path.exists():
            raise HTTPException(status_code=404, detail=f"Image file '{request.image_filename}' not found")
    
    try:
        # Use Base64 data URI instead of upload_file (more reliable per FAL docs)
        with open(image_path, 'rb') as img_file:
            image_data = base64.b64encode(img_file.read()).decode('utf-8')
        image_url = f"data:image/png;base64,{image_data}"
        
        print(f"[BACKEND] Starting FAL image-to-video generation...")
        print(f"[BACKEND] Using Base64 data URI for image (size: {len(image_data)} bytes)")
        print(f"[BACKEND] Narration prompt: {request.narration_prompt}")
        
        # Submit video generation request to FAL (async)
        handler = fal_client.submit(
            "xai/grok-imagine-video/image-to-video",
            arguments={
                "image_url": image_url,
                "prompt": request.narration_prompt,
            },
        )
        
        op_id = uuid.uuid4().hex[:12]
        video_operations[op_id] = {
            "fal_handler": handler,
            "request_id": handler.request_id,
            "status": "pending",
            "created_at": time.time(),
            "image_filename": request.image_filename,
        }
        
        print(f"[BACKEND] FAL video generation started with operation_id={op_id}, request_id={handler.request_id}")
        
        return GenerateVideoResponse(
            operation_id=op_id,
            status="pending",
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Video generation failed: {str(e)}")

@app.post("/api/generate-article", response_model=GenerateArticleResponse)
async def generate_article(request: GenerateArticleRequest):
    """
    Generate a complete fake news article using coordinated prompts:
    1. Use image_prompt to generate image via /api/generate-image endpoint
    2. Use article_prompt to generate article text
    3. Render HTML from template
    4. Save locally and return URLs
    """
    print(f"[BACKEND] Received generate-article request: target={request.target_id}, narrative={request.narrative_id}")
    print(f"[BACKEND] Image prompt length: {len(request.image_prompt)}, Article prompt length: {len(request.article_prompt)}")
    
    if not GOOGLE_API_KEY:
        raise HTTPException(status_code=500, detail="GOOGLE_API_KEY not configured")
    
    # Find target and narrative
    target = next((t for t in TARGETS if t["id"] == request.target_id), None)
    narrative = next((n for n in NARRATIVES if n["id"] == request.narrative_id), None)
    
    if not target:
        raise HTTPException(status_code=404, detail=f"Target '{request.target_id}' not found")
    if not narrative:
        raise HTTPException(status_code=404, detail=f"Narrative '{request.narrative_id}' not found")
    
    print(f"[BACKEND] Starting image generation...")
    try:
        # Step 1: Generate image using the provided image_prompt
        # Build contents: optionally prepend portrait reference image
        image_contents: list = []
        if target.get("send_portrait_with_prompt", False):
            portrait_path = SAMPLE_IMAGES_DIR / f"{request.target_id}.png"
            if portrait_path.exists():
                portrait_bytes = portrait_path.read_bytes()
                image_contents.append(types.Part.from_bytes(data=portrait_bytes, mime_type="image/png"))
                print(f"[BACKEND] Sending portrait reference image for {target['name']}")
            else:
                print(f"[BACKEND] Warning: portrait not found at {portrait_path}")
        image_contents.append(request.image_prompt)

        image_response = client.models.generate_content(
            model=IMAGE_MODEL,
            contents=image_contents,
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE", "TEXT"],
            ),
        )
        
        # Check if image response has candidates
        if not image_response.candidates or len(image_response.candidates) == 0:
            raise HTTPException(
                status_code=400,
                detail="Image generation blocked by safety filters. Try modifying the image prompt."
            )
        
        # Extract and save image
        image_filename = None
        # Create images directory if it doesn't exist
        images_dir = ARTICLES_DIR / "images"
        images_dir.mkdir(exist_ok=True)
        
        for part in image_response.candidates[0].content.parts:
            if part.inline_data is not None:
                image_filename = f"article_{uuid.uuid4().hex[:8]}.png"
                image_path = images_dir / image_filename
                
                image_bytes = part.inline_data.data
                if isinstance(image_bytes, str):
                    image_bytes = base64.b64decode(image_bytes)
                
                with open(image_path, "wb") as f:
                    f.write(image_bytes)
                break
        
        if not image_filename:
            raise HTTPException(
                status_code=400,
                detail="Failed to generate image. The model blocked the content. Try modifying the image prompt."
            )
        
        print(f"[BACKEND] Image generated successfully: {image_filename}")
        print(f"[BACKEND] Starting article text generation...")
        
        # Step 2: Generate article text using the provided article_prompt
        article_text_prompt = f"""Using this scenario description:

{request.article_prompt}

Write a realistic fake news article for EDUCATIONAL purposes.

Target: {target['name']} ({target['role']})
Narrative: {narrative['title']}

Requirements:
- Headline: Clickbait-style, sensational (60-80 chars)
- Author: Fake journalist name (sounds professional)
- Publication: Make up a news outlet name that sounds legitimate
- Body: 3-4 paragraphs, 300-400 words total
- Include fake quotes from {target['name']} that explicitly mentions the misinformation scenario
- Use specific details that make the story believable (e.g. locations, times, names of people, organizations, racial or religious groups involved, etc.)
- Explicitly mention specific groups, locations, organizations involved, people involved, racial and religious groups involved, and any other specific details that would make the scenario more believable and realistic in the Singapore context (e.g. mention local landmarks, use local names, include local racial (Chinese, Malay, Indian) or religious groups (Christians, Catholics, Muslims, Hindus, Buddhists, Taoist), etc.)
- Sound professional and believable like real journalism
- No disclaimers or warnings in the article itself
- Format body as HTML paragraphs using <p> tags
- The article content must match the scenario described above

Output ONLY valid JSON with no markdown formatting:
{{
  "headline": "...",
  "author": "...",
  "publication": "...",
  "body": "<p>...</p><p>...</p><p>...</p>"
}}"""
        
        # Using Gemini for now (Grok code commented out below)
        response = client.models.generate_content(
            model=PROMPT_MODEL,
            contents=[article_text_prompt],
        )
        
        # Check if response has candidates
        if not response.candidates or len(response.candidates) == 0:
            raise HTTPException(
                status_code=400,
                detail="Article text generation blocked by safety filters. Try modifying the article prompt."
            )
        
        article_text = response.text.strip()
        print(f"[BACKEND] Article text generated, length: {len(article_text)}")
        
        # GROK: Uncomment below to use Grok instead of Gemini
        # chat = grok_client.chat.create(model=PROMPT_MODEL)
        # chat.append(system("You are a professional journalist. Output only valid JSON."))
        # chat.append(user(article_prompt))
        # response = chat.sample()
        # article_text = response.message.strip()
        
        # Parse JSON response
        # Remove markdown code blocks if present
        if article_text.startswith("```"):
            article_text = article_text.split("```")[1]
            if article_text.startswith("json"):
                article_text = article_text[4:]
        article_data = json.loads(article_text.strip())
        
        # Step 4: Load and render HTML template
        template_path = Path(__file__).parent / "templates" / "article_template.html"
        with open(template_path, "r") as f:
            template_content = f.read()
        
        template = Template(template_content)
        
        article_id = uuid.uuid4().hex[:12]
        current_date = datetime.now().strftime("%B %d, %Y")
        
        html_content = template.render(
            headline=article_data["headline"],
            author=article_data["author"],
            publication=article_data["publication"],
            date=current_date,
            image_url=f"images/{image_filename}",
            body=article_data["body"],
            year=datetime.now().year
        )
        
        # Step 5: Save HTML file
        html_filename = f"{article_id}.html"
        html_path = ARTICLES_DIR / html_filename
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        
        # Rebuild the article index
        update_articles_index()
        
        print(f"[BACKEND] Article saved: {html_filename}")
        
        # Store article metadata
        articles_store[article_id] = {
            "headline": article_data["headline"],
            "author": article_data["author"],
            "publication": article_data["publication"],
            "html_path": str(html_path),
            "image_filename": image_filename,
            "created_at": time.time(),
            "published_url": None,
        }
        
        print(f"[BACKEND] Article generation complete! Returning response for article_id={article_id}")
        
        return GenerateArticleResponse(
            article_id=article_id,
            article_url=f"/articles/{html_filename}",
            headline=article_data["headline"],
            image_url=f"/articles/images/{image_filename}",
            published_url=None,
        )
    
    except HTTPException:
        # Re-raise HTTPExceptions as-is (includes our 400 errors for safety filters)
        raise
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to parse article content: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Article generation failed: {str(e)}"
        )

async def _sync_remote_articles(pages_url: str) -> dict[str, str]:
    """
    Download _catalog.json from the live Cloudflare Pages site, sync any files
    listed there that are missing locally, then rebuild index.html.
    Returns remote_catalog dict (path -> hash), empty dict on first deploy or error.
    """
    remote_catalog: dict[str, str] = {}
    async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as http:
        try:
            resp = await http.get(f"{pages_url}/_catalog.json")
            if resp.status_code == 200:
                try:
                    remote_catalog = resp.json()
                    if not isinstance(remote_catalog, dict):
                        print("[SYNC] Warning: remote _catalog.json is not a JSON object; ignoring")
                        remote_catalog = {}
                    else:
                        print(f"[SYNC] Fetched remote catalog with {len(remote_catalog)} entries")
                except Exception as e:
                    print(f"[SYNC] Warning: remote _catalog.json could not be parsed ({e})")
            else:
                print(f"[SYNC] Remote _catalog.json returned {resp.status_code}; first deployment or propagation delay")
        except Exception as e:
            print(f"[SYNC] Could not fetch remote _catalog.json ({e})")

        # Re-download any catalog-listed files missing locally (best-effort).
        for path in remote_catalog:
            if path in ("/_catalog.json", "/index.html", "/_articles_meta.json"):
                continue
            local_path = ARTICLES_DIR / path.lstrip("/")
            if not local_path.exists():
                try:
                    file_resp = await http.get(f"{pages_url}{path}")
                    if file_resp.status_code == 200:
                        local_path.parent.mkdir(parents=True, exist_ok=True)
                        local_path.write_bytes(file_resp.content)
                        print(f"[SYNC] Re-synced {path} from remote")
                    else:
                        print(f"[SYNC] Warning: could not fetch {path} (status {file_resp.status_code})")
                except Exception as e:
                    print(f"[SYNC] Warning: could not re-sync {path} ({e})")

    update_articles_index()  # Rebuild with all articles (local + just-synced)
    return remote_catalog


@app.post("/api/publish-article/{article_id}")
async def publish_article(article_id: str):
    """
    Deploy the entire backend/generated/articles/ directory to Cloudflare Pages
    via the Direct Upload API and return the live article URL.
    """
    if article_id not in articles_store:
        raise HTTPException(status_code=404, detail="Article not found")

    if not all([CLOUDFLARE_ACCOUNT_ID, CLOUDFLARE_API_TOKEN, CLOUDFLARE_PROJECT_NAME]):
        raise HTTPException(
            status_code=500,
            detail="Cloudflare credentials not configured. Set CLOUDFLARE_ACCOUNT_ID, CLOUDFLARE_API_TOKEN, and CLOUDFLARE_PROJECT_NAME in .env"
        )

    article = articles_store[article_id]

    # Collect files and compute hashes using the same algorithm Wrangler uses:
    # BLAKE3( base64(file_bytes) + extension_without_dot )[:32]
    manifest: dict[str, str] = {}
    file_contents: dict[str, tuple[bytes, str]] = {}  # hash -> (bytes, content-type)
    
    MIME_TYPES = {
        ".html": "text/html",
        ".css": "text/css",
        ".js": "application/javascript",
        ".json": "application/json",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".svg": "image/svg+xml",
        ".webp": "image/webp",
        ".ico": "image/x-icon",
        ".woff": "font/woff",
        ".woff2": "font/woff2",
        ".ttf": "font/ttf",
    }

    def cf_hash(content: bytes, suffix: str) -> str:
        ext = suffix.lstrip(".").lower()
        data = base64.b64encode(content).decode() + ext
        return blake3.blake3(data.encode()).hexdigest()[:32]

    # Sync remote articles before building manifest so index.html and manifest
    # include all previously published articles, not just local ones.
    pages_url = f"https://{CLOUDFLARE_PROJECT_NAME}.pages.dev"
    remote_catalog = await _sync_remote_articles(pages_url)

    for file_path in ARTICLES_DIR.rglob("*"):
        if file_path.is_file():
            if file_path.name in ("_catalog.json", "_articles_meta.json"):
                continue  # Rebuilt fresh below; never read a stale disk copy
            content = file_path.read_bytes()
            file_hash = cf_hash(content, file_path.suffix)
            arcname = "/" + file_path.relative_to(ARTICLES_DIR).as_posix()
            manifest[arcname] = file_hash
            content_type = MIME_TYPES.get(file_path.suffix.lower(), "application/octet-stream")
            file_contents[file_hash] = (content, content_type)

    # Merge remote-only entries (e.g. images from other machines' articles).
    # CF already holds their bytes by hash — no re-upload needed.
    for remote_path, remote_hash in remote_catalog.items():
        if remote_path not in manifest:
            manifest[remote_path] = remote_hash

    # After the full manifest is assembled, ensure every article HTML in it has
    # a local copy so update_articles_index() can produce a complete index.html.
    # Some files may not have been downloaded by _sync_remote_articles (e.g. if
    # the sync fetch timed out or CF hadn't propagated yet).
    missing_html = [
        p for p in manifest
        if p.endswith(".html") and p != "/index.html"
        and not (ARTICLES_DIR / p.lstrip("/")).exists()
    ]
    if missing_html:
        print(f"[PUBLISH] {len(missing_html)} article(s) in manifest still missing locally; re-fetching...")
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as fetch_client:
            for path in missing_html:
                try:
                    resp = await fetch_client.get(f"{pages_url}{path}")
                    if resp.status_code == 200:
                        local_path = ARTICLES_DIR / path.lstrip("/")
                        local_path.write_bytes(resp.content)
                        # Add bytes to file_contents so CF can re-upload if needed
                        h = cf_hash(resp.content, ".html")
                        manifest[path] = h
                        file_contents[h] = (resp.content, "text/html")
                        print(f"[PUBLISH] Re-fetched {path}")
                    else:
                        print(f"[PUBLISH] Warning: CF returned {resp.status_code} for {path}")
                except Exception as e:
                    print(f"[PUBLISH] Warning: could not fetch {path}: {e}")

    # Fetch the authoritative article list from CF so that articles deleted locally
    # are never removed from index.html — they still exist on CF Pages.
    remote_meta: list[dict] = []
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as meta_client:
        try:
            meta_resp = await meta_client.get(f"{pages_url}/_articles_meta.json")
            if meta_resp.status_code == 200 and meta_resp.content:
                data = meta_resp.json()
                if isinstance(data, list):
                    remote_meta = data
                    print(f"[PUBLISH] Fetched remote article metadata ({len(remote_meta)} entries)")
            else:
                print(f"[PUBLISH] No existing article metadata on CF (status {meta_resp.status_code}); starting fresh")
        except Exception as e:
            print(f"[PUBLISH] Could not fetch remote article metadata: {e}")

    # Rebuild index.html merging remote metadata with local files, then update manifest.
    merged_entries = update_articles_index(remote_meta)
    index_path = ARTICLES_DIR / "index.html"
    if index_path.exists():
        idx_bytes = index_path.read_bytes()
        idx_hash = cf_hash(idx_bytes, ".html")
        manifest["/index.html"] = idx_hash
        file_contents[idx_hash] = (idx_bytes, "text/html")

    # Build fresh _articles_meta.json from merged entries and add to manifest.
    meta_bytes = json.dumps(merged_entries, indent=2).encode("utf-8")
    meta_hash = cf_hash(meta_bytes, ".json")
    manifest["/_articles_meta.json"] = meta_hash
    file_contents[meta_hash] = (meta_bytes, "application/json")

    # Build a fresh _catalog.json mapping all deployed paths to their hashes.
    # Intentionally excludes its own entry to avoid a circular hash dependency.
    catalog_bytes = json.dumps(manifest, sort_keys=True, indent=2).encode("utf-8")
    catalog_hash = cf_hash(catalog_bytes, ".json")
    manifest["/_catalog.json"] = catalog_hash
    file_contents[catalog_hash] = (catalog_bytes, "application/json")

    # Cloudflare API requests
    cf_base = "https://api.cloudflare.com/client/v4"
    cf_headers = {"Authorization": f"Bearer {CLOUDFLARE_API_TOKEN}"}

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            # Step 1: Get upload JWT
            jwt_resp = await client.get(
                f"{cf_base}/accounts/{CLOUDFLARE_ACCOUNT_ID}/pages/projects/{CLOUDFLARE_PROJECT_NAME}/upload-token",
                headers=cf_headers,
            )
            if jwt_resp.status_code != 200 or not jwt_resp.json().get("success"):
                raise HTTPException(
                    status_code=502,
                    detail=f"Failed to get upload JWT: {jwt_resp.text[:500]}"
                )
            upload_jwt = jwt_resp.json()["result"]["jwt"]
            jwt_headers = {"Authorization": f"Bearer {upload_jwt}"}

            # Step 2a: Check missing hashes
            check_resp = await client.post(
                f"{cf_base}/pages/assets/check-missing",
                headers=jwt_headers,
                json={"hashes": list(file_contents.keys())},
            )
            if check_resp.status_code != 200 or not check_resp.json().get("success"):
                raise HTTPException(
                    status_code=502,
                    detail=f"Failed to check missing assets: {check_resp.text[:500]}"
                )
            missing_hashes = check_resp.json()["result"]

            # Step 2b: Upload missing files
            if missing_hashes:
                upload_payload = [
                    {
                        "key": h,
                        "value": base64.b64encode(file_contents[h][0]).decode(),
                        "metadata": {"contentType": file_contents[h][1]},
                        "base64": True,
                    }
                    for h in missing_hashes
                    if h in file_contents
                ]
                upload_resp = await client.post(
                    f"{cf_base}/pages/assets/upload",
                    headers=jwt_headers,
                    json=upload_payload,
                )
                if upload_resp.status_code != 200 or not upload_resp.json().get("success"):
                    raise HTTPException(
                        status_code=502,
                        detail=f"Failed to upload assets: {upload_resp.text[:500]}"
                    )

            # Step 2c: Upsert all hashes
            upsert_resp = await client.post(
                f"{cf_base}/pages/assets/upsert-hashes",
                headers=jwt_headers,
                json={"hashes": list(file_contents.keys())},
            )
            if upsert_resp.status_code != 200 or not upsert_resp.json().get("success"):
                raise HTTPException(
                    status_code=502,
                    detail=f"Failed to upsert hashes: {upsert_resp.text[:500]}"
                )

            # Step 3: Create the deployment — multipart/form-data required by Cloudflare.
            # Using files= with (None, value) tuples is the httpx pattern for sending
            # multipart text fields. branch, commit_hash, commit_message are all required.
            response = await client.post(
                f"{cf_base}/accounts/{CLOUDFLARE_ACCOUNT_ID}"
                f"/pages/projects/{CLOUDFLARE_PROJECT_NAME}/deployments",
                headers=cf_headers,
                files={
                    "branch":         (None, "main"),
                    "commit_message": (None, f"Publish article {article_id}"),
                    "commit_hash":    (None, article_id.replace("-", "")[:40].ljust(40, "0")),
                    "manifest":       (None, json.dumps(manifest)),
                },
            )
    except HTTPException:
        raise
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Cloudflare API timed out.")
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail=f"Network error: {str(exc)}")
    
    if response.status_code not in (200, 201):
        raise HTTPException(
            status_code=502,
            detail=f"Cloudflare error {response.status_code}: {response.text[:500]}"
        )

    cf_data = response.json()
    if not cf_data.get("success"):
        raise HTTPException(
            status_code=502,
            detail=f"Cloudflare deployment failed: {cf_data.get('errors', [])}"
        )

    published_url = f"https://{CLOUDFLARE_PROJECT_NAME}.pages.dev/{article_id}.html"
    articles_store[article_id]["published_url"] = published_url

    return {
        "article_id": article_id,
        "published_url": published_url,
        "headline": article["headline"],
        "message": "Deployed to Cloudflare Pages. Allow ~30 seconds for propagation.",
    }


@app.get("/api/articles/{article_id}")
async def get_article_info(article_id: str):
    """Get article metadata."""
    if article_id not in articles_store:
        raise HTTPException(status_code=404, detail="Article not found")
    
    return articles_store[article_id]


@app.get("/api/video-status/{operation_id}", response_model=VideoStatusResponse)
async def get_video_status(operation_id: str):
    """
    Check the status of a FAL image-to-video generation operation.
    When complete, returns the video URL.
    """
    if operation_id not in video_operations:
        raise HTTPException(status_code=404, detail="Operation not found")

    op_data = video_operations[operation_id]
    request_id = op_data["request_id"]
    
    try:
        # Check FAL operation status - it returns different object types
        status_result = fal_client.status(
            "xai/grok-imagine-video/image-to-video",
            request_id,
            with_logs=True
        )
        
        print(f"[BACKEND] Checking video status for operation_id={operation_id}, request_id={request_id}")
        print(f"[BACKEND] FAL status type: {type(status_result).__name__}")
        
        # Check if it's a Completed object - need to call result() to get the actual data
        if hasattr(status_result, '__class__') and status_result.__class__.__name__ == 'Completed':
            print(f"[BACKEND] Video generation completed! Fetching result...")
            
            # Get the actual result data
            result = fal_client.result("xai/grok-imagine-video/image-to-video", request_id)
            print(f"[BACKEND] Result keys: {result.keys() if isinstance(result, dict) else 'not a dict'}")
            
            if result and "video" in result:
                video_url = result["video"]["url"]
                
                # Download the video from FAL to local storage
                filename = f"generated_{uuid.uuid4().hex[:8]}.mp4"
                filepath = GENERATED_DIR / filename
                
                import httpx
                async with httpx.AsyncClient() as client:
                    response = await client.get(video_url)
                    with open(filepath, "wb") as f:
                        f.write(response.content)
                
                video_operations[operation_id]["status"] = "complete"
                
                print(f"[BACKEND] Video downloaded and saved to {filename}")
                
                return VideoStatusResponse(
                    status="complete",
                    video_url=f"/generated/{filename}",
                    filename=filename,
                )
            else:
                video_operations[operation_id]["status"] = "failed"
                return VideoStatusResponse(
                    status="failed",
                    error="Video generation completed but no video was returned.",
                )
        
        # Check if it's a completed result (dict with 'video' key) - fallback
        elif isinstance(status_result, dict) and "video" in status_result:
            video_url = status_result["video"]["url"]
            
            # Download the video from FAL to local storage
            filename = f"generated_{uuid.uuid4().hex[:8]}.mp4"
            filepath = GENERATED_DIR / filename
            
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.get(video_url)
                with open(filepath, "wb") as f:
                    f.write(response.content)
            
            video_operations[operation_id]["status"] = "complete"
            
            print(f"[BACKEND] Video generation complete! Saved to {filename}")
            
            return VideoStatusResponse(
                status="complete",
                video_url=f"/generated/{filename}",
                filename=filename,
            )
        
        # Check if it's an InProgress object
        elif isinstance(status_result, fal_client.InProgress):
            print(f"[BACKEND] Video generation in progress...")
            if hasattr(status_result, 'logs') and status_result.logs:
                for log in status_result.logs:
                    print(f"[BACKEND] FAL log: {log.get('message', '')}")
            return VideoStatusResponse(status="pending")
        
        # Check if it's a Queued object
        elif hasattr(status_result, '__class__') and status_result.__class__.__name__ == 'Queued':
            print(f"[BACKEND] Video generation queued...")
            return VideoStatusResponse(status="pending")
        
        # Unknown status type - still pending
        print(f"[BACKEND] Unknown status type, treating as pending")
        return VideoStatusResponse(status="pending")

    except Exception as e:
        print(f"[BACKEND] Error checking video status: {str(e)}")
        video_operations[operation_id]["status"] = "failed"
        return VideoStatusResponse(
            status="failed",
            error=f"Error checking video status: {str(e)}",
        )


@app.get("/api/download/{filename}")
async def download_file(filename: str):
    """Download a generated file."""
    filepath = GENERATED_DIR / filename
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="File not found")

    media_type = "image/png" if filename.endswith(".png") else "video/mp4"
    return FileResponse(
        path=str(filepath),
        filename=filename,
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@app.post("/api/upload-to-drive/{filename}")
async def upload_to_drive(filename: str):
    """
    Upload a generated file to the shared Google Drive folder
    so the detection system can analyse it.
    """
    filepath = GENERATED_DIR / filename
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="File not found")

    if not GOOGLE_DRIVE_FOLDER_ID:
        raise HTTPException(
            status_code=500,
            detail="GOOGLE_DRIVE_FOLDER_ID is not configured in .env",
        )

    try:
        result = upload_file_to_drive(filepath, filename)
        return result
    except FileNotFoundError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to upload to Google Drive: {str(e)}",
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
