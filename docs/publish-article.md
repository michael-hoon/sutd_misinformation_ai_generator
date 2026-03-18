# Publish Article Feature

This document explains how the "Publish Article" feature works — from the user clicking the button to a live URL being returned.

---

## Overview

After an article is generated locally, it can be published to the internet via **Cloudflare Pages Direct Upload API**. This deploys the entire `backend/generated/articles/` directory (HTML files + images) as a static Cloudflare Pages site, making each article accessible at a public URL.

**Live URL format:** `https://{CLOUDFLARE_PROJECT_NAME}.pages.dev/{article_id}.html`

---

## Architecture

```
User clicks "Publish"
        ↓
Frontend (React)
  publishArticle(articleId) → POST /api/publish-article/{article_id}
        ↓
Backend (FastAPI)
  1. Hash all files in backend/generated/articles/ using BLAKE3
  2. Request an upload JWT from Cloudflare
  3. Check which files Cloudflare already has (deduplication)
  4. Upload only missing files (base64-encoded)
  5. Register all hashes with the Pages project
  6. Create a Pages deployment with the file manifest
        ↓
Cloudflare Pages
  Serves the static site globally via CDN
        ↓
Return: https://<project>.pages.dev/<article_id>.html
```

---

## Prerequisites

Three environment variables must be set before publishing works. Copy `.env.template` and fill them in:

| Variable | Where to find it |
|---|---|
| `CLOUDFLARE_ACCOUNT_ID` | Cloudflare dashboard → right sidebar |
| `CLOUDFLARE_API_TOKEN` | My Profile → API Tokens → Create Token (needs **Cloudflare Pages: Edit** permission) |
| `CLOUDFLARE_PROJECT_NAME` | The name of your Pages project (e.g. `my-news-site` → `my-news-site.pages.dev`) |

> The Pages project must already exist in your Cloudflare account before publishing. Create it once via the Cloudflare dashboard (can be an empty project).

---

## Step-by-Step: How the Cloudflare API Is Used

The backend (`backend/main.py`, endpoint `POST /api/publish-article/{article_id}`) performs five sequential API calls to Cloudflare.

### Step 1 — Get Upload JWT

```
GET https://api.cloudflare.com/client/v4/accounts/{ACCOUNT_ID}/pages/projects/{PROJECT_NAME}/upload-token
Authorization: Bearer {API_TOKEN}
```

Returns a short-lived **JWT token** used to authenticate the asset upload steps (steps 2–4). This is separate from the main API token and is scoped specifically to asset uploads for this project.

---

### Step 2 — Check Missing Assets

```
POST https://api.cloudflare.com/client/v4/pages/assets/check-missing
Authorization: Bearer {UPLOAD_JWT}

Body: { "hashes": ["abc123...", "def456...", ...] }
```

Before uploading, the backend computes a **BLAKE3 hash** for every file and asks Cloudflare which hashes it doesn't already have. This is a **deduplication step** — if you publish twice with only one new article, only the new file gets uploaded.

