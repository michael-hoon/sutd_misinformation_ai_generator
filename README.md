# 🛡️ AI Misinformation Generator — Showcase Demo

> **For educational and demonstration purposes only.**  

A locally-hosted web application that generates AI-fabricated images and videos for testing the misinformation detection pipeline. Users select a target public figure and a misinformation narrative, then the system uses Google's Gemini and Veo models to generate realistic fake media.

## Architecture

```
Frontend (React + Vite + Tailwind)     →     Backend (FastAPI + Google AI SDK)
     ↓                                           ↓
User selects Target + Narrative         Gemini 3 Flash orchestrates prompt
     ↓                                           ↓
Generate button clicked                 Gemini Image / Veo 3.1 generates media
     ↓                                           ↓
Display + Download                      Serves generated files
```

## Quick Start

### Prerequisites
- **Python 3.11+**
- **Node.js 18+**
- **Google AI API Key** with access to Gemini 3 Flash, Gemini Image, and Veo 3.1

### 1. Clone and Configure

```bash
cp .env.template backend/.env
# Edit backend/.env and add your GOOGLE_API_KEY
```

### 2. Start Backend

```bash
cd backend
uv venv --python 3.12
source .venv/bin/activate
uv pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

The API docs will be available at http://localhost:8000/docs

### 3. Start Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 in your browser.

## Usage Flow

1. **Select Target** — Choose a prominent Singaporean figure (politician or celebrity)
2. **Select Narrative** — Pick a misinformation scenario (CDC voucher scam, hate speech, etc.)
3. **Generate** — The system will:
   - Use Gemini 3 Flash to craft a descriptive generation prompt
   - Send that prompt to Gemini Image (for images) or Veo 3.1 Fast (for videos)
   - Display the result for download
4. **Test** — Download the generated media and feed it to the AI Misinformation Detection System

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Frontend | React 19, Vite 7, Tailwind CSS v4 |
| Backend | FastAPI, Python |
| AI Models | Gemini 3 Flash, Gemini 3.1 Flash Image, Grok Imagine |
| SDK | `google-genai` (Google AI SDK) |

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | Health check |
| GET | `/api/targets` | List available targets |
| GET | `/api/narratives` | List available narratives |
| POST | `/api/generate-prompt` | Generate a descriptive prompt via Gemini |
| POST | `/api/generate-image` | Generate an image from prompt |
| POST | `/api/generate-video` | Start video generation (async) |
| GET | `/api/video-status/{id}` | Poll video generation status |
| GET | `/api/download/{filename}` | Download generated file |
