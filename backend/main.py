"""
AI Misinformation Generator Demo - FastAPI Backend

Provides endpoints for:
1. Prompt orchestration via Gemini 3 Flash
2. Image generation via Gemini 3.1 Flash Image
3. Video generation via Veo 3.1 Fast
"""

import base64
import os
import time
import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from google import genai
from google.genai import types

from config import (
    GOOGLE_API_KEY,
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

# --- Google AI Client ---
client = genai.Client(api_key=GOOGLE_API_KEY)

# --- In-memory store for video operations ---
video_operations: dict = {}


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
    Use Gemini 3 Flash to orchestrate a descriptive generation prompt
    based on the selected target and narrative.
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
        response = client.models.generate_content(
            model=PROMPT_MODEL,
            contents=[orchestration_prompt],
        )
        generated_prompt = response.text.strip()
        return PromptResponse(
            prompt=generated_prompt,
            target=target,
            narrative=narrative,
        )
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
            status_code=500, 
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
                person_generation="allow_adult",
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