**Hashing algorithm** (matching Wrangler's formula):
```
hash = BLAKE3(base64(file_bytes) + extension_without_dot)[:32 chars]
```

For example, for `article_abc.html`:
```
hash = BLAKE3(base64(<html bytes>) + "html")[:32]
```

---

### Step 3 — Upload Missing Files

```
POST https://api.cloudflare.com/client/v4/pages/assets/upload
Authorization: Bearer {UPLOAD_JWT}

Body: [
  {
    "key": "<blake3_hash>",
    "value": "<base64_encoded_file_content>",
    "metadata": { "contentType": "text/html" },
    "base64": true
  },
  ...
]
```

Only the files that Cloudflare reported as missing in Step 2 are sent here. Files are uploaded in **batches of up to 50** to stay within API limits.

Supported MIME types: `text/html`, `text/css`, `application/javascript`, `application/json`, `image/png`, `image/jpeg`, `image/gif`, `image/svg+xml`, `image/webp`, `image/x-icon`, `font/woff`, `font/woff2`, `font/ttf`.

---

### Step 4 — Upsert Hashes

```
POST https://api.cloudflare.com/client/v4/pages/assets/upsert-hashes
Authorization: Bearer {UPLOAD_JWT}

Body: { "hashes": ["abc123...", "def456...", ...] }
```

Registers **all** file hashes (not just new ones) with the Pages project. This tells Cloudflare which assets belong to the upcoming deployment.

---

### Step 5 — Create Deployment

```
POST https://api.cloudflare.com/client/v4/accounts/{ACCOUNT_ID}/pages/projects/{PROJECT_NAME}/deployments
Authorization: Bearer {API_TOKEN}
Content-Type: multipart/form-data

Fields:
  branch:         "main"
  commit_message: "Publish article {article_id}"
  commit_hash:    "{article_id padded to 40 chars}"
  manifest:       '{ "/article_abc.html": "hash1", "/images/img.png": "hash2", ... }'
```

The `manifest` is a JSON object mapping every file path (relative to `ARTICLES_DIR`) to its BLAKE3 hash. Cloudflare uses this to assemble the deployment from the previously uploaded assets — no files are transferred in this step.

Once this call succeeds, Cloudflare propagates the deployment globally (~30 seconds).

---

## File Structure Published

The entire `backend/generated/articles/` directory is deployed:

```
backend/generated/articles/
├── index.html              → https://<project>.pages.dev/
├── article_<uuid>.html     → https://<project>.pages.dev/article_<uuid>.html
├── article_<uuid2>.html    → https://<project>.pages.dev/article_<uuid2>.html
└── images/
    ├── article_<uuid>.png  → https://<project>.pages.dev/images/article_<uuid>.png
    └── article_<uuid2>.png → https://<project>.pages.dev/images/article_<uuid2>.png
```

Every publish deploys the full directory. This means **all previously generated articles** are included in each deployment — the Cloudflare site always shows all articles, not just the latest one.

---

## Frontend Integration

**[frontend/src/api.ts](../frontend/src/api.ts)** — API call:
```typescript
export async function publishArticle(articleId: string): Promise<PublishResponse> {
  const res = await api.post(`/api/publish-article/${articleId}`);
  return res.data;
}
```

**[frontend/src/components/GenerationPanel.tsx](../frontend/src/components/GenerationPanel.tsx)** — UI handler:
- The "Publish Article" button is enabled after article generation completes.
- During publishing, a spinner is shown.
- On success, the `published_url` is displayed as a clickable link.
- On failure, the error message from the backend is shown.

---

## Response

On success, the backend returns:

```json
{
  "article_id": "article_abc123",
  "published_url": "https://my-news-site.pages.dev/article_abc123.html",
  "headline": "Breaking: ...",
  "message": "Article published successfully. May take ~30 seconds to propagate."
}
```

---

## Error Handling

| Scenario | HTTP Status | Message |
|---|---|---|
| Missing Cloudflare env vars | 500 | Lists which variables are missing |
| Upload token request failed | 502 | "Failed to get upload token" |
| Asset check failed | 502 | "Failed to check missing assets" |
| File upload failed | 502 | "Failed to upload assets" |
| Hash upsert failed | 502 | "Failed to upsert hashes" |
| Deployment creation failed | 502 | Cloudflare error details |
| Cloudflare API timeout | 504 | "Cloudflare API timed out" |
| Network error | 502 | Network error details |

---

## Dependencies

| Package | Version | Purpose |
|---|---|---|
| `httpx` | 0.27.0 | Async HTTP client for Cloudflare API calls |
| `blake3` | 1.0.4 | BLAKE3 hashing (matches Wrangler's algorithm) |
| `jinja2` | 3.1.3 | HTML article template rendering |

---

## Notes

- **Idempotent uploads**: BLAKE3 deduplication means re-publishing unchanged files costs no extra bandwidth — only new/modified files are uploaded.
- **Single Cloudflare project**: All articles share one Pages project and one subdomain. Each publish is a new deployment revision, so Cloudflare keeps a deployment history.
- **No authentication on the live site**: The published Pages site is fully public. Anyone with the URL can view the articles.
- **Propagation delay**: After a successful API response, allow ~30 seconds for the deployment to propagate across Cloudflare's CDN before the URL is accessible.
