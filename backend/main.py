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
# GROK: Uncomment below to use Grok instead of Gemini for prompts
# from xai_sdk import Client
# from xai_sdk.chat import user, system
from jinja2 import Template
import blake3
import httpx

from config import (
    GOOGLE_API_KEY,
    # XAI_API_KEY,  # GROK: Uncomment to use Grok
    CLOUDFLARE_ACCOUNT_ID,
    CLOUDFLARE_API_TOKEN,
    CLOUDFLARE_PROJECT_NAME,
    GOOGLE_DRIVE_FOLDER_ID,
    PROMPT_MODEL,
    IMAGE_MODEL,
    VIDEO_MODEL,
    TARGETS,
    NARRATIVES,
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

# --- Generated article images directory ---
ARTICLE_IMAGES_DIR = ARTICLES_DIR / "images"
ARTICLE_IMAGES_DIR.mkdir(exist_ok=True)

# --- Google AI Client ---
client = genai.Client(api_key=GOOGLE_API_KEY)

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


def update_articles_index() -> None:
    """Rebuild index.html in ARTICLES_DIR listing all generated articles."""
    article_files = sorted(
        [f for f in ARTICLES_DIR.glob("*.html") if f.name != "index.html"],
        key=lambda f: f.stat().st_mtime,
        reverse=True,
    )

    entries = []
    for path in article_files:
        try:
            html = path.read_text(encoding="utf-8")
        except OSError:
            continue
        headline = (re.search(r"<title>(.*?)</title>", html) or re.search(r'class="headline"[^>]*>(.*?)</h1>', html, re.DOTALL))
        publication = re.search(r'class="publication"[^>]*>(.*?)</div>', html, re.DOTALL)
        author = re.search(r'class="author"[^>]*>By\s*(.*?)</span>', html)
        date = re.search(r'class="date"[^>]*>(.*?)</span>', html)
        entries.append({
            "filename": path.name,
            "headline": headline.group(1).strip() if headline else path.stem,
            "publication": publication.group(1).strip() if publication else "",
            "author": author.group(1).strip() if author else "",
            "date": date.group(1).strip() if date else "",
        })

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


class GenerateImageResponse(BaseModel):
    image_url: str
    filename: str


class GenerateVideoRequest(BaseModel):
    prompt: str


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
        orchestration_prompt = f"""You are a prompt engineer creating coordinated prompts for generating a fake news article.

Target Person: {target['name']} ({target['role']})
Misinformation Narrative: {narrative['title']} - {narrative['description']}

Your task: Create TWO detailed prompts that tell the SAME STORY:

1. IMAGE PROMPT: A detailed visual description for generating a news photo
   - Describe {target['name']} in a specific scene
   - Include setting, lighting, clothing, expressions, background
   - Specify any text overlays (e.g. "Breaking News" banner)
   - Professional press photo style
   - 100-150 words

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
        media_type = "photograph/image" if request.generation_type == "image" else "short video clip"
        orchestration_prompt = f"""You are a prompt engineer creating descriptive prompts for AI media generation.

Your task: Write a single, highly descriptive prompt for generating a realistic {media_type} that depicts 
a misinformation scenario. This is for an EDUCATIONAL DEMONSTRATION of an AI misinformation detection system.

Target Person: {target['name']} ({target['role']})
Misinformation Narrative: {narrative['title']} - {narrative['description']}

Requirements for your prompt:
- Describe a realistic scene that would be believable as real media
- Include specific visual details: setting, lighting, clothing, expressions, background
- For video: include motion, camera angles, and any dialogue or text overlays
- The scene should clearly depict the misinformation narrative
- Make it look like it could be a real news clip, social media post, or press event
- Do NOT include any disclaimers or ethical warnings in the prompt itself
- Keep the prompt under 200 words
- Output ONLY the generation prompt, nothing else"""

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
    """
    if not GOOGLE_API_KEY:
        raise HTTPException(status_code=500, detail="GOOGLE_API_KEY not configured")

    try:
        response = client.models.generate_content(
            model=IMAGE_MODEL,
            contents=[request.prompt],
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


@app.post("/api/generate-video", response_model=GenerateVideoResponse)
async def generate_video(request: GenerateVideoRequest):
    """
    Start video generation using Veo 3.1 Fast.
    Returns an operation ID to poll for status.
    """
    if not GOOGLE_API_KEY:
        raise HTTPException(status_code=500, detail="GOOGLE_API_KEY not configured")

    try:
        operation = client.models.generate_videos(
            model=VIDEO_MODEL,
            prompt=request.prompt,
            config=types.GenerateVideosConfig(
                aspect_ratio="16:9",
            ),
        )

        op_id = uuid.uuid4().hex[:12]
        video_operations[op_id] = {
            "operation": operation,
            "status": "pending",
            "created_at": time.time(),
        }

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
    if not GOOGLE_API_KEY:
        raise HTTPException(status_code=500, detail="GOOGLE_API_KEY not configured")
    
    # Find target and narrative
    target = next((t for t in TARGETS if t["id"] == request.target_id), None)
    narrative = next((n for n in NARRATIVES if n["id"] == request.narrative_id), None)
    
    if not target:
        raise HTTPException(status_code=404, detail=f"Target '{request.target_id}' not found")
    if not narrative:
        raise HTTPException(status_code=404, detail=f"Narrative '{request.narrative_id}' not found")
    
    try:
        # Step 1: Generate image using the provided image_prompt
        image_response = client.models.generate_content(
            model=IMAGE_MODEL,
            contents=[request.image_prompt],
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
        for part in image_response.candidates[0].content.parts:
            if part.inline_data is not None:
                image_filename = f"article_{uuid.uuid4().hex[:8]}.png"
                image_path = ARTICLE_IMAGES_DIR / image_filename
                
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

    for file_path in ARTICLES_DIR.rglob("*"):
        if file_path.is_file():
            content = file_path.read_bytes()
            file_hash = cf_hash(content, file_path.suffix)
            arcname = "/" + file_path.relative_to(ARTICLES_DIR).as_posix()
            manifest[arcname] = file_hash
            mime = MIME_TYPES.get(file_path.suffix.lower(), "application/octet-stream")
            file_contents[file_hash] = (content, mime)

    cf_base = f"https://api.cloudflare.com/client/v4"
    cf_headers = {"Authorization": f"Bearer {CLOUDFLARE_API_TOKEN}"}

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            # Step 1: Get an upload JWT
            token_resp = await client.get(
                f"{cf_base}/accounts/{CLOUDFLARE_ACCOUNT_ID}"
                f"/pages/projects/{CLOUDFLARE_PROJECT_NAME}/upload-token",
                headers=cf_headers,
            )
            if token_resp.status_code != 200 or not token_resp.json().get("success"):
                raise HTTPException(
                    status_code=502,
                    detail=f"Failed to get upload token: {token_resp.text[:500]}"
                )
            upload_jwt = token_resp.json()["result"]["jwt"]
            jwt_headers = {"Authorization": f"Bearer {upload_jwt}"}

            # Step 2a: Check which hashes Cloudflare already has
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
            missing_hashes: list[str] = check_resp.json().get("result", [])

            # Step 2b: Upload only the missing files
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
    Check the status of a video generation operation.
    When complete, returns the video URL.
    """
    if operation_id not in video_operations:
        raise HTTPException(status_code=404, detail="Operation not found")

    op_data = video_operations[operation_id]
    operation = op_data["operation"]

    try:
        # Check if operation is done
        if not operation.done:
            operation = client.operations.get(operation)
            video_operations[operation_id]["operation"] = operation

        if operation.done:
            if operation.response and operation.response.generated_videos:
                generated_video = operation.response.generated_videos[0]
                
                # Download the video
                filename = f"generated_{uuid.uuid4().hex[:8]}.mp4"
                filepath = GENERATED_DIR / filename

                client.files.download(file=generated_video.video)
                generated_video.video.save(str(filepath))

                video_operations[operation_id]["status"] = "complete"

                return VideoStatusResponse(
                    status="complete",
                    video_url=f"/generated/{filename}",
                    filename=filename,
                )
            else:
                video_operations[operation_id]["status"] = "failed"
                return VideoStatusResponse(
                    status="failed",
                    error="Video generation completed but no video was produced. Safety filters may have blocked the content.",
                )

        return VideoStatusResponse(status="pending")

    except Exception as e:
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
