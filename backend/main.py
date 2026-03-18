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

from config import (
    GOOGLE_API_KEY,
    # XAI_API_KEY,  # GROK: Uncomment to use Grok
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
                image_path = GENERATED_DIR / image_filename
                
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
            image_url=f"/generated/{image_filename}",
            body=article_data["body"],
            year=datetime.now().year
        )
        
        # Step 5: Save HTML file
        html_filename = f"{article_id}.html"
        html_path = ARTICLES_DIR / html_filename
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        
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
            image_url=f"/generated/{image_filename}",
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
    Publish article to your hosted domain.
    For now, returns the local article URL.
    TODO: Implement actual publishing to GitHub Pages, Cloudflare, or other hosting.
    """
    if article_id not in articles_store:
        raise HTTPException(status_code=404, detail="Article not found")
    
    article = articles_store[article_id]
    
    # For now, just return the local URL
    # In production, implement actual publishing here:
    # - Upload to GitHub Pages
    # - Upload to Cloudflare R2
    # - Deploy to Vercel/Netlify
    
    published_url = f"http://localhost:8000/articles/{article_id}.html"
    articles_store[article_id]["published_url"] = published_url
    
    return {
        "article_id": article_id,
        "published_url": published_url,
        "headline": article["headline"],
        "message": "Article is available locally. Configure hosting for public publishing."
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
