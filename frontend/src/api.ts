import axios from 'axios';

const API_BASE = 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE,
  timeout: 120000, // 2 min for generation requests
});

export interface Target {
  id: string;
  name: string;
  role: string;
  category: string;
  description: string;
  sample_image: string;
}

export interface Narrative {
  id: string;
  title: string;
  description: string;
  category: string;
  icon: string;
}

export interface PromptResponse {
  prompt: string;
  target: Target;
  narrative: Narrative;
  // For articles: dual coordinated prompts
  image_prompt?: string;
  article_prompt?: string;
}

export interface ImageResponse {
  image_url: string;
  filename: string;
}

export interface VideoResponse {
  operation_id: string;
  status: string;
}

export interface VideoStatusResponse {
  status: 'pending' | 'complete' | 'failed';
  video_url?: string;
  filename?: string;
  error?: string;
}

export async function fetchTargets(): Promise<Target[]> {
  const res = await api.get('/api/targets');
  return res.data.targets;
}

export async function fetchNarratives(): Promise<Narrative[]> {
  const res = await api.get('/api/narratives');
  return res.data.narratives;
}

export async function generatePrompt(
  targetId: string,
  narrativeId: string,
  generationType: 'image' | 'video' | 'article',
  signal?: AbortSignal
): Promise<PromptResponse> {
  const res = await api.post('/api/generate-prompt', {
    target_id: targetId,
    narrative_id: narrativeId,
    generation_type: generationType,
  }, {
    signal, // Pass abort signal to cancel request
  });
  return res.data;
}

export async function generateImage(prompt: string): Promise<ImageResponse> {
  const res = await api.post('/api/generate-image', { prompt });
  return res.data;
}

export async function generateNarration(
  imagePrompt: string,
  targetId: string,
  narrativeId: string
): Promise<{ narration_prompt: string }> {
  const res = await api.post('/api/generate-narration', {
    image_prompt: imagePrompt,
    target_id: targetId,
    narrative_id: narrativeId,
  });
  return res.data;
}

export async function generateVideo(imageFilename: string, narrationPrompt: string): Promise<VideoResponse> {
  const res = await api.post('/api/generate-video', {
    image_filename: imageFilename,
    narration_prompt: narrationPrompt,
  });
  return res.data;
}

export async function checkVideoStatus(operationId: string): Promise<VideoStatusResponse> {
  const res = await api.get(`/api/video-status/${operationId}`);
  return res.data;
}

export function getMediaUrl(path: string): string {
  return `${API_BASE}${path}`;
}

export function getDownloadUrl(filename: string): string {
  return `${API_BASE}/api/download/${filename}`;
}

export interface DriveUploadResponse {
  file_id: string;
  web_view_link: string;
  filename: string;
}

export interface ArticleResponse {
  article_id: string;
  article_url: string;
  headline: string;
  image_url: string;
  published_url: string | null;
}

export interface PublishResponse {
  article_id: string;
  published_url: string;
  headline: string;
  message: string;
}

export async function uploadToDrive(filename: string): Promise<DriveUploadResponse> {
  const res = await api.post(`/api/upload-to-drive/${filename}`);
  return res.data;
}

export async function generateArticle(
  targetId: string,
  narrativeId: string,
  imagePrompt: string,
  articlePrompt: string
): Promise<ArticleResponse> {
  const res = await api.post('/api/generate-article', {
    target_id: targetId,
    narrative_id: narrativeId,
    image_prompt: imagePrompt,
    article_prompt: articlePrompt,
  });
  return res.data;
}

export async function publishArticle(articleId: string): Promise<PublishResponse> {
  const res = await api.post(`/api/publish-article/${articleId}`);
  return res.data;
}

export function getArticleUrl(path: string): string {
  return `${API_BASE}${path}`;
}
